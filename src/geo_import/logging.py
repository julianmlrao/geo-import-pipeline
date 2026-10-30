"""Logging setup: plain text by default, JSON lines with GEO_IMPORT_LOG_JSON=1."""

from __future__ import annotations

import json
import logging
import os
import sys


class _Json(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


def setup() -> None:
    handler = logging.StreamHandler(sys.stderr)
    if os.environ.get("GEO_IMPORT_LOG_JSON") == "1":
        handler.setFormatter(_Json())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(os.environ.get("GEO_IMPORT_LOG_LEVEL", "INFO"))
