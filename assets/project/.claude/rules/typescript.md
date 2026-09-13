---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "package.json"
---
# TypeScript rules
- Preserve strict typing. Avoid `any`; use `unknown` and type guards.
- Validate external input at trust boundaries.
- Keep UI, transport, and business logic separated according to the existing architecture.
- Use the package manager and scripts declared by the repository.
