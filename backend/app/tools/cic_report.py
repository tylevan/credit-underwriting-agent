"""
Tool: Get CIC Report
Lấy báo cáo tín dụng CIC của khách hàng.
"""

import pandas as pd
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from ..config.policy_constants import CreditPolicy
from ..models.database import get_customer_by_id


class CICReportInput(BaseModel):
    customer_id: str = Field(description="ID của khách hàng")


@tool("get_cic_report", args_schema=CICReportInput)
def get_cic_report(customer_id: str) -> dict:
    """
    Lấy báo cáo tín dụng CIC của khách hàng.
    Trả về: credit_sco, suggested_rate, debt_group, auto_reject flag.
    """
    try:
        customer = get_customer_by_id(int(customer_id))

        if customer is None:
            return {
                "success": False,
                "error": f"Không tìm thấy khách hàng với ID: {customer_id}",
                "reasoning_step": {
                    "step": 2,
                    "action": "Tra cứu CIC",
                    "result": "KHÔNG TÌM THẤY",
                    "decision": "FAIL",
                    "detail": f"ID {customer_id} không tồn tại"
                }
            }

        # Lấy thông tin CIC
        credit_score = int(customer.get('credit_sco', 0))
        risk_score = float(customer.get('risk_score', 0)) if pd.notna(customer.get('risk_score')) else 0
        risk_segment = customer.get('risk_segment', 'Unknown')

        # Tra cứu CIC tier từ policy constants
        cic_tier = CreditPolicy.get_cic_tier(credit_score)
        if cic_tier:
            score_rating = cic_tier["rating"]
            suggested_rate = cic_tier["rate"]
        else:
            score_rating = "Kém (Dưới chuẩn)"
            suggested_rate = None

        # Xác định nhóm nợ từ policy constants
        debt_info = CreditPolicy.get_debt_group(risk_score)
        debt_group = debt_info["group"]
        debt_group_name = debt_info["name"]
        has_bad_debt = debt_info["is_bad"]

        # Kiểm tra điều kiện từ chối ngay
        auto_reject_reasons = []
        if credit_score < CreditPolicy.CIC_AUTO_REJECT:
            auto_reject_reasons.append(
                f"Điểm CIC {credit_score} < {CreditPolicy.CIC_AUTO_REJECT} (dưới ngưỡng tối thiểu)"
            )
        if has_bad_debt:
            auto_reject_reasons.append(
                f"Nhóm nợ {debt_group} ({debt_group_name}) - thuộc nhóm nợ xấu {CreditPolicy.BAD_DEBT_GROUPS}"
            )

        # Ước tính nợ hiện tại
        balance = float(customer.get('balance', 0))
        estimated_current_debt = balance * risk_score * 0.5
        estimated_monthly_payment = estimated_current_debt * 0.05 if debt_group > 1 else 0

        auto_reject = len(auto_reject_reasons) > 0

        cic_data = {
            "customer_id": customer_id,
            "credit_sco": credit_score,
            "score_rating": score_rating,
            "suggested_rate": suggested_rate,
            "risk_score": round(risk_score, 4),
            "risk_segment": risk_segment,
            "debt_group": debt_group,
            "debt_group_name": debt_group_name,
            "has_bad_debt": has_bad_debt,
            "estimated_current_debt": round(estimated_current_debt),
            "estimated_monthly_payment": round(estimated_monthly_payment),
            "auto_reject": auto_reject,
            "auto_reject_reasons": auto_reject_reasons,
        }

        # Structured reasoning
        if auto_reject:
            decision = "FAIL"
            detail = "AUTO REJECT: " + "; ".join(auto_reject_reasons)
        else:
            decision = "PASS"
            detail = (
                f"CIC {credit_score} ({score_rating}) ✅. "
                f"Nhóm nợ {debt_group} ({debt_group_name}) ✅. "
                f"Lãi suất đề xuất: {suggested_rate}%/năm."
            )

        reasoning_step = {
            "step": 2,
            "action": "Kiểm tra báo cáo tín dụng CIC",
            "result": f"CIC = {credit_score} ({score_rating}), Nhóm nợ {debt_group}",
            "policy_ref": "Mục 2 & 3 - Hệ số CIC và Lãi suất",
            "decision": decision,
            "detail": detail,
        }

        return {"success": True, "data": cic_data, "reasoning_step": reasoning_step}

    except Exception as e:
        return {
            "success": False,
            "error": f"Lỗi khi lấy CIC: {str(e)}",
            "reasoning_step": {
                "step": 2,
                "action": "Tra cứu CIC",
                "result": "LỖI HỆ THỐNG",
                "decision": "ERROR",
                "detail": str(e)
            }
        }
