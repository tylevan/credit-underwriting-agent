"""
Tool: Get Customer Info
Lấy thông tin khách hàng từ Core Banking.
"""

import pandas as pd
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from ..config.policy_constants import CreditPolicy
from ..models.database import get_customer_by_id


class CustomerInfoInput(BaseModel):
    customer_id: str = Field(description="ID của khách hàng (cột 'id' trong hệ thống)")


@tool("get_customer_info", args_schema=CustomerInfoInput)
def get_customer_info(customer_id: str) -> dict:
    """
    Lấy thông tin khách hàng từ Core Banking.

    DÙNG TOOL NÀY ĐẦU TIÊN khi bắt đầu thẩm định.

    TOOL TRẢ VỀ:
    - full_name, age, gender, occupation, address, origin_province
    - balance: Số dư tài khoản / Thu nhập ước tính (VND)
    - monthly_ir: Thu nhập hàng tháng khác (VND)
    - tenure_ye: Số năm làm việc
    - married: Tình trạng hôn nhân (0: Độc thân, 1: Đã kết hôn)
    - customer_segment: Phân khúc KH (Priority/Standard/Basic)
    - total_income: balance + monthly_ir
    - net_income: total_income - chi phí ước tính

    KIỂM TRA NGAY:
    - age: Phải từ 18-60 tuổi
    """
    try:
        customer = get_customer_by_id(int(customer_id))

        if customer is None:
            return {
                "success": False,
                "error": f"Không tìm thấy khách hàng với ID: {customer_id}",
                "reasoning_step": {
                    "step": 1,
                    "action": "Tra cứu thông tin khách hàng",
                    "result": "KHÔNG TÌM THẤY",
                    "decision": "FAIL",
                    "detail": f"ID {customer_id} không tồn tại trong hệ thống"
                }
            }

        # Tính toán
        age = int(customer.get('age', 0))
        tenure_years = float(customer.get('tenure_ye', 0))
        balance = float(customer.get('balance', 0))
        monthly_ir = float(customer.get('monthly_ir', 0)) if pd.notna(customer.get('monthly_ir')) else 0

        total_income = balance + monthly_ir

        # Kiểm tra điều kiện
        age_eligible = CreditPolicy.AGE_MIN <= age <= CreditPolicy.AGE_MAX

        eligibility_issues = []
        if not age_eligible:
            eligibility_issues.append(
                f"Tuổi {age} không trong khoảng {CreditPolicy.AGE_MIN}-{CreditPolicy.AGE_MAX}"
            )

        basic_eligible = len(eligibility_issues) == 0

        # Build data
        data = {
            "customer_id": customer_id,
            "full_name": customer.get('full_name'),
            "age": age,
            "gender": customer.get('gender'),
            "occupation": customer.get('occupation'),
            "address": customer.get('address'),
            "origin_province": customer.get('origin_province'),
            "balance": balance,
            "monthly_ir": monthly_ir,
            "tenure_ye": tenure_years,
            "tenure_months": int(tenure_years * 12),
            "married": customer.get('married'),
            "customer_segment": customer.get('customer_segment'),
            "loyalty_level": customer.get('loyalty_level'),
            "total_income": total_income,
            "age_eligible": age_eligible,
            "eligibility_issues": eligibility_issues,
            "basic_eligible": basic_eligible,
        }

        # Structured reasoning
        if basic_eligible:
            decision = "PASS"
            detail = (
                f"Tuổi {age} ✅ (trong {CreditPolicy.AGE_MIN}-{CreditPolicy.AGE_MAX}). "
                f"Thu nhập: {total_income:,.0f} VND/tháng."
            )
        else:
            decision = "FAIL"
            detail = "AUTO REJECT: " + "; ".join(eligibility_issues)

        reasoning_step = {
            "step": 1,
            "action": "Kiểm tra thông tin & điều kiện cơ bản khách hàng",
            "result": f"{customer.get('full_name')}, {age} tuổi, thu nhập {total_income:,.0f} VND",
            "policy_ref": "Mục 1 - Điều kiện khách hàng",
            "decision": decision,
            "detail": detail,
        }

        return {"success": True, "data": data, "reasoning_step": reasoning_step}

    except Exception as e:
        return {
            "success": False,
            "error": f"Lỗi khi lấy thông tin: {str(e)}",
            "reasoning_step": {
                "step": 1,
                "action": "Tra cứu thông tin khách hàng",
                "result": "LỖI HỆ THỐNG",
                "decision": "ERROR",
                "detail": str(e)
            }
        }
