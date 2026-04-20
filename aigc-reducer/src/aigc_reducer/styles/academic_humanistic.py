"""学术人文化风格 — 主观评价、疑问句、个人见解。"""

from .base import RewriteStyle


class AcademicHumanisticStyle(RewriteStyle):
    name = "学术人文化"
    description = "保持学术严谨但加入个人化表达、主观评价、疑问句式"

    def rewrite_paragraph(self, text: str, detection_result: dict) -> str:
        prompt = (
            f"将以下学术文本改写为学术人文化风格：保持学术严谨性的同时，"
            f"加入主观评价、个人见解、疑问句式（如'笔者认为'、'值得我们注意的是'、'是否...？'）。"
            f"注入批判性思考，避免纯陈述式表达。\n\n"
            f"原文：{text}\n\n"
            f"改写后："
        )
        return self._call_llm(prompt)

    def rewrite_paragraph_conservative(self, text: str, detection_result: dict) -> str:
        prompt = (
            f"将以下学术文本进行轻度人文化改写：保留学术框架，仅在关键论述处"
            f"加入个人观点或疑问句，不要过度主观化。\n\n"
            f"原文：{text}\n\n"
            f"改写后："
        )
        return self._call_llm(prompt)
