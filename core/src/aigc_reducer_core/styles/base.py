"""改写风格基类。"""

from abc import ABC, abstractmethod

from aigc_reducer_core.llm_client import LLMClient


class RewriteStyle(ABC):
    """改写风格抽象基类。

    所有改写风格必须接收 LLMClient 实例，
    不再通过 from_env() 隐式创建客户端。
    """

    name: str = "base"
    description: str = ""

    def __init__(self, llm_client: LLMClient):
        self._llm_client = llm_client

    @abstractmethod
    def rewrite_paragraph(self, text: str, detection_result: dict) -> str:
        """改写单个段落（激进模式）。"""
        pass

    @abstractmethod
    def rewrite_paragraph_conservative(self, text: str, detection_result: dict) -> str:
        """保守改写 — 保留更多原文表达。"""
        pass

    def _call_llm(self, prompt: str) -> str:
        """调用 LLM 进行改写。"""
        try:
            return self._llm_client.chat(prompt)
        except Exception as e:
            return f"[LLM 调用失败: {e}]"
