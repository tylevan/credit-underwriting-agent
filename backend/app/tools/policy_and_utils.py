"""
Utility Tools: Policy Lookup.
"""

from langchain_core.tools import tool

from ..config.policy_constants import CreditPolicy


# ════════════════════════════════════════════
# TOOL: GET CREDIT POLICY
# ════════════════════════════════════════════

@tool("get_credit_policy")
def get_credit_policy() -> dict:
    """
    Tra cứu Chính sách Tín dụng hiện hành.
    Trả về: bảng ngưỡng DTI, CIC, lãi suất, hạn mức theo policy.
    """
    return {
        "success": True,
        "data": {
            "readable_summary": CreditPolicy.get_readable_policy(),
            "thresholds": {
                "age": f"{CreditPolicy.AGE_MIN}-{CreditPolicy.AGE_MAX}",
                "cic_reject": f"< {CreditPolicy.CIC_AUTO_REJECT}",
                "dti_pass": f"<= {CreditPolicy.DTI_PASS}%",
                "dti_review": f"{CreditPolicy.DTI_PASS}-{CreditPolicy.DTI_REVIEW}%",
                "dti_reject": f"> {CreditPolicy.DTI_REVIEW}%",
                "bad_debt_groups": CreditPolicy.BAD_DEBT_GROUPS,
            }
        },
        "reasoning_step": None  # Tool thông tin, không cần reasoning
    }

