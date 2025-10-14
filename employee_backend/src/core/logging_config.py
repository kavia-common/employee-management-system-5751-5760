"""
Logging configuration for structured JSON logs with correlation ID support.

- Emits JSON logs to stdout with fields: timestamp, level, message, logger, env, correlationId.
- Avoids logging PII or sensitive data by design; callers must not pass PII.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from src.core.config import settings


class CorrelationIdFilter(logging.Filter):
    """
    Logging filter to inject correlationId into log records.

    The correlation ID is obtained from a context variable set by middleware.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Lazy import to avoid circular dependency
        try:
            from src.middlewares.correlation import correlation_id_var  # type: ignore
            cid = correlation_id_var.get()
        except Exception:
            cid = None
        setattr(record, "correlationId", cid)
        return True


class JsonFormatter(logging.Formatter):
    """Format log records as JSON with standard fields."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        log: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "env": settings.env,
            "correlationId": getattr(record, "correlationId", None),
        }
        if record.exc_info:
            # Include exception type and message only; avoid full stack unless DEBUG
            exc_type = record.exc_info[0].__name__ if record.exc_info[0] else "Exception"
            exc_msg = str(record.exc_info[1]) if record.exc_info[1] else ""
            log["exception"] = {"type": exc_type, "message": exc_msg}
            if logging.getLevelName(settings.log_level.upper()) == "DEBUG":
                log["stack"] = self.formatException(record.exc_info)
        return json.dumps(log, ensure_ascii=False)


# PUBLIC_INTERFACE
def setup_logging() -> None:
    """Configure root logging with JSON formatter and correlation ID filter."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(JsonFormatter())

    root.addHandler(handler)

    # Quiet noisy loggers if desired (optional; keep defaults practical)
    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel(logging.WARNING)
