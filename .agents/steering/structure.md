# Structure

Architecture and directory layout an agent should know before navigating.

## Layout notes

<fill in: where does business logic live, where are tests, what's generated vs. hand-written>

Detected size: small, as of `init` time -- this line is a one-time snapshot,
never refreshed (see `lib/context_engine.py`'s module docstring); check
`.agents/state/project-profile.md` for the current count instead of trusting
a specific number here.
