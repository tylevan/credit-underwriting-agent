"""
Utility functions.
"""


def clean_agent_content(content) -> str:
    """
    Làm sạch nội dung trả về từ Google Gemini.
    Nếu content là list (chứa metadata), ghép các phần text lại.
    """
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        return "".join([
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and "text" in part
        ])
    return str(content)
