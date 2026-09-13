"""Minimal event schema for the T2 example pipeline."""
from __future__ import annotations

from typing import Any

EVENT_SCHEMA = {
    "required": ["event_id", "timestamp", "event_type", "account_id"],
}


def validate_event(event: dict[str, Any], schema: dict[str, Any]) -> None:
    missing = [field for field in schema["required"] if field not in event]
    if missing:
        raise ValueError(f"event missing required fields: {missing}")
