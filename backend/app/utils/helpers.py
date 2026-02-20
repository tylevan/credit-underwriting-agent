"""
Utility functions.
"""

import re

# Framework keywords nội bộ — KHÔNG BAO GIỜ xuất hiện trong output cho user
INTERNAL_KEYWORDS = [
    "system prompt",
    "scratchpad",
    "reasoning_trail",
    "bind_tools",
    "langchain",
    "langgraph",
    "AgentState",
]

# Compile regex pattern (case-insensitive)
_LEAK_PATTERN = re.compile(
    "|".join(re.escape(kw) for kw in INTERNAL_KEYWORDS),
    re.IGNORECASE,
)

# Tool code names → tên hiển thị tự nhiên cho user
TOOL_DISPLAY_NAMES = {
    "get_customer_info": "tra cứu thông tin khách hàng",
    "get_cic_report": "tra cứu báo cáo tín dụng CIC",
    "calculate_monthly_payment": "tính tiền trả hàng tháng",
    "calculate_dti": "tính tỷ lệ nợ trên thu nhập",
    "calculate_max_loan": "tính hạn mức vay tối đa",
    "get_credit_policy": "tra cứu chính sách tín dụng",
}

# Compile tool name replacement pattern
_TOOL_NAME_PATTERN = re.compile(
    "|".join(re.escape(name) for name in TOOL_DISPLAY_NAMES),
    re.IGNORECASE,
)

DEFLECTION_MESSAGE = (
    "Tôi là chuyên viên thẩm định tín dụng. "
    "Tôi chỉ hỗ trợ các nghiệp vụ liên quan đến thẩm định và cho vay tín dụng. "
    "Vui lòng đặt câu hỏi trong phạm vi này."
)


def sanitize_output(content: str) -> str:
    """
    Output guardrail:
    1. Thay tên tool code bằng tên tự nhiên (VD: get_customer_info → tra cứu thông tin khách hàng)
    2. Nếu vẫn chứa framework keywords nội bộ → chặn toàn bộ
    """
    # Step 1: Replace tool names with natural language
    content = _TOOL_NAME_PATTERN.sub(
        lambda m: TOOL_DISPLAY_NAMES.get(m.group(0).lower(), m.group(0)),
        content,
    )
    # Step 2: Block if framework keywords leaked
    if _LEAK_PATTERN.search(content):
        return DEFLECTION_MESSAGE
    return content


def clean_agent_content(content) -> str:
    """
    Làm sạch nội dung trả về từ Google Gemini.
    Nếu content là list (chứa metadata), ghép các phần text lại.
    """
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "".join([
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and "text" in part
        ])
    else:
        text = str(content)

    return sanitize_output(text)

