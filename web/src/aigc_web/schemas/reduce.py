# web/src/aigc_web/schemas/reduce.py
"""P3 检测/改写相关的请求/响应模型。"""

from pydantic import BaseModel


class ParagraphChoiceRequest(BaseModel):
    choice: str  # "aggressive" | "conservative" | "original" | "manual"
    manual_text: str | None = None  # choice="manual" 时必填


class CreditsEstimateResponse(BaseModel):
    estimated_credits: int
    current_balance: int
    sufficient: bool


class ParagraphResponse(BaseModel):
    index: int
    original_text: str
    is_heading: bool
    has_formula: bool
    has_code: bool
    risk_level: str | None = None
    composite_score: float | None = None
    detection_detail: dict | None = None
    rewrite_aggressive: str | None = None
    rewrite_conservative: str | None = None
    user_choice: str | None = None
    final_text: str | None = None
    status: str

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    id: str
    title: str
    status: str
    detect_mode: str
    style: str
    full_reconstruct: bool
    total_credits: int
    original_text: str
    reduced_text: str | None = None
    created_at: str
    completed_at: str | None = None
    paragraphs: list[ParagraphResponse]

    model_config = {"from_attributes": True}


class TaskListItem(BaseModel):
    id: str
    title: str
    status: str
    style: str
    total_credits: int
    paragraph_count: int
    created_at: str
    completed_at: str | None = None


class TaskListResponse(BaseModel):
    items: list[TaskListItem]
    total: int
    page: int
    page_size: int


class UserStatsResponse(BaseModel):
    detection_count: int
    rewritten_paragraphs: int
    pass_rate: float
