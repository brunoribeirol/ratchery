---
paths:
  - "**/*.py"
  - "pyproject.toml"
---
# Python rules
- Use type hints for public and business-critical code.
- Keep routers/controllers thin and business logic testable.
- Prefer project-configured Ruff, mypy, pytest, and dependency tooling.
- Do not add broad exception catches without preserving actionable errors.
