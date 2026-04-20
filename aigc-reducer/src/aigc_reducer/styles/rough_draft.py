"""粗犷草稿风 — 短句为主，轻微语法不连贯。"""

from .base import RewriteStyle


class RoughDraftStyle(RewriteStyle):
    name = "粗犷草稿风"
    description = "短句为主，刻意制造轻微语法不连贯，模拟人类初稿特征"

    def rewrite_paragraph(self, text: str, detection_result: dict) -> str:
        prompt = (
            f"将以下学术文本改写为粗犷草稿风格：使用短句为主，"
            f"刻意制造轻微的语法不连贯和表达跳跃感，模拟人类初稿未经精修的特征。"
            f"保持核心内容可理解。\n\n"
            f"原文：{text}\n\n"
            f"改写后："
        )
        return self._call_llm(prompt)

    def rewrite_paragraph_conservative(self, text: str, detection_result: dict) -> str:
        prompt = (
            f"将以下学术文本改写为较简洁的版本：多用短句，减少冗长修饰，"
            f"保留学术深度但不要求精修。\n\n"
            f"原文：{text}\n\n"
            f"改写后："
        )
        return self._call_llm(prompt)
