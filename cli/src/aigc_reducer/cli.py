"""CLI 入口 — 实现完整的 6 步交互流程。"""

import logging
import sys
import os
import shutil
import tempfile
from logging.handlers import TimedRotatingFileHandler
from typing import Dict, List, Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

from aigc_reducer_core.parser import parse_document, Paragraph
from aigc_reducer_core.llm_client import LLMClient
from aigc_reducer_core.detector import AIGCDetector
from aigc_reducer_core.rewriter import Rewriter, list_styles
from aigc_reducer.report import (
    print_scan_report,
    print_revision_progress,
    print_final_report,
    RISK_LABEL,
)

console = Console()
logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    """配置日志：同时输出到 stdout 和 cli/logs/ 目录，每天轮转。"""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
    log_dir = os.path.normpath(log_dir)
    os.makedirs(log_dir, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if not root.handlers:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        root.addHandler(sh)

    fh = TimedRotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    logging.getLogger("httpx").setLevel(logging.WARNING)

    logger.info("Logging initialized: logs dir = %s", os.path.abspath(log_dir))


_setup_logging()

# 工作目录结构
WORKSPACE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "aigc-reducer")
DIR_RAW = os.path.join(WORKSPACE, "raw-paper")
DIR_MD = os.path.join(WORKSPACE, "md-paper")
DIR_OUTPUT = os.path.join(WORKSPACE, "output")


def _ensure_dirs():
    """确保工作目录存在。"""
    os.makedirs(DIR_RAW, exist_ok=True)
    os.makedirs(DIR_MD, exist_ok=True)
    os.makedirs(DIR_OUTPUT, exist_ok=True)


def main():
    """CLI 主入口。"""
    _ensure_dirs()
    console.print(Panel("AIGC 降重工具", subtitle="降低论文 AI 查重率", border_style="cyan"))
    console.print(f"  原始文件: {DIR_RAW}")
    console.print(f"  中间产物: {DIR_MD}")
    console.print(f"  最终输出: {DIR_OUTPUT}")

    input_path = _get_input_path()
    paragraphs = _load_document(input_path)

    # 解析后将原始文件复制到 raw-paper
    _stash_raw(input_path)

    # 解析后的 md 文本存到 md-paper
    _save_parsed_md(paragraphs, input_path)

    style = _select_style()

    mode = _select_detect_mode()

    # 创建 LLM 客户端（llm 检测模式和改写都需要）
    llm_client = LLMClient.from_env()

    detector = AIGCDetector(mode=mode, llm_client=llm_client)
    before_results = detector.analyze_all(paragraphs)
    total_words = sum(len(p.text) for p in paragraphs)
    estimated_rate, needs_processing = print_scan_report(paragraphs, before_results, total_words)

    if not needs_processing:
        console.print("\n[green]所有段落均为低风险，无需处理！[/green]")
        return

    do_full_rewrite = Confirm.ask("\n是否进行全量语义重构？（推荐：可进一步降低整体 AI 特征值）", default=False)

    if do_full_rewrite:
        paragraphs = _full_semantic_reconstruct(paragraphs, style, llm_client)
        before_results = detector.analyze_all(paragraphs)
        estimated_rate, needs_processing = print_scan_report(paragraphs, before_results, total_words)

    rewriter = Rewriter(style, llm_client=llm_client)
    after_paragraphs = paragraphs.copy()
    after_results = before_results.copy()

    for idx, para_idx in enumerate(needs_processing):
        para = paragraphs[para_idx]
        result = before_results[para_idx]

        option_a = rewriter.rewrite_single(para.text, result, conservative=False)
        option_b = rewriter.rewrite_single(para.text, result, conservative=True)

        print_revision_progress(
            current=idx + 1,
            total=len(needs_processing),
            paragraph_index=para_idx,
            text=para.text,
            detection_result=result,
            option_a=option_a,
            option_b=option_b,
        )

        choice = Prompt.ask("请选择", choices=["A", "B", "手动", "跳过"], default="A")

        if choice == "A":
            after_paragraphs[para_idx] = Paragraph(
                text=option_a,
                index=para.index,
            )
        elif choice == "B":
            after_paragraphs[para_idx] = Paragraph(
                text=option_b,
                index=para.index,
            )
        elif choice == "手动":
            manual_text = Prompt.ask("请输入改写后的文本")
            after_paragraphs[para_idx] = Paragraph(
                text=manual_text,
                index=para.index,
            )

    after_results = detector.analyze_all(after_paragraphs)

    basename = _derive_basename(input_path)
    output_file = os.path.join(DIR_OUTPUT, f"{basename}_reduced.md")
    diff_file = os.path.join(DIR_OUTPUT, f"{basename}_diff.md")
    revision_file = os.path.join(DIR_OUTPUT, f"{basename}_revision_report.md")

    _save_output(after_paragraphs, output_file)
    _save_diff(before_results, after_results, paragraphs, after_paragraphs, diff_file)
    _save_revision_report(before_results, after_results, paragraphs, after_paragraphs, revision_file)

    print_final_report(before_results, after_results, output_file, diff_file)


