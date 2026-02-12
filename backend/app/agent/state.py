"""
Agent State Definition.
Chứa tất cả state fields cho LangGraph workflow.
"""

from typing import Annotated, Sequence, TypedDict, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    State của Credit Underwriting Agent.

    Fields:
        messages: Lịch sử hội thoại (auto-append qua add_messages).
        scratchpad: Working memory ngắn gọn cho LLM.
        reasoning_trail: Danh sách structured reasoning từ tools (audit trail).
        needs_human_review: Flag yêu cầu human review.
        human_decision: Quyết định từ human reviewer (APPROVED/REJECTED).
        human_note: Ghi chú từ reviewer.
        final_decision: Quyết định cuối cùng sau guardrails.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    scratchpad: str
    reasoning_trail: list[dict]
    needs_human_review: bool
    human_decision: Optional[str]
    human_note: Optional[str]
    final_decision: Optional[str]
