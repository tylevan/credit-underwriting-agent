"""
Data Access Layer.
Load CSV một lần, cache trong memory.
Sau này có thể swap sang PostgreSQL/Firestore mà không ảnh hưởng tools.
"""

import pandas as pd
from functools import lru_cache
from ..config.settings import settings


@lru_cache(maxsize=1)
def get_dataframe() -> pd.DataFrame:
    """
    Load và cache DataFrame từ CSV.
    lru_cache đảm bảo chỉ đọc file 1 lần duy nhất.
    """
    df = pd.read_csv(settings.DATA_PATH)
    return df


def get_customer_by_id(customer_id: int) -> dict | None:
    """
    Lấy 1 customer theo ID.
    Returns: dict hoặc None nếu không tìm thấy.
    """
    df = get_dataframe()
    row = df[df['id'] == customer_id]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def list_all_customers(limit: int = 20) -> list[dict]:
    """Lấy danh sách customers."""
    df = get_dataframe()
    return df[['id', 'full_name', 'credit_sco', 'customer_segment']].head(limit).to_dict('records')


def get_total_customer_count() -> int:
    """Đếm tổng số customers."""
    return len(get_dataframe())
