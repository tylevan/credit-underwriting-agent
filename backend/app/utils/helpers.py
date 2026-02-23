"""
Utility functions.
"""

import re

# Framework keywords nội bộ — KHÔNG BAO GIỜ xuất hiện trong output cho user
INTERNAL_KEYWORDS = [
    "system prompt",
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


def normalize_chat_message(message: str) -> str:
    """
    Chuẩn hoá các câu chat ngắn/viết tắt để LLM nhận diện đúng đây là
    yêu cầu thẩm định tín dụng (tránh false deflection).

    Ví dụ: "cccd 1987 vay 100 tr trong 2 năm"
    → "Yêu cầu thẩm định tín dụng: CCCD 1987, vay 100 tr trong 2 năm."
    """
    text = (message or "").strip()
    if not text:
        return text

    lower = text.lower()
    has_credit_signal = any(keyword in lower for keyword in (
        "cccd", "cmnd", "vay", "khoản vay", "tín dụng", "lãi suất", "dti", "cic",
    ))

    # Parse shorthand có cấu trúc: cccd + số tiền vay + kỳ hạn
    id_match = re.search(r"(?:cccd|cmnd)\s*[:\-]?\s*(\d{4,15})", lower)
    amount_match = re.search(r"vay\s*(\d+[\d.,]*)\s*(tỷ|ty|triệu|tr|vnd|đồng)?", lower)
    term_match = re.search(
        r"(?:trong|kỳ hạn)\s*(\d+)\s*(năm|tháng|month|months)|"
        r"(\d+)\s*(năm|tháng|month|months)",
        lower,
    )

    if has_credit_signal and id_match and amount_match and term_match:
        s = amount_match.group(1)
        if "." in s and "," in s:
            decimal_sep = "." if s.rfind(".") > s.rfind(",") else ","
            thousand_sep = "," if decimal_sep == "." else "."
            normalized_amount = s.replace(thousand_sep, "")
            if decimal_sep == ",":
                normalized_amount = normalized_amount.replace(",", ".")
        elif "," in s:
            normalized_amount = s.replace(",", ".")
        else:
            normalized_amount = s

        amount_value = float(normalized_amount)
        amount_unit = (amount_match.group(2) or "vnd").strip()

        if amount_unit in ("tỷ", "ty"):
            amount_value *= 1_000_000_000
        elif amount_unit in ("triệu", "tr"):
            amount_value *= 1_000_000

        term_value = int(term_match.group(1) or term_match.group(3))
        term_unit = (term_match.group(2) or term_match.group(4) or "tháng").strip()
        term_months = term_value * 12 if term_unit == "năm" else term_value

        return (
            "Yêu cầu thẩm định tín dụng: "
            f"CCCD {id_match.group(1)}, "
            f"số tiền vay {amount_value:,.0f} VND, "
            f"kỳ hạn {term_months} tháng."
        )

    # Fallback cho tin nhắn ngắn kiểu command/keyword
    if has_credit_signal and len(text) <= 120 and "thẩm định" not in lower:
        suffix = "" if text.endswith((".", "?", "!")) else "."
        return f"Yêu cầu thẩm định tín dụng: {text}{suffix}"

    return text
