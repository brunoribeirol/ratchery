# Product

Ratchetry is a batteries-included, low-overhead operating layer for AI-assisted
development. It configures Claude Code and OpenAI Codex with safe permissions,
curated agents and Skills, project templates, durable Obsidian memory,
diagnostics, and cost-aware tool routing.

## Goal

Give developers an excellent agent workspace without requiring them to
research and assemble every hook, permission, Skill, agent, memory convention,
and optional tool themselves. Ship broad capability, but activate and load only
what the project and task justify: maximum useful capability, minimum justified
token, permission, dependency, and maintenance cost.

The T0-T3 classifier and risk ratchet are the adaptive control plane that
selects rigor inside this setup. They are not the product's entire identity.

Optional optimizers must demonstrate lower cost per successful task on the
user's own workload. Vendor percentages, star counts, and installation alone
are not evidence; aggregate local benchmarks decide promotion.

## Non-goals

- Do not maximize agent/Skill/tool counts.
- Do not become a model host, general orchestrator, compliance certificate, or
  replacement for Spec Kit/OpenSpec/architecture analyzers.
- Do not auto-install external tools, persist raw conversations, expose
  credentials, or overwrite human-owned configuration.
- Do not make optional capabilities an always-on context or startup tax.

## Primary users

Individual developers and small teams using Claude Code, Codex, or both who
want safe defaults, continuity across sessions, proportional rigor, and full
ownership of their repository configuration.

The authoritative product contract is `docs/PROJECT_CONTEXT.md`. This steering
file is the short topic-scoped version loaded during product decisions.
