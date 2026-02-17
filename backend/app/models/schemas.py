"""
Pydantic Schemas cho API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Request Models ──

class AssessmentRequest(BaseModel):
    """Request thẩm định tín dụng."""
    customer_id: str = Field(..., description="ID khách hàng")
    loan_amount: float = Field(..., gt=0, le=1_200_000_000, description="Số tiền vay (VND), tối đa 1.2 tỷ")
    term_months: int = Field(..., gt=0, le=60, description="Kỳ hạn vay (tháng), tối đa 60 tháng")


class ChatRequest(BaseModel):
    """Request chat tự do."""
    message: str = Field(..., min_length=1, description="Tin nhắn từ user")
    thread_id: Optional[str] = Field(None, description="Thread ID để duy trì context")


class HumanReviewRequest(BaseModel):
    """Request từ human reviewer."""
    thread_id: str
    decision: str = Field(..., pattern="^(APPROVED|REJECTED)$")
    reviewer_note: str = Field("", description="Ghi chú từ reviewer")


# ── Response Models ──

class AssessmentResponse(BaseModel):
    """Response thẩm định."""
    success: bool
    thread_id: str
    decision: Optional[str] = None  # APPROVED / REVIEW / REJECTED
    report: Optional[str] = None
    reasoning_trail: list[dict] = Field(default_factory=list)
    needs_human_review: bool = False
    error: Optional[str] = None


class ChatResponse(BaseModel):
    """Response chat."""
    success: bool
    thread_id: str
    message: str
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
