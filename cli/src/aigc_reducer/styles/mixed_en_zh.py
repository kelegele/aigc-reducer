"""中英混杂风格 — 插入英文术语、短语。"""

from .base import RewriteStyle


class MixedEnZhStyle(RewriteStyle):
    name = "中英混杂化"
    description = "在适当位置插入英文术语、短语"

    def rewrite_paragraph(self, text: str, detection_result: dict) -> str:
        prompt = (
            f"将以下中文学术文本改写为中英混杂风格：在适当位置（如专业术语、概念名称、技术方法）"
            f"插入英文原文。模拟学术写作中中英夹杂的真实习惯。\n\n"
            f"原文：{text}\n\n"
            f"改写后："
        )
        return self._call_llm(prompt)

    def rewrite_paragraph_conservative(self, text: str, detection_result: dict) -> str:
        prompt = (
            f"将以下中文学术文本进行轻度改写：仅在关键专业术语处插入英文原文，"
            f"其余部分保持中文。保持学术严谨。\n\n"
            f"原文：{text}\n\n"
            f"改写后："
        )
        return self._call_llm(prompt)
