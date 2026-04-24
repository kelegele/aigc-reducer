"""报告生成器 — 生成风险评估报告和差异对比报告。"""

from typing import Dict, List
from rich.console import Console
from rich.panel import Panel

console = Console()

RISK_EMOJI = {
    "low": "🟢",
    "medium": "🟡",
    "medium_high": "🟠",
    "high": "🔴",
}

RISK_LABEL = {
    "low": "低风险",
    "medium": "中风险",
    "medium_high": "中高",
    "high": "高风险",
}


def print_scan_report(
    paragraphs: List,
    detection_results: List[Dict],
    total_words: int,
):
    """输出首次扫描风险评估报告。"""
    high_risk_count = sum(
        1 for r in detection_results
        if r["risk_level"] in ("high", "medium_high")
    )
    estimated_rate = round(high_risk_count / max(len(detection_results), 1) * 100)

    header = f"═══ AIGC 风险评估报告 ═══\n总字数: {total_words:,} | 预估 AIGC 率: {estimated_rate}%\n"
    console.print(Panel(header, title="扫描结果", border_style="yellow"))

    needs_processing = []

    for i, (para, result) in enumerate(zip(paragraphs, detection_results)):
        emoji = RISK_EMOJI.get(result["risk_level"], "⚪")
        score = result["composite_score"]

        text = para.text
        head = text[:15] + "..." if len(text) > 15 else text
        tail = "..." + text[-15:] if len(text) > 15 else text

        console.print(f"段落 {i}  \"{head}\" → \"{tail}\"")
        console.print(f"  风险: {emoji} {score}% | 评价: {_generate_evaluation(result)}")
        console.print()

        if result["risk_level"] in ("high", "medium_high"):
            needs_processing.append(i)

    console.print(f"需处理段落: {', '.join(f'段落{n}' for n in needs_processing)} (共{len(needs_processing)}段)")
    console.print("═══════════════════════════")

    return estimated_rate, needs_processing


def print_revision_progress(
    current: int,
    total: int,
    paragraph_index: int,
    text: str,
    detection_result: Dict,
    option_a: str,
    option_b: str,
):
    """输出逐段精调交互界面。"""
    emoji = RISK_EMOJI.get(detection_result["risk_level"], "⚪")
    score = detection_result["composite_score"]

    head = text[:20] + "..." if len(text) > 20 else text
    tail = "..." + text[-20:] if len(text) > 20 else text

    console.print(f"\n📍 处理进度: {current}/{total}")
    console.print(f"段落 {paragraph_index}: \"{head}\" → \"{tail}\"")
    console.print(f"风险等级: {emoji} {score}%")

    console.print("\nAI 特征分析：")
    for feature in detection_result.get("ai_features", []):
        console.print(f"  • {feature}")

    console.print(Panel(option_a, title="改写方案 A（推荐）", border_style="green"))
    console.print(Panel(option_b, title="改写方案 B（保守）", border_style="blue"))

    console.print("\n请选择：A / B / 手动输入 / 跳过")


def print_final_report(
    before_results: List[Dict],
    after_results: List[Dict],
    output_file: str,
    diff_file: str,
):
    """输出最终降重报告。"""
    before_rate = _calc_rate(before_results)
    after_rate = _calc_rate(after_results)

    console.print(Panel("", title="═══ 降重完成 - 最终报告 ═══", border_style="green"))
    console.print(f"\n修改前 AIGC 率: {before_rate}%  →  修改后 AIGC 率: {after_rate}%  {'✅' if after_rate < 10 else '⚠️'}")
    console.print("\n修改汇总：")

    for i, (before, after) in enumerate(zip(before_results, after_results)):
        if before["risk_level"] in ("high", "medium_high", "medium"):
            before_emoji = RISK_EMOJI.get(before["risk_level"], "⚪")
            after_emoji = RISK_EMOJI.get(after["risk_level"], "⚪")
            console.print(
                f"  段落 {i}: {before['composite_score']}% → {after['composite_score']}%  "
                f"{before_emoji}→{after_emoji}"
            )

    console.print(f"\n📄 修改后全文 (已保存到 {output_file})")
    console.print(f"📊 差异对比报告 ({diff_file})")


def _calc_rate(results: List[Dict]) -> float:
    """计算整体 AIGC 率。"""
    if not results:
        return 0
    high_risk = sum(
        1 for r in results
        if r["risk_level"] in ("high", "medium_high")
    )
    return round(high_risk / len(results) * 100)


def _generate_evaluation(result: Dict) -> str:
    """根据检测结果生成评价文本。"""
    features = result.get("ai_features", [])
    if not features:
        return "人类写作特征明显，句式自然波动"
    return "，".join(features)
