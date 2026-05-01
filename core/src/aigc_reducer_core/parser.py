"""文档解析器 — 支持 docx/doc/pdf/md 格式，统一输出为 Paragraph 列表。"""

import os
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class Paragraph:
    """一个段落的结构化表示。"""
    text: str                          # 段落纯文本
    index: int = 0                     # 段落序号
    is_heading: bool = False           # 是否为标题
    has_formula: bool = False          # 是否包含公式
    has_code: bool = False             # 是否包含代码块
    original_format: str = ""          # 原始格式标记


def parse_document(file_path: str) -> List[Paragraph]:
    """解析文档文件，返回 Paragraph 列表。

    Args:
        file_path: 文件路径，支持 .md, .docx, .doc, .pdf

    Returns:
        Paragraph 列表，仅包含正文段落
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".md":
        return _parse_markdown(file_path)
    elif ext == ".docx":
        return _parse_docx(file_path)
    elif ext == ".doc":
        return _parse_doc(file_path)
    elif ext == ".pdf":
        return _parse_pdf(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def _parse_markdown(file_path: str) -> List[Paragraph]:
    """解析 Markdown 文件。"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    paragraphs = []
    index = 0
    in_code_block = False

    for line in content.split("\n"):
        # 跳过代码块
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # 标题行
        if line.strip().startswith("#"):
            heading_text = line.strip().lstrip("#").strip()
            if heading_text:
                paragraphs.append(Paragraph(
                    text=heading_text,
                    index=index,
                    is_heading=True,
                    has_formula=False,
                    has_code=False,
                    original_format="markdown",
                ))
                index += 1
            continue

        # 跳过空行
        if not line.strip():
            continue

        text = line.strip()
        has_formula = bool(re.search(r"\$[^$]+\$", text))
        has_code = bool(re.search(r"`[^`]+`", text))

        paragraphs.append(Paragraph(
            text=text,
            index=index,
            is_heading=False,
            has_formula=has_formula,
            has_code=has_code,
            original_format="markdown",
        ))
        index += 1

    return paragraphs


def _parse_docx(file_path: str) -> List[Paragraph]:
    """解析 DOCX 文件。"""
    from docx import Document

    doc = Document(file_path)
    paragraphs = []
    index = 0

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        # 跳过头标题（Heading 1-3）
        if para.style.name.startswith("Heading"):
            paragraphs.append(Paragraph(
                text=text,
                index=index,
                is_heading=True,
                has_formula=False,
                original_format="docx",
            ))
            index += 1
            continue

        has_formula = bool(re.search(r"\$[^$]+\$", text))

        paragraphs.append(Paragraph(
            text=text,
            index=index,
            is_heading=False,
            has_formula=has_formula,
            original_format="docx",
        ))
        index += 1

    return paragraphs


def _parse_doc(file_path: str) -> List[Paragraph]:
    """解析 DOC 文件 — 先转换为 docx 再解析。"""
    import subprocess
    import tempfile
    import shutil

    if not shutil.which("libreoffice"):
        raise RuntimeError(
            "需要安装 LibreOffice 才能解析 .doc 文件。\n"
            "macOS: brew install --cask libreoffice\n"
            "Ubuntu: sudo apt install libreoffice"
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        # 转换为 docx
        subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to",
                "docx",
                "--outdir",
                tmpdir,
                file_path,
            ],
            check=True,
            capture_output=True,
        )

        docx_path = os.path.join(
            tmpdir,
            os.path.splitext(os.path.basename(file_path))[0] + ".docx",
        )
        return _parse_docx(docx_path)


def _parse_pdf(file_path: str) -> List[Paragraph]:
    """解析 PDF 文件，基于字符坐标分行分段。"""
    import pdfplumber
    from collections import Counter

    paragraphs = []
    index = 0

    with pdfplumber.open(file_path) as pdf:
        # 收集所有字符字号，取众数为正文字号
        body_sizes: list[float] = []
        for page in pdf.pages:
            for ch in page.chars:
                if ch["text"].strip():
                    body_sizes.append(round(ch["size"], 1))
        body_size = Counter(body_sizes).most_common(1)[0][0] if body_sizes else 12.0
        heading_threshold = body_size * 1.2

        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            # 构建 top → max_size 映射
            line_size: dict[int, float] = {}
            for ch in page.chars:
                if not ch["text"].strip():
                    continue
                top_key = round(ch["top"])
                size = round(ch["size"], 1)
                if top_key not in line_size or size > line_size[top_key]:
                    line_size[top_key] = size

            # 用 extract_text 的行结构做基础分段
            current_para: list[str] = []
            current_is_heading = False
            prev_top: float | None = None

            for line in text.split("\n"):
                stripped = line.strip()
                if not stripped:
                    if current_para:
                        paragraphs.append(Paragraph(
                            text="".join(current_para),
                            index=index,
                            is_heading=current_is_heading,
                            has_formula=bool(re.search(r"\$[^$]+\$", "".join(current_para))),
                            original_format="pdf",
                        ))
                        index += 1
                        current_para = []
                        current_is_heading = False
                        prev_top = None
                    continue

                # 找该行的 top 和 size
                first_char_top = None
                first_char_size = body_size
                for ch in page.chars:
                    if ch["text"].strip() and stripped.startswith(ch["text"].strip()):
                        first_char_top = ch["top"]
                        first_char_size = round(ch["size"], 1)
                        break

                is_heading = first_char_size >= heading_threshold or (
                    len(stripped) <= 30 and not stripped.endswith(("。", "，", "、", "；", "：", ".", ","))
                    and not stripped.startswith(("-", "（", "("))
                ) or (
                    index == 0 and len(paragraphs) == 0
                    and len(stripped) <= 50
                    and not stripped.endswith(("。", "；"))
                )

                # 段落分隔：标题行独立成段 + 前行句末标点 + 间距突增
                should_split = False
                if is_heading:
                    # heading 行：先输出当前段，heading 自身也独立
                    if current_para:
                        should_split = True
                elif current_para:
                    last_text = current_para[-1]
                    ended = last_text.rstrip().endswith(("。", "！", "？", ".", "!", "?", "）", ")"))
                    if ended:
                        should_split = True
                    elif prev_top is not None and first_char_top is not None:
                        gap = first_char_top - prev_top
                        if gap > body_size * 2.5:
                            should_split = True

                if should_split:
                    paragraphs.append(Paragraph(
                        text="".join(current_para),
                        index=index,
                        is_heading=current_is_heading,
                        has_formula=bool(re.search(r"\$[^$]+\$", "".join(current_para))),
                        original_format="pdf",
                    ))
                    index += 1
                    current_para = []
                    current_is_heading = False

                if not current_para:
                    current_is_heading = is_heading
                current_para.append(stripped)

                # heading 行独立成段，立即输出
                if is_heading:
                    paragraphs.append(Paragraph(
                        text="".join(current_para),
                        index=index,
                        is_heading=True,
                        has_formula=bool(re.search(r"\$[^$]+\$", "".join(current_para))),
                        original_format="pdf",
                    ))
                    index += 1
                    current_para = []
                    current_is_heading = False
                    prev_top = None
                    continue

                if first_char_top is not None:
                    prev_top = first_char_top

            if current_para:
                paragraphs.append(Paragraph(
                    text="".join(current_para),
                    index=index,
                    is_heading=current_is_heading,
                    has_formula=bool(re.search(r"\$[^$]+\$", "".join(current_para))),
                    original_format="pdf",
                ))
                index += 1

    return paragraphs
