"""
Agent Nodes: Các node trong LangGraph workflow.

Nodes:
1. call_model     - Gọi LLM
2. call_tool      - Thực thi tools
3. update_notes   - Cập nhật scratchpad + reasoning_trail
4. validate       - Guardrails kiểm tra quyết định
5. human_review   - Human-in-the-Loop checkpoint
"""

import json
import logging
from datetime import datetime

from langchain_core.messages import AIMessage, ToolMessage, SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .state import AgentState
from .prompts import build_system_prompt
from ..tools import ALL_TOOLS, TOOLS_BY_NAME
from ..config.settings import settings
from ..config.policy_constants import CreditPolicy

logger = logging.getLogger(__name__)

# ── LLM Instance ──
llm = ChatGoogleGenerativeAI(
    model=settings.LLM_MODEL,
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=settings.LLM_TEMPERATURE,
)
llm_with_tools = llm.bind_tools(ALL_TOOLS)


# ════════════════════════════════════════════
# NODE 1: CALL MODEL
# ════════════════════════════════════════════

def call_model(state: AgentState) -> dict:
    """
    Gọi LLM để suy nghĩ và ra quyết định.
    Inject scratchpad + reasoning_trail vào system prompt.
    """
    messages = state["messages"]
    scratchpad = state.get("scratchpad", "")
    reasoning_trail = state.get("reasoning_trail", [])

    # Build system prompt với context
    system_msg = build_system_prompt(scratchpad, reasoning_trail)
    input_messages = [system_msg] + list(messages)

    # Gọi LLM
    response = llm_with_tools.invoke(input_messages)

    logger.info(
        "llm_called",
        extra={
            "has_tool_calls": bool(response.tool_calls),
            "tool_count": len(response.tool_calls) if response.tool_calls else 0,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

    return {"messages": [response]}


# ════════════════════════════════════════════
# NODE 2: CALL TOOL (với error handling)
# ════════════════════════════════════════════

def call_tool(state: AgentState) -> dict:
    """
    Thực thi tools được LLM yêu cầu.
    Có error handling - nếu tool fail, trả về error message thay vì crash.
    """
    last_message = state["messages"][-1]
    tool_messages = []

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]

        logger.info(f"tool_executing: {tool_name}", extra={"tool_args": tool_args})

        try:
            # Kiểm tra tool có tồn tại
            if tool_name not in TOOLS_BY_NAME:
                result = {"success": False, "error": f"Tool '{tool_name}' không tồn tại"}
            else:
                tool_func = TOOLS_BY_NAME[tool_name]
                result = tool_func.invoke(tool_args)

        except Exception as e:
            # Error handling: không crash, trả về error message
            logger.error(f"tool_error: {tool_name}", extra={"error": str(e)})
            result = {
                "success": False,
                "error": f"Lỗi khi thực thi {tool_name}: {str(e)}",
                "reasoning_step": {
                    "step": "?",
                    "action": f"Thực thi {tool_name}",
                    "result": "LỖI HỆ THỐNG",
                    "decision": "ERROR",
                    "detail": str(e)
                }
            }

        tool_messages.append(
            ToolMessage(
                content=json.dumps(result, ensure_ascii=False, default=str),
                name=tool_name,
                tool_call_id=tool_id,
            )
        )

    return {"messages": tool_messages}


# ════════════════════════════════════════════
# NODE 3: UPDATE SCRATCHPAD + REASONING TRAIL
# ════════════════════════════════════════════

def update_scratchpad(state: AgentState) -> dict:
    """
    Cập nhật Working Memory và Reasoning Trail.

    DEDUP FIX: Track existing step numbers to prevent duplicates
    when messages[-5:] overlaps with previously processed tools.
    """
    scratchpad = state.get("scratchpad", "")
    reasoning_trail = list(state.get("reasoning_trail", []))

    # Track existing steps to prevent duplicates
    existing_steps = {(r.get("step"), r.get("action")) for r in reasoning_trail}

    # Only process messages after the last HumanMessage (= current assessment scope)
    # This prevents re-adding old tool steps when trail was reset between assessments
    all_msgs = state["messages"]
    last_human_idx = 0
    for i, m in enumerate(all_msgs):
        if isinstance(m, HumanMessage):
            last_human_idx = i
    recent_messages = all_msgs[last_human_idx:]

    for msg in recent_messages:
        if not isinstance(msg, ToolMessage):
            continue

        try:
            result = json.loads(msg.content)
        except (json.JSONDecodeError, AttributeError):
            continue

        if not isinstance(result, dict):
            continue

        # Extract reasoning step (for both success and failed tools)
        reasoning_step = result.get("reasoning_step")
        if reasoning_step:
            step_key = (reasoning_step.get("step"), reasoning_step.get("action"))
            if step_key not in existing_steps:
                reasoning_trail.append(reasoning_step)
                existing_steps.add(step_key)

        if not result.get("success"):
            continue

        data = result.get("data", {})

        # Update scratchpad per tool (idempotent — check before appending)
        if msg.name == "get_customer_info" and f"KH: {data.get('full_name')}" not in scratchpad:
            scratchpad += (
                f"\n📋 KH: {data.get('full_name')}, "
                f"{data.get('age')} tuổi, "
                f"thu nhập {data.get('total_income', 0):,.0f} VND"
            )
            if not data.get('basic_eligible'):
                scratchpad += f" ⚠️ ISSUES: {data.get('eligibility_issues')}"

        elif msg.name == "get_cic_report" and f"CIC: {data.get('credit_sco')}" not in scratchpad:
            scratchpad += (
                f"\n📊 CIC: {data.get('credit_sco')}, "
                f"Nhóm nợ: {data.get('debt_group')}, "
                f"Lãi suất: {data.get('suggested_rate')}%"
            )
            if data.get("auto_reject"):
                scratchpad += f" ❌ AUTO REJECT: {data.get('auto_reject_reasons')}"

        elif msg.name == "calculate_monthly_payment" and "Trả/tháng" not in scratchpad:
            scratchpad += f"\n💰 Trả/tháng: {data.get('monthly_payment', 0):,.0f} VND"

        elif msg.name == "calculate_dti" and "DTI:" not in scratchpad:
            scratchpad += (
                f"\n📈 DTI: {data.get('dti_percent')}% - "
                f"{data.get('assessment')}"
            )

        elif msg.name == "calculate_max_loan" and "Hạn mức:" not in scratchpad:
            scratchpad += f"\n🏦 Hạn mức: {data.get('final_approved_limit', 0):,.0f} VND"

    return {
        "scratchpad": scratchpad,
        "reasoning_trail": reasoning_trail,
    }


# ════════════════════════════════════════════
# NODE 4: VALIDATE DECISION (Guardrails)
# ════════════════════════════════════════════

def validate_decision(state: AgentState) -> dict:
    """
    Guardrails: Kiểm tra quyết định cuối cùng có đúng policy không.

    Logic:
    - Nếu reasoning_trail có bất kỳ FAIL → final_decision phải là REJECTED
    - Nếu reasoning_trail có REVIEW → final_decision phải là REVIEW
    - Nếu tất cả PASS → final_decision là APPROVED
    - Override LLM nếu nó đưa ra quyết định sai policy
    """
    reasoning_trail = state.get("reasoning_trail", [])

    if not reasoning_trail:
        # Không có data từ tools → không thể validate
        return {"final_decision": None, "needs_human_review": False}

    decisions = [r.get("decision", "") for r in reasoning_trail if r]

    # Rule-based validation
    has_fail = any(d in ("FAIL",) for d in decisions)
    has_error = any(d in ("ERROR",) for d in decisions)
    has_review = any(d in ("REVIEW",) for d in decisions)

    if has_fail:
        final = "REJECTED"
        needs_review = False
    elif has_error:
        final = "REVIEW"
        needs_review = True
    elif has_review:
        final = "REVIEW"
        needs_review = True
    else:
        final = "APPROVED"
        needs_review = False

    logger.info(
        "decision_validated",
        extra={
            "final_decision": final,
            "needs_human_review": needs_review,
            "reasoning_decisions": decisions,
        }
    )

    return {
        "final_decision": final,
        "needs_human_review": needs_review,
    }


# ════════════════════════════════════════════
# NODE 5: HUMAN REVIEW (Human-in-the-Loop)
# ════════════════════════════════════════════

def human_review_node(state: AgentState) -> dict:
    """
    Human-in-the-Loop checkpoint.

    Khi needs_human_review = True:
    - Node này interrupt execution
    - Chờ human reviewer đưa ra quyết định
    - human_decision được inject từ API endpoint

    LangGraph sử dụng interrupt() để pause execution.
    """
    human_decision = state.get("human_decision")
    human_note = state.get("human_note", "")

    if human_decision:
        # Human đã review
        logger.info(
            "human_reviewed",
            extra={
                "decision": human_decision,
                "note": human_note,
            }
        )
        return {
            "final_decision": human_decision,
            "needs_human_review": False,
        }

    # Chưa có review → giữ nguyên state, sẽ được interrupt bởi graph
    return {}


# ════════════════════════════════════════════
# ROUTER: Should Continue?
# ════════════════════════════════════════════

def should_continue(state: AgentState) -> str:
    """
    Router quyết định workflow đi tiếp hay dừng.

    Returns:
        "continue": LLM yêu cầu gọi tools
        "end": LLM đã trả lời xong
    """
    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        logger.debug(f"Router: {len(last_message.tool_calls)} tool(s) → continue")
        return "continue"
    else:
        logger.debug("Router: LLM done → end")
        return "end"


def route_after_validate(state: AgentState) -> str:
    """
    Router sau validate: cần human review hay kết thúc?
    """
    if state.get("needs_human_review"):
        return "human_review"
    return "end"
