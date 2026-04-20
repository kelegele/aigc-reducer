"""改写风格基类。"""

import os

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
        """通过 Anthropic SDK 调用 Claude 进行改写。"""
        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                system="你是一个专业的学术论文改写助手。请严格按照用户要求的风格改写文本，保持学术严谨性和核心内容不变。只输出改写后的文本，不要添加任何解释。",
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except ImportError:
            return f"[LLM 改写]: {prompt[:100]}..."
        except Exception as e:
            return f"[LLM 调用失败: {e}]"
