"""文言文化风格 — 四字成语、对仗句式。"""

from .base import RewriteStyle


class ClassicalStyle(RewriteStyle):
    name = "文言文化"
    description = "适当使用文言文表达，如四字成语、对仗句式"

    def rewrite_paragraph(self, text: str, detection_result: dict) -> str:
        prompt = (
            f"将以下学术文本改写为带有文言色彩的风格：适当使用四字成语、对仗句式，"
            f"融入古文表达习惯。保持核心内容不变。\n\n"
            f"原文：{text}\n\n"
            f"改写后："
        )
        return self._call_llm(prompt)

    def rewrite_paragraph_conservative(self, text: str, detection_result: dict) -> str:
        prompt = (
            f"将以下学术文本进行轻度文言化改写：仅在关键论述处使用四字成语或对仗句式，"
            f"整体保持现代汉语风格。\n\n"
            f"原文：{text}\n\n"
            f"改写后："
        )
        return self._call_llm(prompt)
