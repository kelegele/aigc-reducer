"""困惑度检测器 — 检测文本是否过于流畅和可预测。"""

import re
from aigc_reducer_core.parser import Paragraph


COMMON_PATTERNS = [
    r"能够有效",
    r"具有重要意义",
    r"广泛的应用",
    r"良好的性能",
    r"得到了广泛的关注",
    r"成为了研究热点",
    r"引起了广泛关注",
    r"具有重要的理论",
    r"具有重要的实际",
    r"在实际应用中",
    r"综上所述",
    r"总而言之",
]


class PerplexityDetector:
    def analyze(self, paragraph: Paragraph) -> float:
        text = paragraph.text
        score = 0.0

        matches = 0
        for pattern in COMMON_PATTERNS:
            if re.search(pattern, text):
                matches += 1

        template_ratio = matches / max(len(text) / 50, 1)
        score += min(template_ratio * 100, 50)

        words = list(text)
        if len(words) > 10:
            unique_words = len(set(words))
            ttr = unique_words / len(words)
            if ttr > 0.85:
                score += 30
            elif ttr > 0.75:
                score += 15

        human_markers = ["——", "倒", "倒是", "吧", "呢", "其实", "不过", "话说"]
        for marker in human_markers:
            if marker in text:
                score = max(0, score - 10)

        return min(score, 100)
