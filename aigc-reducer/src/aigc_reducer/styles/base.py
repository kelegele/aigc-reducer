"""改写风格基类。"""

from abc import ABC, abstractmethod


class RewriteStyle(ABC):
    """改写风格抽象。"""

    name: str = "base"
    description: str = ""

    @abstractmethod
    def rewrite_paragraph(self, text: str, detection_result: dict) -> str:
        """改写单个段落（激进模式）。"""
        pass

    @abstractmethod
    def rewrite_paragraph_conservative(self, text: str, detection_result: dict) -> str:
        """保守改写 — 保留更多原文表达。"""
        pass

    def _call_llm(self, prompt: str) -> str:
        """调用 LLM 进行改写（占位实现，Task 8 中替换为真实 API）。"""
        return f"[LLM 改写]: {prompt[:100]}..."
