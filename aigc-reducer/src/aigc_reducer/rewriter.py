"""改写引擎主入口 — 管理风格实例，调度改写任务。"""

from typing import Dict, List, Optional
from aigc_reducer.parser import Paragraph
from aigc_reducer.styles import (
    ColloquialStyle,
    ClassicalStyle,
    MixedEnZhStyle,
    AcademicHumanisticStyle,
    RoughDraftStyle,
)
from aigc_reducer.styles.base import RewriteStyle


STYLE_MAP = {
    "口语化": ColloquialStyle,
    "文言文化": ClassicalStyle,
    "中英混杂化": MixedEnZhStyle,
    "学术人文化": AcademicHumanisticStyle,
    "粗犷草稿风": RoughDraftStyle,
}


def list_styles() -> List[str]:
    """列出所有可用风格。"""
    return list(STYLE_MAP.keys())


class Rewriter:
    """改写引擎。"""

    def __init__(self, style_name: str):
        if style_name not in STYLE_MAP:
            raise ValueError(f"未知风格: {style_name}，可选: {list(STYLE_MAP.keys())}")

        self.style: RewriteStyle = STYLE_MAP[style_name]()
        self.style_name = style_name

    def rewrite_all(
        self,
        paragraphs: List[Paragraph],
        detection_results: Optional[List[Dict]] = None,
    ) -> List[Paragraph]:
        rewritten = []
        for i, para in enumerate(paragraphs):
            det_result = detection_results[i] if detection_results else {}

            if det_result.get("risk_level") == "低风险":
                rewritten.append(para)
                continue

            new_text = self.style.rewrite_paragraph(para.text, det_result)
            rewritten.append(Paragraph(
                text=new_text,
                index=para.index,
                is_heading=para.is_heading,
                has_formula=para.has_formula,
                has_code=para.has_code,
                original_format=para.original_format,
            ))

        return rewritten

    def rewrite_single(
        self,
        text: str,
        detection_result: Dict,
        conservative: bool = False,
    ) -> str:
        if conservative:
            return self.style.rewrite_paragraph_conservative(text, detection_result)
        else:
            return self.style.rewrite_paragraph(text, detection_result)
