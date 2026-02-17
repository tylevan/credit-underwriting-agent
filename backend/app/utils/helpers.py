"""
Utility functions.
"""

import re

# Tool names và keywords nội bộ — KHÔNG BAO GIỜ xuất hiện trong output cho user
INTERNAL_KEYWORDS = [
    "get_customer_info",
    "get_cic_report",
    "calculate_monthly_payment",
    "calculate_dti",
    "calculate_max_loan",
    "get_credit_policy",
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

DEFLECTION_MESSAGE = (
    "Tôi là chuyên viên thẩm định tín dụng. "
    "Tôi chỉ hỗ trợ các nghiệp vụ liên quan đến thẩm định và cho vay tín dụng. "
    "Vui lòng đặt câu hỏi trong phạm vi này."
)


def sanitize_output(content: str) -> str:
    """
    Output guardrail: phát hiện và chặn response chứa thông tin nội bộ.
    Nếu LLM tiết lộ tên tool/hệ thống → thay toàn bộ bằng câu từ chối.
    """
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

