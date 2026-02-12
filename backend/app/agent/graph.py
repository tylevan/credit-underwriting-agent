"""
LangGraph Workflow: Credit Underwriting Agent.

Graph structure:
  START → llm → [should_continue?]
                   ├── continue → tools → update_notes → llm (loop)
                   └── end → validate → [route_after_validate?]
                                            ├── human_review → END
                                            └── end → END
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .nodes import (
    call_model,
    call_tool,
    update_scratchpad,
    validate_decision,
    human_review_node,
    should_continue,
    route_after_validate,
)


def build_graph(checkpointer=None):
    """
    Build và compile LangGraph workflow.

    Args:
        checkpointer: MemorySaver instance cho conversation memory.
                     Nếu None, tạo mới.

    Returns:
        Compiled graph (runnable agent)
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    # Tạo graph
    workflow = StateGraph(AgentState)

    # Thêm nodes
    workflow.add_node("llm", call_model)
    workflow.add_node("tools", call_tool)
    workflow.add_node("update_notes", update_scratchpad)
    workflow.add_node("validate", validate_decision)
    workflow.add_node("human_review", human_review_node)

    # Entry point
    workflow.set_entry_point("llm")

    # Edges
    # LLM → tools (nếu cần) hoặc validate (nếu xong)
    workflow.add_conditional_edges(
        "llm",
        should_continue,
        {
            "continue": "tools",
            "end": "validate",
        }
    )

    # Tools → update notes → LLM (loop)
    workflow.add_edge("tools", "update_notes")
    workflow.add_edge("update_notes", "llm")

    # Validate → human review (nếu cần) hoặc END
    workflow.add_conditional_edges(
        "validate",
        route_after_validate,
        {
            "human_review": "human_review",
            "end": END,
        }
    )

    # Human review → END
    workflow.add_edge("human_review", END)

    # Compile với checkpointer
    agent = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],  # Interrupt trước human review
    )

    return agent


# Singleton instance
_memory = MemorySaver()
credit_agent = build_graph(checkpointer=_memory)
