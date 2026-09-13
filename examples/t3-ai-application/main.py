"""T3 example: AI application handling PII, publicly accessible.

A small FastAPI app offering an AI-assisted profile-completion feature to the
general public. It stores and processes personal data (models/user.py) and
operates under explicit regulatory scope (e.g. GDPR), so it is a
Critical/regulated-system tier (T3) project.
"""
from __future__ import annotations

from fastapi import FastAPI

from models.user import UserProfile, summarize_profile

app = FastAPI(title="AI Profile Assistant (public)")


@app.post("/profile/summarize")
def summarize(profile: UserProfile) -> dict[str, str]:
    return {"summary": summarize_profile(profile)}
