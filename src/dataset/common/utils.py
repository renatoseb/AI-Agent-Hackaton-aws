"""Shared utility helpers (dates, lots extraction) for multiple countries."""
from __future__ import annotations

from datetime import datetime
import re
from typing import List

LOT_PATTERNS = [
    re.compile(r"\bLOT[:\s-]*([A-Z0-9-]{3,})", re.IGNORECASE),
    re.compile(r"\bLote[:\s-]*([A-Z0-9-]{3,})", re.IGNORECASE),
    re.compile(r"\bBatch[:\s-]*([A-Z0-9-]{3,})", re.IGNORECASE),
]


def normalize_date_yyyymmdd(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"]:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def extract_lots(text: str | None) -> List[str]:
    if not text:
        return []
    lots = set()
    for rx in LOT_PATTERNS:
        for m in rx.finditer(text):
            lots.add(m.group(1).upper())
    return sorted(lots)