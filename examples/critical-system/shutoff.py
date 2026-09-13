"""Emergency shutoff relay logic. This is a life-safety code path -- do not
change trigger conditions, timeouts, or the fail-safe default without a
docs/SECURITY_REVIEW.md entry and human review, per this project's T3 tier
requirements.
"""
from __future__ import annotations

from pydantic import BaseModel


class ShutoffCommand(BaseModel):
    line_id: str
    reason: str
    confirmed_by: str


def trigger_shutoff(command: ShutoffCommand) -> str:
    if not command.confirmed_by:
        raise ValueError("shutoff command must be explicitly confirmed")
    # Placeholder: a real implementation would assert the physical relay and
    # fail safe (shutoff engaged) if the relay's own health check is uncertain.
    return f"shutoff engaged for line {command.line_id}"
