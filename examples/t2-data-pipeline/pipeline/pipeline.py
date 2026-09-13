"""T2 example: data pipeline.

Extracts customer usage events from a partner-facing upload endpoint,
transforms them into the warehouse schema, and loads them into the analytics
warehouse. The upload endpoint is internet-reachable (external_exposure), so
this pipeline is a Product-tier (T2) project even without PII/payments.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from schema import EVENT_SCHEMA, validate_event


def extract(raw_dir: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in sorted(raw_dir.glob("*.jsonl")):
        import json

        for line in path.read_text().splitlines():
            if line.strip():
                events.append(json.loads(line))
    return events


def transform(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for event in events:
        validate_event(event, EVENT_SCHEMA)
        out.append({**event, "event_date": event["timestamp"][:10]})
    return out


def load(events: list[dict[str, Any]], warehouse_table: str) -> int:
    # Placeholder: a real implementation would write to the configured warehouse.
    print(f"Would load {len(events)} rows into {warehouse_table}")
    return len(events)


def run(raw_dir: Path, warehouse_table: str = "analytics.usage_events") -> int:
    return load(transform(extract(raw_dir)), warehouse_table)


if __name__ == "__main__":
    import sys

    raise SystemExit(0 if run(Path(sys.argv[1] if len(sys.argv) > 1 else "raw")) >= 0 else 1)
