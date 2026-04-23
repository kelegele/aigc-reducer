"""认知特征检测器 — 检测文本是否缺乏批判性思考和个人见解。"""

import re
from aigc_reducer_core.parser import Paragraph


CRITICAL_MARKERS = [
    "笔者认为",
    "值得注意",
    "需要注意的是",
    "然而",
    "但是",
    "问题在于",
    "矛盾的是",
    "出人意料",
    "意料之外",
    "令人惊讶",
    "我们推测",
    "或许",
    "可能",
    "尚待",
    "有待",
    "——",
    "？",
    "?",
    "不过",
    "倒是",
    "其实",
    "话说",
    "倒是说",
]

DESCRIPTIVE_PATTERNS = [
    r"结果表明",
    r"结果显示",
    r"实验表明",
    r"证明了",
    r"验证了",
    r"优于",
    r"高于",
    r"低于",
]


class CognitiveDetector:
    def analyze(self, paragraph: Paragraph) -> float:
        text = paragraph.text
        score = 40

        critical_count = 0
        for marker in CRITICAL_MARKERS:
            if marker in text:
                critical_count += 1
                score -= 15

        descriptive_count = 0
        for pattern in DESCRIPTIVE_PATTERNS:
            if re.search(pattern, text):
                descriptive_count += 1
                score += 10

        if any(m in text for m in ["笔者", "我们", "我发现", "我觉得", "个人认为"]):
            score -= 20

        if "?" in text or "？" in text:
            score -= 10

        if critical_count == 0 and descriptive_count >= 2:
            score += 20

        return max(0, min(score, 100))
