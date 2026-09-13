"""critical-system example: life-safety emergency shutoff controller.

Software that arms and triggers a physical emergency-shutoff relay for an
industrial line (e.g. an interlock that halts machinery when a safety sensor
trips). Used only by plant staff on an internal network -- not public, not
handling payments or PII -- yet a single risk fact (life_safety: true) is
enough on its own to force this to the maximum-rigor tier (T3). See
README.md for exactly how the hard-floor mechanism does that.
"""
from __future__ import annotations

from fastapi import FastAPI

from shutoff import ShutoffCommand, trigger_shutoff

app = FastAPI(title="Emergency Shutoff Controller (internal)")


@app.post("/shutoff/trigger")
def trigger(command: ShutoffCommand) -> dict[str, str]:
    return {"status": trigger_shutoff(command)}
