"""T1 example: standard backend API.

A small inventory lookup/adjust API used by a couple of external partner
integrations (not the public internet), plus internal staff. Real but modest
complexity: a couple of route modules, no PII/payments, no regulated data.
"""
from __future__ import annotations

from fastapi import FastAPI

from routes import inventory, health

app = FastAPI(title="Inventory Lookup API (internal)")
app.include_router(health.router)
app.include_router(inventory.router)
