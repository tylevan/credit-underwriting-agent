"""
Utility Tools: Policy Lookup, Customer Summary, List Customers.
"""

import pandas as pd
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from ..config.policy_constants import CreditPolicy
from ..models.database import get_customer_by_id, list_all_customers, get_total_customer_count


# ════════════════════════════════════════════
# TOOL 9: GET CREDIT POLICY
# ════════════════════════════════════════════

@tool("get_credit_policy")
def get_credit_policy() -> dict:
    """
    Tra cứu Chính sách Tín dụng hiện hành.

    Dùng khi:
    - Khách hàng hỏi về điều kiện vay, lãi suất, hạn mức
    - Cần giải thích lý do hồ sơ bị từ chối
    - Cần tham chiếu ngưỡng DTI và CIC
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


# ════════════════════════════════════════════
# TOOL 6: CUSTOMER SUMMARY
# ════════════════════════════════════════════

class CustomerSummaryInput(BaseModel):
    customer_id: str = Field(description="ID của khách hàng")


@tool("get_customer_summary", args_schema=CustomerSummaryInput)
def get_customer_summary(customer_id: str) -> dict:
    """
    Lấy tổng hợp nhanh thông tin khách hàng + CIC trong 1 lần gọi.

    Dùng khi cần xem nhanh tổng quan trước khi thẩm định chi tiết.
    """
    try:
        customer = get_customer_by_id(int(customer_id))

        if customer is None:
            return {"success": False, "error": f"Không tìm thấy khách hàng ID: {customer_id}"}

        age = int(customer.get('age', 0))
        tenure = float(customer.get('tenure_ye', 0))
        credit_score = int(customer.get('credit_sco', 0))
        risk_score = float(customer.get('risk_score', 0)) if pd.notna(customer.get('risk_score')) else 0
        balance = float(customer.get('balance', 0))
        monthly_ir = float(customer.get('monthly_ir', 0)) if pd.notna(customer.get('monthly_ir')) else 0

        debt_info = CreditPolicy.get_debt_group(risk_score)

        # Kiểm tra điều kiện
        issues = []
        if not (CreditPolicy.AGE_MIN <= age <= CreditPolicy.AGE_MAX):
            issues.append(f"Tuổi {age} ngoài khoảng {CreditPolicy.AGE_MIN}-{CreditPolicy.AGE_MAX}")
        if credit_score < CreditPolicy.CIC_AUTO_REJECT:
            issues.append(f"CIC {credit_score} < {CreditPolicy.CIC_AUTO_REJECT}")
        if debt_info["is_bad"]:
            issues.append(f"Nhóm nợ {debt_info['group']} (nợ xấu)")

        summary = {
            "customer_id": customer_id,
            "full_name": customer.get('full_name'),
            "age": age,
            "occupation": customer.get('occupation'),
            "customer_segment": customer.get('customer_segment'),
            "total_income": balance + monthly_ir,
            "credit_score": credit_score,
            "risk_score": round(risk_score, 4),
            "debt_group": debt_info["group"],
            "debt_group_name": debt_info["name"],
            "preliminary_eligible": len(issues) == 0,
            "issues": issues,
            "recommendation": "Có thể tiếp tục thẩm định" if len(issues) == 0 else "Cần xem xét kỹ hoặc từ chối"
        }

        return {"success": True, "data": summary, "reasoning_step": None}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ════════════════════════════════════════════
# TOOL 7: LIST CUSTOMERS
# ════════════════════════════════════════════

@tool("list_customers")
def list_customers() -> dict:
    """
    Liệt kê danh sách khách hàng trong hệ thống.

    Dùng khi cần biết có những khách hàng nào hoặc tìm ID.
    Trả về tối đa 20 khách hàng đầu tiên.
    """
    try:
        customers = list_all_customers(limit=20)
        total = get_total_customer_count()

        return {
            "success": True,
            "data": {
                "total_count": total,
                "showing": len(customers),
                "customers": customers,
            },
            "reasoning_step": None
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
