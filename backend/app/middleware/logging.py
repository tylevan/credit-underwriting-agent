"""
Logging configuration.
Structured JSON logging cho audit trail.
"""

import logging
import json
import sys
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Format log messages as JSON for Cloud Logging."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Thêm extra fields nếu có
        if hasattr(record, "extra"):
            log_entry.update(record.extra)

        # Thêm exception info
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO"):
    """Setup structured logging."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.addHandler(handler)

    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