def _get_input_path() -> str:
    """获取输入文件路径。"""
    console.print("\n请选择输入方式：")
    console.print("  1. 指定文件路径（.md/.docx/.doc/.pdf）")
    console.print("  2. 指定目录（自动合并目录下所有文档）")
    console.print("  3. 手动输入段落")

    choice = Prompt.ask("请选择", choices=["1", "2", "3"], default="1")

    if choice == "1":
        path = Prompt.ask("请输入文件路径")
        if not os.path.exists(path):
            console.print(f"[red]文件不存在: {path}[/red]")
            sys.exit(1)
        return path
    elif choice == "2":
        dir_path = Prompt.ask("请输入目录路径")
        if not os.path.isdir(dir_path):
            console.print(f"[red]目录不存在: {dir_path}[/red]")
            sys.exit(1)
        console.print("[yellow]目录模式暂未实现，请使用文件模式[/yellow]")
        sys.exit(1)
    else:
        console.print("\n请输入论文内容（空行结束）：")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
        tmp.write("\n\n".join(lines))
        tmp.close()
        return tmp.name


def _load_document(path: str) -> List[Paragraph]:
    """加载文档。"""
    console.print(f"\n[green]正在解析: {path}[/green]")
    try:
        paragraphs = parse_document(path)
        console.print(f"[green]成功加载 {len(paragraphs)} 个段落[/green]")
        return paragraphs
    except Exception as e:
        console.print(f"[red]解析失败: {e}[/red]")
        sys.exit(1)


def _select_style() -> str:
    """选择改写风格。"""
    console.print("\n请选择改写风格：")

    style_examples = {
        "口语化": ("日常表达，自然停顿", "「这个办法确实能提高识别的准确度，用起来感觉还不错」"),
        "文言文化": ("四字成语、对仗句式", "「此法诚可提识别之准度，屡试不爽，成效昭然」"),
        "中英混杂化": ("插入英文术语、短语", "「这个方法确实能 improve 识别的 accuracy」"),
        "学术人文化": ("主观评价、疑问句（推荐）", "「笔者认为，该方法确实有效——但是否适用于所有场景？」"),
        "粗犷草稿风": ("短句为主，轻微不连贯", "「方法有用。识别率上去了。但有些情况还得再看看。」"),
    }

    for i, (name, (desc, example)) in enumerate(style_examples.items(), 1):
        console.print(f"  [{i}] {name} — {desc}")
        console.print(f"      例：{example}")

    choice = Prompt.ask("请选择风格编号", choices=[str(i) for i in range(1, 6)], default="4")
    style_names = list(style_examples.keys())
    return style_names[int(choice) - 1]


def _select_detect_mode() -> str:
    """选择检测模式。"""
    console.print("\n请选择检测模式：")
    console.print("  [1] 规则引擎 — 快速，基于文本特征分析（困惑度、突发性等）")
    console.print("  [2] LLM 反查 — 精准，用大模型模拟商业平台判断（推荐）")

    choice = Prompt.ask("请选择", choices=["1", "2"], default="2")
    return "llm" if choice == "2" else "rules"


def _derive_basename(input_path: str) -> str:
    """从输入文件名提取基础名（不含扩展名）。"""
    name = os.path.basename(input_path)
    return os.path.splitext(name)[0]


