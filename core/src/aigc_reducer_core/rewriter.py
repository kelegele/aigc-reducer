"""改写引擎主入口 — 管理风格实例，调度改写任务。"""

import threading
from typing import Dict, List

from aigc_reducer_core import CancelledError
from aigc_reducer_core.parser import Paragraph
from aigc_reducer_core.styles import (
    ColloquialStyle,
    ClassicalStyle,
    MixedEnZhStyle,
    AcademicHumanisticStyle,
    RoughDraftStyle,
)
from aigc_reducer_core.styles.base import RewriteStyle
from aigc_reducer_core.llm_client import LLMClient


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
    """改写引擎。

    Args:
        style_name: 改写风格名称。
        llm_client: LLM 客户端实例，传递给改写风格。
        cancel_event: 可选的取消事件，用于中断长时间运行的改写任务。
    """

    def __init__(
        self,
        style_name: str,
        llm_client: LLMClient,
        cancel_event: threading.Event | None = None,
    ):
        if style_name not in STYLE_MAP:
            raise ValueError(f"未知风格: {style_name}，可选: {list(STYLE_MAP.keys())}")

        self.style: RewriteStyle = STYLE_MAP[style_name](llm_client)
        self.style_name = style_name
        self._cancel = cancel_event

    def rewrite_all(
        self,
        paragraphs: List[Paragraph],
        detection_results: List[Dict] | None = None,
    ) -> List[Paragraph]:
        """批量改写段落，支持通过 cancel_event 中断。"""
        rewritten = []
        for i, para in enumerate(paragraphs):
            if self._cancel and self._cancel.is_set():
                raise CancelledError("改写已取消")

            det_result = detection_results[i] if detection_results else {}

            if det_result.get("risk_level") == "low":
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
