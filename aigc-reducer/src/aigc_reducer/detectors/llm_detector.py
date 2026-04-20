"""LLM 反查检测器 — 用 LLM 模拟商业平台判断，评估段落 AIGC 风险。"""

from typing import Dict, Optional
from aigc_reducer.parser import Paragraph
from aigc_reducer.llm_client import LLMClient


SYSTEM_PROMPT = """你是一个专业的学术论文 AIGC 检测专家。请分析以下文本的 AI 生成可能性，并输出严格格式的 JSON 结果。

评估维度：
1. 困惑度：文本是否过于流畅、用词是否过于标准化
2. 突发性：句子长度和句式是否缺乏变化
3. 模板化连接词：是否高频使用"首先/其次/此外/综上所述"等
4. 认知特征：是否缺乏批判性思考、个人观点、实证数据
5. 语义指纹：语义组织方式是否符合 AI 标准论证结构

输出格式（必须是合法 JSON，不要包含任何其他文本）：
{
  "score": 0-100的整数,
  "perplexity": 0-100,
  "burstiness": 0-100,
  "connector": 0-100,
  "cognitive": 0-100,
  "semantic": 0-100,
  "features": ["检测到的AI特征1", "检测到的AI特征2"]
}

分数说明：
- 0-10：低风险（人类写作）
- 10-30：中风险
- 30-60：中高
- 60-100：高风险"""


class LLMDetector:
    """用 LLM 反查评估段落的 AIGC 风险。"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self._client = llm_client or LLMClient.from_env()

    def analyze(self, paragraph: Paragraph) -> Dict:
        """用 LLM 分析单个段落。

        Returns:
            与规则检测器相同格式的 Dict
        """
        text = paragraph.text

        # 短文本/标题直接跳过
        if len(text) < 20:
            return {
                "paragraph_index": paragraph.index,
                "perplexity_score": 15,
                "burstiness_score": 15,
                "connector_score": 10,
                "cognitive_score": 15,
                "semantic_score": 15,
                "composite_score": 14,
                "risk_level": "中风险",
                "ai_features": ["文本过短，无法准确判断"],
                "_llm_raw": None,
            }

        prompt = f"""请分析以下学术文本的 AIGC 风险：

{text}"""

        try:
            raw = self._client.chat(prompt, system_prompt=SYSTEM_PROMPT)
            result = self._parse_llm_output(raw)
        except Exception as e:
            raw = None
            result = self._fallback(text, paragraph.index, str(e))

        features = result.pop("features", [])
        perplexity = result.get("perplexity", 30)
        burstiness = result.get("burstiness", 25)
        connector = result.get("connector", 15)
        cognitive = result.get("cognitive", 30)
        semantic = result.get("semantic", 25)

        composite = (
            perplexity * 0.20
            + burstiness * 0.20
            + connector * 0.20
            + cognitive * 0.20
            + semantic * 0.20
        )

        risk_level = self._classify(composite)

        return {
            "paragraph_index": paragraph.index,
            "perplexity_score": perplexity,
            "burstiness_score": burstiness,
            "connector_score": connector,
            "cognitive_score": cognitive,
            "semantic_score": semantic,
            "composite_score": round(composite, 1),
            "risk_level": risk_level,
            "ai_features": features,
            "_llm_raw": raw[:200] if raw else None,
        }

    def _parse_llm_output(self, raw: str) -> Dict:
        """解析 LLM 的 JSON 输出。"""
        import json
        import re

        # 提取 JSON 块（可能被 markdown 包裹）
        json_match = re.search(r"\{[\s\S]*\}", raw)
        if not json_match:
            raise ValueError(f"无法解析 JSON: {raw[:200]}")

        return json.loads(json_match.group())

    def _fallback(self, text: str, index: int, error: str) -> Dict:
        """LLM 调用失败时降级到中等风险。"""
        return {
            "perplexity": 40,
            "burstiness": 35,
            "connector": 20,
            "cognitive": 40,
            "semantic": 35,
            "score": 34,
            "features": [f"LLM 检测失败，降级评估: {error[:80]}"],
        }

    def _classify(self, score: float) -> str:
        if score < 10:
            return "低风险"
        elif score < 30:
            return "中风险"
        elif score < 60:
            return "中高"
        else:
            return "高风险"