def _stash_raw(input_path: str):
    """将原始文件复制到 raw-paper 目录。"""
    if not os.path.isfile(input_path):
        return
    dest = os.path.join(DIR_RAW, os.path.basename(input_path))
    if os.path.abspath(input_path) != os.path.abspath(dest):
        shutil.copy2(input_path, dest)
        console.print(f"[dim]原始文件已备份: {dest}[/dim]")


def _save_parsed_md(paragraphs: List[Paragraph], input_path: str):
    """将解析后的纯文本保存到 md-paper 目录。"""
    basename = _derive_basename(input_path)
    md_path = os.path.join(DIR_MD, f"{basename}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        for para in paragraphs:
            f.write(para.text + "\n\n")
    console.print(f"[dim]解析后文本已保存: {md_path}[/dim]")


def _save_revision_report(
    before_results: List[Dict],
    after_results: List[Dict],
    before_paras: List[Paragraph],
    after_paras: List[Paragraph],
    revision_file: str,
):
    """保存整改建议报告。"""
    with open(revision_file, "w", encoding="utf-8") as f:
        f.write("# AIGC 降重整改建议报告\n\n")
        for i, (bp, ap, br, ar) in enumerate(zip(before_paras, after_paras, before_results, after_results)):
            if bp.text != ap.text:
                f.write(f"## 段落 {i}\n\n")
                f.write(f"**检测分数**: {RISK_LABEL.get(br['risk_level'], br['risk_level'])} {br['composite_score']}% → {RISK_LABEL.get(ar['risk_level'], ar['risk_level'])} {ar['composite_score']}%\n\n")
                f.write(f"**检测特征**:\n")
                for feat in br.get('ai_features', []):
                    f.write(f"- {feat}\n")
                f.write(f"\n**原文**:\n\n{bp.text}\n\n")
                f.write(f"**改写后**:\n\n{ap.text}\n\n")
                f.write("---\n\n")

    console.print(f"[green]整改建议报告已保存到: {revision_file}[/green]")


def _full_semantic_reconstruct(paragraphs: List[Paragraph], style: str, llm_client: LLMClient) -> List[Paragraph]:
    """全量语义重构 — 打散全文骨架并重建逻辑。"""
    console.print("\n[green]正在进行全量语义重构...[/green]")

    full_text = "\n\n".join(p.text for p in paragraphs)
    rewriter = Rewriter(style, llm_client=llm_client)

    prompt = (
        f"请对以下学术论文全文进行深度语义重构：打散原有句子骨架，重建逻辑框架，"
        f"同时保持学术严谨性和核心内容不变。去除所有 AI 写作痕迹。\n\n"
        f"原文：\n{full_text}\n\n"
        f"重构后（按段落分割，用空行分隔）："
    )

    reconstructed_text = rewriter.style._call_llm(prompt)

    new_paragraphs = []
    for i, text in enumerate(reconstructed_text.split("\n\n")):
        text = text.strip()
        if text:
            new_paragraphs.append(Paragraph(text=text, index=i))

    return new_paragraphs


def _save_output(paragraphs: List[Paragraph], output_file: str):
    """保存修改后的全文。"""
    with open(output_file, "w", encoding="utf-8") as f:
        for para in paragraphs:
            f.write(para.text + "\n\n")
    console.print(f"\n[green]修改后全文已保存到: {output_file}[/green]")


def _save_diff(
    before_results: List[Dict],
    after_results: List[Dict],
    before_paras: List[Paragraph],
    after_paras: List[Paragraph],
    diff_file: str,
):
    """保存差异对比报告。"""
    with open(diff_file, "w", encoding="utf-8") as f:
        f.write("# AIGC 降重差异对比报告\n\n")
        for i, (bp, ap, br, ar) in enumerate(zip(before_paras, after_paras, before_results, after_results)):
            if bp.text != ap.text:
                f.write(f"## 段落 {i}\n\n")
                f.write(f"**修改前** ({RISK_LABEL.get(br['risk_level'], br['risk_level'])} {br['composite_score']}%):\n\n")
                f.write(f"{bp.text}\n\n")
                f.write(f"**修改后** ({RISK_LABEL.get(ar['risk_level'], ar['risk_level'])} {ar['composite_score']}%):\n\n")
                f.write(f"{ap.text}\n\n")
                f.write("---\n\n")

    console.print(f"[green]差异对比报告已保存到: {diff_file}[/green]")


if __name__ == "__main__":
    main()
