"""
══════════════════════════════════════════════════════════════
SINGLE SOURCE OF TRUTH: Credit Policy Constants
══════════════════════════════════════════════════════════════

Mọi tool, node, prompt đều import từ file này.
Khi policy thay đổi, CHỈ SỬA FILE NÀY.

Version: 2024.1
Last updated: 2024-12-01
"""


class CreditPolicy:
    """Chính sách thẩm định tín dụng tiêu dùng."""

    # ── ĐIỀU KIỆN KHÁCH HÀNG ──
    AGE_MIN = 18
    AGE_MAX = 60
    MIN_MONTHLY_INCOME = 5_000_000  # 5 triệu VND

    # ── HẠN MỨC VAY ──
    LOAN_MIN = 10_000_000            # 10 triệu
    LOAN_MAX = 1_200_000_000         # 1.2 tỷ (trần tuyệt đối)
    BASE_MULTIPLIER = 18             # Hạn mức = 18x thu nhập
    TERM_MIN_MONTHS = 6
    TERM_MAX_MONTHS = 60

    # ── ĐIỂM CIC & LÃI SUẤT ──
    # Ngưỡng từ chối tuyệt đối
    CIC_AUTO_REJECT = 600

    # Bảng CIC → lãi suất, hệ số, rating
    # Key = ngưỡng dưới (>=), sắp xếp giảm dần khi tra cứu
    CIC_TIERS = [
        {"min_score": 750, "rate": 12.0, "factor": 1.0, "rating": "Rất tốt"},
        {"min_score": 700, "rate": 14.0, "factor": 0.9, "rating": "Tốt"},
        {"min_score": 650, "rate": 16.0, "factor": 0.8, "rating": "Khá"},
        {"min_score": 600, "rate": 18.0, "factor": 0.6, "rating": "Trung bình"},
    ]

    # ── DTI (Debt-to-Income) ──
    DTI_PASS = 40       # <= 40%: OK
    DTI_REVIEW = 50     # 40-50%: Cần xem xét
    # > 50%: Từ chối

    # ── NỢ XẤU ──
    BAD_DEBT_GROUPS = [3, 4, 5]
    RISK_SCORE_BAD_DEBT = 0.6    # risk_score >= 0.6 → nợ xấu


    @classmethod
    def get_cic_tier(cls, score: int) -> dict:
        """
        Tra cứu tier CIC dựa trên điểm.

        Returns:
            dict với keys: min_score, rate, factor, rating
            Hoặc None nếu dưới ngưỡng từ chối
        """
        if score < cls.CIC_AUTO_REJECT:
            return None
        for tier in cls.CIC_TIERS:
            if score >= tier["min_score"]:
                return tier
        return None

    @classmethod
    def get_debt_group(cls, risk_score: float) -> dict:
        """Xác định nhóm nợ từ risk_score."""
        if risk_score >= 0.8:
            return {"group": 4, "name": "Nợ nghi ngờ/Nợ xấu", "is_bad": True}
        elif risk_score >= 0.6:
            return {"group": 3, "name": "Nợ dưới tiêu chuẩn", "is_bad": True}
        elif risk_score >= 0.4:
            return {"group": 2, "name": "Nợ cần chú ý", "is_bad": False}
        else:
            return {"group": 1, "name": "Nợ tiêu chuẩn", "is_bad": False}

    @classmethod
    def assess_dti(cls, dti_percent: float) -> dict:
        """Đánh giá DTI."""
        if dti_percent <= cls.DTI_PASS:
            return {"assessment": "PASS", "description": "Khả năng trả nợ tốt"}
        elif dti_percent <= cls.DTI_REVIEW:
            return {"assessment": "REVIEW", "description": "Cần xem xét thêm các yếu tố khác"}
        else:
            return {"assessment": "FAIL", "description": "Tỷ lệ nợ quá cao, rủi ro không trả được nợ"}



    @classmethod
    def get_readable_policy(cls) -> str:
        """Trả về policy dạng text cho LLM đọc."""
        tiers_text = "\n".join([
            f"   - CIC >= {t['min_score']} ({t['rating']}): {t['rate']}%/năm, hệ số {t['factor']}"
            for t in cls.CIC_TIERS
        ])
        return f"""
=== CHÍNH SÁCH TÍN DỤNG TÍN CHẤP ===
1. ĐIỀU KIỆN CƠ BẢN:
   - Tuổi: {cls.AGE_MIN} - {cls.AGE_MAX} tuổi
   - Thu nhập tối thiểu: {cls.MIN_MONTHLY_INCOME:,.0f} VND/tháng

2. SẢN PHẨM VAY:
   - Hạn mức: {cls.LOAN_MIN:,.0f} - {cls.LOAN_MAX:,.0f} VND
   - Kỳ hạn: {cls.TERM_MIN_MONTHS} - {cls.TERM_MAX_MONTHS} tháng
   - Hạn mức = MIN({cls.LOAN_MAX:,.0f}, {cls.BASE_MULTIPLIER} x Thu nhập x Hệ số CIC)

3. LÃI SUẤT THEO CIC:
{tiers_text}
   - CIC < {cls.CIC_AUTO_REJECT}: TỪ CHỐI

4. DTI (Nợ/Thu nhập):
   - <= {cls.DTI_PASS}%: PASS
   - {cls.DTI_PASS}-{cls.DTI_REVIEW}%: REVIEW
   - > {cls.DTI_REVIEW}%: REJECT

5. ĐIỀU KIỆN TỪ CHỐI NGAY:
   - Nợ xấu nhóm {cls.BAD_DEBT_GROUPS}
   - CIC < {cls.CIC_AUTO_REJECT}
   - Tuổi < {cls.AGE_MIN} hoặc > {cls.AGE_MAX}
   - DTI > {cls.DTI_REVIEW}%
"""
