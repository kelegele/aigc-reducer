"""语义指纹检测器 — 检测语义组织方式是否符合 AI 标准论证结构。"""

import re
from aigc_reducer_core.parser import Paragraph


STANDARD_PATTERNS = [
    r"本研究旨在",
    r"本文首先",
    r"然后提出",
    r"最后通过",
    r"实验验证了",
    r"结果表明",
    r"综上所述",
    r"具有重要意义",
    r"具有重要的理论和实际",
    r"为.*提供参考",
    r"为.*奠定基础",
]

HUMAN_PATTERNS = [
    r"问题在于",
    r"反过来",
    r"换个角度",
    r"有意思的是",
    r"奇怪的是",
    r"没想到",
    r"出乎意料",
]


class SemanticFingerprintDetector:
    def analyze(self, paragraph: Paragraph) -> float:
        text = paragraph.text
        score = 30

        standard_matches = 0
        for pattern in STANDARD_PATTERNS:
            if re.search(pattern, text):
                standard_matches += 1
                score += 20

        human_matches = 0
        for pattern in HUMAN_PATTERNS:
            if re.search(pattern, text):
                human_matches += 1
                score -= 15

        clauses = re.split(r"[，,；;]", text)
        if len(clauses) >= 4:
            clause_lengths = [len(c.strip()) for c in clauses]
            avg = sum(clause_lengths) / len(clause_lengths)
            if avg > 0:
                variance = sum((l - avg) ** 2 for l in clause_lengths) / len(clause_lengths)
                if variance < 10:
                    score += 15

        if standard_matches == 0:
            score -= 10

        return max(0, min(score, 100))
