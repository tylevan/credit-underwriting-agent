"""
Calculator Tools: Monthly Payment, DTI, Max Loan.
Tất cả logic tính toán dùng CreditPolicy constants.
"""

from pydantic import BaseModel, Field
from langchain_core.tools import tool

from ..config.policy_constants import CreditPolicy


# ════════════════════════════════════════════
# TOOL 3: CALCULATE MONTHLY PAYMENT
# ════════════════════════════════════════════

class MonthlyPaymentInput(BaseModel):
    loan_amount: float = Field(description="Số tiền vay (VND)")
    annual_rate: float = Field(description="Lãi suất năm (%), lấy từ suggested_rate của CIC")
    term_months: int = Field(description="Kỳ hạn vay (tháng)")


@tool("calculate_monthly_payment", args_schema=MonthlyPaymentInput)
def calculate_monthly_payment(loan_amount: float, annual_rate: float, term_months: int) -> dict:
    """
    Tính số tiền trả hàng tháng theo phương pháp dư nợ giảm dần.
    Trả về: monthly_payment, total_payment, total_interest.
    """
    # Validate kỳ hạn vay
    if term_months < CreditPolicy.TERM_MIN_MONTHS or term_months > CreditPolicy.TERM_MAX_MONTHS:
        return {
            "success": False,
            "error": f"Kỳ hạn vay phải từ {CreditPolicy.TERM_MIN_MONTHS} đến {CreditPolicy.TERM_MAX_MONTHS} tháng",
            "reasoning_step": {
                "step": 3,
                "action": "Tính tiền trả hàng tháng",
                "result": f"KỲ HẠN KHÔNG HỢP LỆ: {term_months} tháng",
                "policy_ref": f"Kỳ hạn: {CreditPolicy.TERM_MIN_MONTHS}-{CreditPolicy.TERM_MAX_MONTHS} tháng",
                "decision": "FAIL",
                "detail": f"Kỳ hạn {term_months} tháng nằm ngoài phạm vi cho phép ({CreditPolicy.TERM_MIN_MONTHS}-{CreditPolicy.TERM_MAX_MONTHS} tháng)"
            }
        }

    if loan_amount <= 0 or annual_rate <= 0 or term_months <= 0:
        return {
            "success": False,
            "error": "Tham số không hợp lệ (phải > 0)",
            "reasoning_step": {
                "step": 3,
                "action": "Tính tiền trả hàng tháng",
                "result": "THAM SỐ KHÔNG HỢP LỆ",
                "decision": "ERROR",
                "detail": f"loan={loan_amount}, rate={annual_rate}, term={term_months}"
            }
        }

    monthly_rate = annual_rate / 100 / 12
    monthly_principal = loan_amount / term_months
    first_month_interest = loan_amount * monthly_rate

    # PMT tháng đầu (cao nhất)
    pmt = monthly_principal + first_month_interest

    # Tổng lãi (dư nợ giảm dần)
    total_interest = (loan_amount * monthly_rate * (term_months + 1)) / 2
    total_payment = loan_amount + total_interest

    data = {
        "loan_amount": loan_amount,
        "annual_rate": annual_rate,
        "term_months": term_months,
        "monthly_principal": round(monthly_principal),
        "first_month_interest": round(first_month_interest),
        "monthly_payment": round(pmt),
        "total_payment": round(total_payment),
        "total_interest": round(total_interest),
    }

    reasoning_step = {
        "step": 3,
        "action": "Tính tiền trả hàng tháng",
        "result": f"Trả tháng đầu: {pmt:,.0f} VND (gốc {monthly_principal:,.0f} + lãi {first_month_interest:,.0f})",
        "policy_ref": "Phương pháp dư nợ giảm dần",
        "decision": "CALCULATED",
        "detail": (
            f"Vay {loan_amount:,.0f} VND, lãi {annual_rate}%/năm, "
            f"kỳ hạn {term_months} tháng. "
            f"Tổng trả: {total_payment:,.0f} VND (lãi: {total_interest:,.0f} VND)"
        )
    }

    return {"success": True, "data": data, "reasoning_step": reasoning_step}


# ════════════════════════════════════════════
# TOOL 4: CALCULATE DTI
# ════════════════════════════════════════════

class DTIInput(BaseModel):
    total_income: float = Field(description="Tổng thu nhập hàng tháng (balance + monthly_ir từ get_customer_info)")
    existing_debt: float = Field(description="Nợ hiện tại hàng tháng (estimated_monthly_payment từ get_cic_report)")
    new_monthly_payment: float = Field(description="Khoản trả nợ mới hàng tháng (monthly_payment từ calculate_monthly_payment)")


