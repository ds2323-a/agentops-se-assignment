"""结构化 JSON 日志，携带 request_id，且不记录敏感字段。"""
from __future__ import annotations

import json
import sys
import threading
from datetime import datetime, timezone

_LOCK = threading.Lock()
_SENSITIVE = {"password", "token", "authorization", "secret", "cookie"}


def _clean(payload: dict) -> dict:
    return {k: ("***" if k.lower() in _SENSITIVE else v) for k, v in payload.items()}


def log(level: str, event: str, request_id: str = "-", **fields) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "level": level,
        "event": event,
        "request_id": request_id,
        **_clean(fields),
    }
    with _LOCK:
        sys.stdout.write(json.dumps(record, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def info(event: str, request_id: str = "-", **fields) -> None:
    log("INFO", event, request_id, **fields)


def warn(event: str, request_id: str = "-", **fields) -> None:
    log("WARN", event, request_id, **fields)


def error(event: str, request_id: str = "-", **fields) -> None:
    log("ERROR", event, request_id, **fields)
