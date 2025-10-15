"""
Logging configuration for [STUB] backend.

Sets up a JSON-structured logger using Python's logging module. Avoids logging
sensitive data; only logs generic operational events.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    """Format logs as compact JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


# PUBLIC_INTERFACE
def configure_json_logging(level: int = logging.INFO) -> None:
    """Configure root logger with JSON formatter. [STUB]"""
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    # Remove existing handlers to avoid duplicates in reload scenarios
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)

    # Quiet overly verbose loggers in dev
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
