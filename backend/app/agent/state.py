"""
Agent State Definition.
Chứa tất cả state fields cho LangGraph workflow.
"""

from typing import Annotated, Sequence, TypedDict, Optional
from typing_extensions import NotRequired
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    State của Credit Underwriting Agent.

    Fields:
        messages: Lịch sử hội thoại (auto-append qua add_messages).
        underwriting_state: Runtime state có cấu trúc lấy từ tool outputs.
        reasoning_trail: Danh sách structured reasoning từ tools (audit trail).
        needs_human_review: Flag yêu cầu human review.
        human_decision: Quyết định từ human reviewer (APPROVED/REJECTED).
        human_note: Ghi chú từ reviewer.
        final_decision: Quyết định cuối cùng sau guardrails.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    underwriting_state: NotRequired[dict]
    reasoning_trail: NotRequired[list[dict]]
    needs_human_review: NotRequired[bool]
    human_decision: NotRequired[Optional[str]]
    human_note: NotRequired[Optional[str]]
    final_decision: NotRequired[Optional[str]]