@tool("calculate_dti", args_schema=DTIInput)
def calculate_dti(total_income: float, existing_debt: float, new_monthly_payment: float) -> dict:
    """
    Tính tỷ lệ nợ trên thu nhập (DTI).
    Trả về: dti_percent, assessment (PASS/REVIEW/FAIL).
    """
    if total_income <= 0:
        return {
            "success": False,
            "error": "Tổng thu nhập phải > 0",
            "reasoning_step": {
                "step": 4, "action": "Tính DTI",
                "result": "THU NHẬP KHÔNG HỢP LỆ", "decision": "ERROR",
                "detail": f"total_income = {total_income}"
            }
        }

    total_debt = existing_debt + new_monthly_payment
    dti = (total_debt / total_income) * 100

    # Dùng policy constants
    assessment_result = CreditPolicy.assess_dti(dti)

    data = {
        "total_income": total_income,
        "existing_debt": existing_debt,
        "new_monthly_payment": new_monthly_payment,
        "total_debt": total_debt,
        "dti_percent": round(dti, 2),
        "assessment": assessment_result["assessment"],
        "description": assessment_result["description"],
    }

    reasoning_step = {
        "step": 4,
        "action": "Tính tỷ lệ nợ trên thu nhập (DTI)",
        "result": f"DTI = {dti:.1f}% → {assessment_result['assessment']}",
        "policy_ref": f"Mục 5 - DTI: PASS <= {CreditPolicy.DTI_PASS}%, REVIEW <= {CreditPolicy.DTI_REVIEW}%, FAIL > {CreditPolicy.DTI_REVIEW}%",
        "decision": assessment_result["assessment"],
        "detail": (
            f"Tổng nợ {total_debt:,.0f} / Thu nhập {total_income:,.0f} = {dti:.1f}%. "
            f"{assessment_result['description']}"
        )
    }

    return {"success": True, "data": data, "reasoning_step": reasoning_step}


# ════════════════════════════════════════════
# TOOL 8: CALCULATE MAX LOAN
# ════════════════════════════════════════════

class MaxLoanInput(BaseModel):
    monthly_income: float = Field(..., description="Thu nhập hàng tháng (VND)")
    cic_score: int = Field(..., description="Điểm tín dụng CIC (300-850)")


@tool("calculate_max_loan", args_schema=MaxLoanInput)
def calculate_max_loan(monthly_income: float, cic_score: int) -> dict:
    """
    Tính hạn mức vay tín chấp tối đa dựa trên thu nhập và CIC.
    Trả về: final_approved_limit, is_rejected.
    """
    try:
        if monthly_income < 0:
            return {
                "success": False, "error": "Thu nhập không thể là số âm.",
                "reasoning_step": {
                    "step": 5, "action": "Tính hạn mức",
                    "result": "THU NHẬP KHÔNG HỢP LỆ", "decision": "ERROR",
                    "detail": f"monthly_income = {monthly_income}"
                }
            }

        # Tra CIC tier
        cic_tier = CreditPolicy.get_cic_tier(cic_score)

        if cic_tier is None:
            return {
                "success": True,
                "data": {
                    "input_income": monthly_income,
                    "input_cic": cic_score,
                    "cic_rating": "Kém (Dưới chuẩn)",
                    "cic_factor": 0.0,
                    "final_approved_limit": 0,
                    "is_rejected": True,
                    "message": "Từ chối cấp hạn mức do điểm tín dụng thấp."
                },
                "reasoning_step": {
                    "step": 5,
                    "action": "Tính hạn mức vay tối đa",
                    "result": f"CIC {cic_score} < {CreditPolicy.CIC_AUTO_REJECT} → Từ chối",
                    "policy_ref": "Mục 2 - Hạn mức vay",
                    "decision": "FAIL",
                    "detail": f"Điểm CIC {cic_score} dưới ngưỡng tối thiểu {CreditPolicy.CIC_AUTO_REJECT}"
                }
            }

        cic_factor = cic_tier["factor"]
        cic_rating = cic_tier["rating"]

        # Tính toán
        theoretical_limit = monthly_income * CreditPolicy.BASE_MULTIPLIER
        risk_adjusted_limit = theoretical_limit * cic_factor
        approved_limit = min(risk_adjusted_limit, CreditPolicy.LOAN_MAX)
        approved_limit = round(approved_limit / 100000) * 100000  # Làm tròn

        data = {
            "input_income": monthly_income,
            "input_cic": cic_score,
            "cic_rating": cic_rating,
            "cic_factor": cic_factor,
            "base_multiplier": CreditPolicy.BASE_MULTIPLIER,
            "loan_max": CreditPolicy.LOAN_MAX,
            "theoretical_max": theoretical_limit,
            "risk_adjusted_limit": risk_adjusted_limit,
            "final_approved_limit": approved_limit,
            "is_rejected": approved_limit == 0,
            "message": f"Hạn mức tối đa: {approved_limit:,.0f} VND"
        }

        reasoning_step = {
            "step": 5,
            "action": "Tính hạn mức vay tối đa",
            "result": f"Hạn mức = {approved_limit:,.0f} VND",
            "policy_ref": f"Mục 2 - Công thức: MIN({CreditPolicy.LOAN_MAX:,.0f}, {CreditPolicy.BASE_MULTIPLIER} × Thu nhập × {cic_factor})",
            "decision": "CALCULATED",
            "detail": (
                f"Thu nhập {monthly_income:,.0f} × {CreditPolicy.BASE_MULTIPLIER} = {theoretical_limit:,.0f}. "
                f"× Hệ số CIC {cic_factor} ({cic_rating}) = {risk_adjusted_limit:,.0f}. "
                f"Trần: {CreditPolicy.LOAN_MAX:,.0f}. "
                f"→ Hạn mức duyệt: {approved_limit:,.0f} VND"
            )
        }

        return {"success": True, "data": data, "reasoning_step": reasoning_step}

    except Exception as e:
        return {
            "success": False, "error": f"Lỗi tính toán: {str(e)}",
            "reasoning_step": {
                "step": 5, "action": "Tính hạn mức",
                "result": "LỖI", "decision": "ERROR", "detail": str(e)
            }
        }
