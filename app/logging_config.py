"""Structured (JSON-line) logging.

One JSON object per log record makes the output greppable and ready for log
aggregators (Loki, CloudWatch, etc.) without a parsing step.
"""

from __future__ import annotations

import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    """Render each log record as a single JSON line.

    Anything passed via `logger.info(msg, extra={...})` is merged in, so call
    sites can attach structured fields (request_id, intent, latency_ms, ...).
    """

    # Standard LogRecord attributes we don't want to echo back as "extra".
    _RESERVED = set(
        logging.LogRecord("", 0, "", 0, "", (), None).__dict__
    ) | {"message", "asctime"}

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in self._RESERVED:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Install the JSON formatter on the root logger (idempotent)."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
