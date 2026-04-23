# tests/test_detector.py
import pytest
from aigc_reducer_core.parser import Paragraph
from aigc_reducer_core.detectors import (
    PerplexityDetector,
    BurstinessDetector,
    ConnectorDetector,
    CognitiveDetector,
    SemanticFingerprintDetector,
)


class TestPerplexityDetector:
    def setup_method(self):
        self.detector = PerplexityDetector()

    def test_low_perplexity_text_flags_ai(self):
        text = "该方法能够有效提升识别准确率，在多个测试集中均表现出良好的性能。"
        para = Paragraph(text=text, index=0)
        score = self.detector.analyze(para)
        assert score > 50

    def test_high_perplexity_text_passes(self):
        text = "消融实验显示，去掉 SE Block 后 mAP 掉了 3 个点——这倒是意料之外，说明通道注意力确实管用。"
        para = Paragraph(text=text, index=0)
        score = self.detector.analyze(para)
        assert score < 20


class TestBurstinessDetector:
    def setup_method(self):
        self.detector = BurstinessDetector()

    def test_uniform_sentence_length_flags_ai(self):
        text = "该方法有效。实验结果显著。性能得到提升。准确率有所增加。模型表现良好。结果令人满意。"
        para = Paragraph(text=text, index=0)
        score = self.detector.analyze(para)
        assert score > 50

    def test_varied_sentence_length_passes(self):
        text = "方法有用，虽然一开始结果不太理想——后来调整了参数才稳定。效果不错。"
        para = Paragraph(text=text, index=0)
        score = self.detector.analyze(para)
        assert score < 30


class TestConnectorDetector:
    def setup_method(self):
        self.detector = ConnectorDetector()

    def test_many_template_connectors_flags_ai(self):
        text = "首先，本研究采用了深度学习的方法。其次，通过实验验证了有效性。此外，结果也表明了其优越性。综上所述，该方法具有重要意义。"
        para = Paragraph(text=text, index=0)
        score = self.detector.analyze(para)
        assert score > 60

    def test_few_connecters_passes(self):
        text = "深度学习在图像分类中效果很好。实验结果也验证了这一点。"
        para = Paragraph(text=text, index=0)
        score = self.detector.analyze(para)
        assert score < 30


class TestCognitiveDetector:
    def setup_method(self):
        self.detector = CognitiveDetector()

    def test_pure_descriptive_text_flags_ai(self):
        text = "实验结果表明该方法有效。准确率达到了92%。性能优于基线模型。"
        para = Paragraph(text=text, index=0)
        score = self.detector.analyze(para)
        assert score > 50

    def test_critical_thinking_passes(self):
        text = "实验结果虽然看起来不错，但仔细分析后发现，在边缘场景下表现并不稳定——这或许与训练数据的偏差有关。"
        para = Paragraph(text=text, index=0)
        score = self.detector.analyze(para)
        assert score < 30


class TestSemanticFingerprintDetector:
    def setup_method(self):
        self.detector = SemanticFingerprintDetector()

    def test_standard_argument_structure_flags_ai(self):
        text = "本研究旨在解决XX问题。首先介绍了相关背景。然后提出了我们的方法。最后通过实验验证了有效性。"
        para = Paragraph(text=text, index=0)
        score = self.detector.analyze(para)
        assert score > 50

    def test_non_standard_reasoning_passes(self):
        text = "问题摆在那儿：XX 到底能不能用 YY 方法解决？我们试着换了个角度——把 A 和 B 反过来看，结果反而更清楚了。"
        para = Paragraph(text=text, index=0)
        score = self.detector.analyze(para)
        assert score < 30


class TestAIGCDetector:
    def setup_method(self):
        from aigc_reducer_core.detector import AIGCDetector
        self.detector = AIGCDetector()

    def test_composite_score_classification(self):
        high_risk = Paragraph(
            text="首先，本研究采用了深度学习方法。其次，实验结果表明该方法有效。此外，结果也显著。综上所述，具有重要意义。",
            index=0,
        )
        result = self.detector.analyze(high_risk)
        assert result["risk_level"] in ["高风险", "中高"]

        low_risk = Paragraph(
            text="方法倒是管用，不过边缘场景还得再调调——这问题之前没注意到。",
            index=0,
        )
        result = self.detector.analyze(low_risk)
        assert result["risk_level"] == "低风险"
