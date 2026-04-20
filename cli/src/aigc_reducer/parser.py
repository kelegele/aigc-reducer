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

        # 跳过标题行
        if line.strip().startswith("#"):
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
    """解析 PDF 文件。"""
    import pdfplumber

    paragraphs = []
    index = 0

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            # 按行分割，合并为段落
            lines = text.split("\n")
            current_para = []

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    # 空行 = 段落分隔
                    if current_para:
                        para_text = " ".join(current_para)
                        has_formula = bool(re.search(r"\$[^$]+\$", para_text))
                        paragraphs.append(Paragraph(
                            text=para_text,
                            index=index,
                            is_heading=False,
                            has_formula=has_formula,
                            original_format="pdf",
                        ))
                        index += 1
                        current_para = []
                else:
                    current_para.append(stripped)

            # 处理最后一个段落
            if current_para:
                para_text = " ".join(current_para)
                has_formula = bool(re.search(r"\$[^$]+\$", para_text))
                paragraphs.append(Paragraph(
                    text=para_text,
                    index=index,
                    is_heading=False,
                    has_formula=has_formula,
                    original_format="pdf",
                ))
                index += 1

    return paragraphs
