"""
Global Error Handler for FastAPI.
"""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler."""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
        }
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error. Vui lòng thử lại sau.",
        }
    )
