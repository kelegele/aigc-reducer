"""AIGC 检测主入口 — 支持规则引擎和 LLM 反查两种模式。"""

import threading
from typing import Dict, List, Literal

from aigc_reducer_core import CancelledError
from aigc_reducer_core.parser import Paragraph
from aigc_reducer_core.detectors import (
    PerplexityDetector,
    BurstinessDetector,
    ConnectorDetector,
    CognitiveDetector,
    SemanticFingerprintDetector,
)
from aigc_reducer_core.detectors.llm_detector import LLMDetector
from aigc_reducer_core.llm_client import LLMClient


RISK_LEVELS = [
    (10, "低风险"),
    (30, "中风险"),
    (60, "中高"),
    (100, "高风险"),
]


class AIGCDetector:
    """AIGC 检测主类，支持两种模式。

    Args:
        mode: "rules" 为纯规则引擎（快速），"llm" 为 LLM 反查（精准）。
        llm_client: LLM 客户端实例（llm 模式必需）。
        cancel_event: 可选的取消事件，用于中断长时间运行的检测任务。
    """

    def __init__(
        self,
        mode: Literal["rules", "llm"] = "rules",
        llm_client: LLMClient | None = None,
        cancel_event: threading.Event | None = None,
    ):
        self.mode = mode
        self._cancel = cancel_event

        if mode == "llm":
            if llm_client is None:
                raise ValueError("llm 模式必须传入 llm_client 参数")
            self.llm_detector = LLMDetector(llm_client)
        else:
            self.perplexity = PerplexityDetector()
            self.burstiness = BurstinessDetector()
            self.connectors = ConnectorDetector()
            self.cognitive = CognitiveDetector()
            self.semantic = SemanticFingerprintDetector()

    def analyze(self, paragraph: Paragraph) -> Dict:
        if self.mode == "llm":
            result = self.llm_detector.analyze(paragraph)
            # 移除内部字段，保持对外接口一致
            result.pop("_llm_raw", None)
            return result

        p_score = self.perplexity.analyze(paragraph)
        b_score = self.burstiness.analyze(paragraph)
        c_score = self.connectors.analyze(paragraph)
        cog_score = self.cognitive.analyze(paragraph)
        s_score = self.semantic.analyze(paragraph)

        composite = (
            p_score * 0.20
            + b_score * 0.20
            + c_score * 0.20
            + cog_score * 0.20
            + s_score * 0.20
        )

        risk_level = self._classify(composite)

        features = []
        if p_score > 50:
            features.append("困惑度过低：用词过于标准化")
        if b_score > 50:
            features.append("突发性缺失：句式长度高度统一")
        if cog_score > 50:
            features.append("认知特征缺失：无批判性观点，纯陈述")
        if s_score > 50:
            features.append("语义指纹：语义组织方式符合AI逻辑")
        if c_score > 30:
            features.append("模板化连接词过多")

        return {
            "paragraph_index": paragraph.index,
            "perplexity_score": round(p_score, 1),
            "burstiness_score": round(b_score, 1),
            "connector_score": round(c_score, 1),
            "cognitive_score": round(cog_score, 1),
            "semantic_score": round(s_score, 1),
            "composite_score": round(composite, 1),
            "risk_level": risk_level,
            "ai_features": features,
        }

    def analyze_all(self, paragraphs: List[Paragraph]) -> List[Dict]:
        """分析所有段落，支持通过 cancel_event 中断。"""
        results = []
        for p in paragraphs:
            if self._cancel and self._cancel.is_set():
                raise CancelledError("检测已取消")
            results.append(self.analyze(p))
        return results

    def _classify(self, score: float) -> str:
        for threshold, level in RISK_LEVELS:
            if score < threshold:
                return level
        return "高风险"
