"""口语化风格 — 日常表达，自然停顿，降低学术腔调。"""

from .base import RewriteStyle


class ColloquialStyle(RewriteStyle):
    name = "口语化"
    description = "日常化表达，降低学术腔调，增加自然停顿"

    def rewrite_paragraph(self, text: str, detection_result: dict) -> str:
        ai_features = detection_result.get("ai_features", [])
        feature_hint = "，".join(ai_features) if ai_features else ""
        prompt = (
            f"将以下学术文本改写为口语化风格：用日常表达、自然停顿，降低学术腔调。"
            f"保持原意不变，但要让它听起来像一个人自然说话的方式。"
            f"检测到的 AI 特征：{feature_hint}\n\n"
            f"原文：{text}\n\n"
            f"改写后："
        )
        return self._call_llm(prompt)

    def rewrite_paragraph_conservative(self, text: str, detection_result: dict) -> str:
        prompt = (
            f"将以下学术文本进行轻度口语化改写：保留学术框架和核心术语，"
            f"只在连接词和过渡处使用更自然的口语表达。不要改得太口语化。\n\n"
            f"原文：{text}\n\n"
            f"改写后："
        )
        return self._call_llm(prompt)
