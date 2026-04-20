"""突发性检测器 — 检测句子长度和句式的变化幅度。"""

import re
from aigc_reducer.parser import Paragraph


class BurstinessDetector:
    def analyze(self, paragraph: Paragraph) -> float:
        text = paragraph.text
        sentences = re.split(r"[。！？.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) < 3:
            return 20

        lengths = [len(s) for s in sentences]
        mean_len = sum(lengths) / len(lengths)
        variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
        std_dev = variance ** 0.5
        cv = std_dev / mean_len if mean_len > 0 else 0

        if cv < 0.2:
            return 80
        elif cv < 0.3:
            return 60
        elif cv < 0.5:
            return 30
        else:
            return 10
