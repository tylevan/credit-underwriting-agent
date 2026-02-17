"""
Rate Limiter Middleware.
Giới hạn số requests/ngày theo IP. Bật/tắt qua RATE_LIMIT_ENABLED.
"""

import time
import logging
from collections import defaultdict
from datetime import date

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from ..config.settings import settings

logger = logging.getLogger(__name__)


class RateLimitState:
    """In-memory rate limit tracker. Resets daily."""

    def __init__(self):
        self._counters: dict[str, int] = defaultdict(int)
        self._current_date: date = date.today()

    def _reset_if_new_day(self):
        today = date.today()
        if today != self._current_date:
            self._counters.clear()
            self._current_date = today

    def check_and_increment(self, ip: str) -> tuple[bool, int]:
        """
        Returns (allowed, current_count).
        """
        self._reset_if_new_day()
        self._counters[ip] += 1
        count = self._counters[ip]
        allowed = count <= settings.RATE_LIMIT_PER_DAY
        return allowed, count


# Singleton state
_state = RateLimitState()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limit middleware cho FastAPI.
    Chỉ áp dụng cho /api/v1/assess và /api/v1/chat (endpoints gọi LLM).
    Các endpoint khác (health, dashboard, customers) không bị giới hạn.
    """

    # Chỉ rate-limit các paths gọi LLM (tốn tiền API)
    RATE_LIMITED_PATHS = {"/api/v1/assess", "/api/v1/chat"}

    async def dispatch(self, request: Request, call_next):
        # Skip nếu rate limit bị tắt
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Chỉ rate-limit requests tới LLM endpoints
        if request.url.path not in self.RATE_LIMITED_PATHS:
            return await call_next(request)

        # Lấy IP (hỗ trợ proxy/Cloud Run)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        allowed, count = _state.check_and_increment(client_ip)

        if not allowed:
            logger.warning(
                "rate_limit_exceeded",
                extra={"ip": client_ip, "count": count, "limit": settings.RATE_LIMIT_PER_DAY},
            )
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Bạn đã vượt quá giới hạn sử dụng trong ngày.",
                    "message": f"Tối đa {settings.RATE_LIMIT_PER_DAY} yêu cầu/ngày. Vui lòng quay lại vào ngày mai.",
                    "limit": settings.RATE_LIMIT_PER_DAY,
                    "used": count,
                },
            )

        response = await call_next(request)

        # Header thông tin rate limit
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_DAY)
        response.headers["X-RateLimit-Remaining"] = str(max(0, settings.RATE_LIMIT_PER_DAY - count))

        return response
