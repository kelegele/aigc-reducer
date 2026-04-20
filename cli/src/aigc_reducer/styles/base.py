"""改写风格基类。"""

import os

from abc import ABC, abstractmethod

from aigc_reducer.llm_client import LLMClient


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
        """通过 OpenAI 兼容 API 调用 LLM 进行改写。

        支持供应商：DeepSeek / 通义千问 / 智谱 / OpenAI
        配置方式：环境变量或 ~/.aigc-reducer/config.yaml
        """
        try:
            client = LLMClient.from_env()
            return client.chat(prompt)
        except Exception as e:
            return f"[LLM 调用失败: {e}]"
