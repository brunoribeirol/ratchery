"""User profile model. Touches personal data (PII) directly -- name, email,
date of birth -- which is why this example carries handles_pii: true and
regulated: true in its risk answers. Do not add fields here without updating
docs/SECURITY_REVIEW.md, per this project's T3 tier requirements.
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, EmailStr


class UserProfile(BaseModel):
    full_name: str
    email: EmailStr
    date_of_birth: date
    bio: str = ""


def summarize_profile(profile: UserProfile) -> str:
    return f"{profile.full_name} ({profile.email}): {profile.bio[:200]}"
