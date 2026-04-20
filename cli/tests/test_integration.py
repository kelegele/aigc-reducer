# tests/test_integration.py
"""集成测试 — 验证完整流程。"""

import pytest
from aigc_reducer.parser import parse_document, Paragraph
from aigc_reducer.detector import AIGCDetector
from aigc_reducer.rewriter import Rewriter


class TestIntegration:
    def test_full_pipeline(self, tmp_path):
        """测试完整降重流程：解析 → 检测 → 改写 → 重检测。"""
        paper = tmp_path / "test_paper.md"
        paper.write_text(
            "首先，本研究采用了深度学习方法。其次，实验结果表明该方法有效。"
            "此外，结果也显著。综上所述，具有重要意义。\n\n"
            "图像识别是计算机视觉的核心任务之一。",
            encoding="utf-8",
        )

        paragraphs = parse_document(str(paper))
        assert len(paragraphs) == 2

        detector = AIGCDetector()
        results = detector.analyze_all(paragraphs)
        assert results[0]["risk_level"] in ("高风险", "中高", "中风险")

        rewriter = Rewriter("学术人文化")
        rewritten = rewriter.rewrite_all(paragraphs, results)
        assert len(rewritten) == 2

        after_results = detector.analyze_all(rewritten)
        assert rewritten[0].text != paragraphs[0].text
