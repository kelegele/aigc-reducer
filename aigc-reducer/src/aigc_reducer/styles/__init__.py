"""改写风格模块。"""

from .colloquial import ColloquialStyle
from .classical import ClassicalStyle
from .mixed_en_zh import MixedEnZhStyle
from .academic_humanistic import AcademicHumanisticStyle
from .rough_draft import RoughDraftStyle

__all__ = [
    "ColloquialStyle",
    "ClassicalStyle",
    "MixedEnZhStyle",
    "AcademicHumanisticStyle",
    "RoughDraftStyle",
]
