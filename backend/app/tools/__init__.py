"""
Tools Registry.
Import tất cả tools và tạo danh sách + lookup table.
"""

from .customer_info import get_customer_info
from .cic_report import get_cic_report
from .calculators import (
    calculate_monthly_payment,
    calculate_dti,
    calculate_max_loan,
)
from .policy_and_utils import get_credit_policy

# Danh sách tất cả tools
ALL_TOOLS = [
    get_customer_info,
    get_cic_report,
    calculate_monthly_payment,
    calculate_dti,
    calculate_max_loan,
    get_credit_policy,
]

# Lookup table: tên tool → tool object
TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}

__all__ = [
    "ALL_TOOLS",
    "TOOLS_BY_NAME",
    "get_customer_info",
    "get_cic_report",
    "calculate_monthly_payment",
    "calculate_dti",
    "calculate_max_loan",
    "get_credit_policy",
]

