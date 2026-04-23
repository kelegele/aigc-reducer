"""AIGC 检测与改写核心库 — 段落检测、风险评分、多风格改写。"""

__version__ = "0.1.0"


class CancelledError(Exception):
    """用户取消操作时抛出的异常。"""
