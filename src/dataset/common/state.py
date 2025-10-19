"""State persistence helpers (local/S3) reused across plugins."""
from __future__ import annotations

from .storage import read_state, write_state


def load_watermark(state_root: str | None, plugin_id: str) -> str | None:
    if not state_root:
        return None
    data = read_state(state_root, f"{plugin_id}.json")
    return data.get("last_until") if data else None


def save_watermark(state_root: str | None, plugin_id: str, until_date: str):
    if not state_root:
        return
    write_state(state_root, f"{plugin_id}.json", {"last_until": until_date})