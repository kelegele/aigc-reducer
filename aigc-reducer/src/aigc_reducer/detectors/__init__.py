"""AI 特征检测模块 — 包含 5 个独立检测器。"""

from .perplexity import PerplexityDetector
from .burstiness import BurstinessDetector
from .connectors import ConnectorDetector
from .cognitive import CognitiveDetector
from .semantic_fingerprint import SemanticFingerprintDetector

__all__ = [
    "PerplexityDetector",
    "BurstinessDetector",
    "ConnectorDetector",
    "CognitiveDetector",
    "SemanticFingerprintDetector",
]
