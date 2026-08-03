"""Append-only agent decision reports."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any

from config import REPORTS_PATH

_lock = threading.Lock()


def append_report(report: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "id": report.get("id")
        or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"),
        "timestamp": report.get("timestamp")
        or datetime.now(timezone.utc).isoformat(),
        **{k: v for k, v in report.items() if k not in {"id", "timestamp"}},
    }
    line = json.dumps(payload, ensure_ascii=False)
    with _lock:
        with REPORTS_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    return payload


def list_reports(limit: int = 50) -> list[dict[str, Any]]:
    if not REPORTS_PATH.exists():
        return []
    with _lock:
        lines = REPORTS_PATH.read_text(encoding="utf-8").splitlines()
    reports: list[dict[str, Any]] = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            reports.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(reports) >= limit:
            break
    return reports
