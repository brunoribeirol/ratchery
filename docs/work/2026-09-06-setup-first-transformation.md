# Work Plan: Setup-First Product Transformation

## Objective

Transform Ratchetry into the public, productized successor to the original
Claude Code + Codex + Obsidian setup: a batteries-included operating layer
that provides strong capabilities while minimizing default token, permission,
dependency, and maintenance cost. The adaptive tier engine remains the control
plane that selects rigor; it is not the product's whole identity.

## Non-goals

- Do not add Sentrux, another MCP server, or another external dependency during
  the foundation work.
- Do not rename the repository, executable, config directories, or managed
  marker in the same change as the product and trust-boundary corrections.
- Do not turn the project into a model host, agent orchestrator, compliance
  certification, architecture scanner, or replacement for Spec Kit/OpenSpec.
- Do not optimize for the number of shipped agents or Skills.
- Do not require every optional capability in every project or session.

## Evidence and assumptions

- The original v8.2.1 specification defines a low-overhead operating layer for
  Claude Code and Codex with curated Obsidian memory and optional tools.
- The external `claude-code-memory-setup` reference centers persistent memory
  and avoiding repeated codebase reads; fixed token-saving claims are not
  adopted without measurement.
- The current code already contains the main building blocks: managed config,
  four baseline agents, progressive-disclosure Skills, project profiling,
  tiering/ratchet, tool routing, Vault memory, diagnostics, and rollback.
- `docs/PROJECT_CONTEXT.md` and `.agents/steering/product.md` are placeholders,
  leaving README marketing to act as an accidental product specification.
- The current security gate has independently reproduced false-negative paths:
  removed Claude denies/hooks and forged derived tier fields can pass doctor.
- The current project remains named Ratchetry and the command remains
  `ratchery` until the clean-history rebrand phase.

## Affected contracts and files

- Product contract: `docs/PROJECT_CONTEXT.md`, `.agents/steering/product.md`,
  `README.md`, `docs/ARCHITECTURE.md`.
- Diagnostic contract: `doctor` is read-only and validates the effective
  security/tier configuration, not merely file presence.
- Project configuration: `.claude/settings.json`, `.codex/config.toml`,
  `.codex/hooks.json`, `.agents/state/tier.json`.
- Tests: `tests/test_doctor_tier_json.py` plus affected integration coverage.
- Later phases may touch MCP opt-in persistence, deterministic generated state,
  release artifacts, examples, catalog pruning, and branding.

## Risks

- Over-validating exact generated config could reject safe user additions;
  validation must require security invariants while allowing stricter values.
- Recomputing tier state must respect the ratchet and acknowledged resets
  without mutating history during doctor.
- Product-document edits can duplicate guidance; one canonical product contract
  must feed shorter README and architecture explanations.
- Rebrand work can break installed paths and upgrades, so it remains isolated.

## Workstreams and ownership

1. **Foundation (primary agent):** canonical product contract, setup-first
   positioning, security/tier doctor integrity, regression tests.
2. **Efficiency:** read-only diagnostics, deterministic refresh state, honest
   first-run risk collection, durable dual-client MCP opt-ins. See
   `docs/specs/team-durable-risk-and-mcp.md`.
3. **Release:** dependency example correction, deterministic source artifact,
   checksums, SBOM/provenance, public-repository launch checklist.
4. **Pruning and integrations:** classify every agent, Skill, template, doc, and
   optional tool as core/conditional/on-demand/remove; evaluate Sentrux only
   after the foundation passes.
5. **Rebrand/publication:** choose final naming, migrate links and paths in a
   dedicated compatibility plan, create the clean-history repository.

The primary agent owns integration. Independent security review and test agents
review sensitive changes after implementation; they do not write overlapping
files.

## Acceptance criteria

- A reader can identify the product, target users, principles, and non-goals
  from the first README screen and the canonical product context.
- The product is described as a complete setup/operating layer; tiering is
  correctly described as its adaptive control plane.
- `doctor --deep` fails if either CLI's required sandbox, credential denies,
  environment filtering, or actual PreToolUse hook binding is removed.
- `doctor` rejects forged derived tier fields and performs no writes.
- Existing safe custom configuration remains allowed.
- New tests reproduce each former false negative before proving the fix.
- Full tests, Ruff, manifest verification, and fresh-clone diagnostics pass.
- Optional tools remain optional and no new production dependency is added.

## Validation plan

```bash
python3 tests/test_doctor_tier_json.py
python3 tests/test_adaptive_engine.py
make test
python3 scripts/verify-manifest.py
git diff --check
```

Also run isolated negative fixtures for removed hook/deny settings and forged
tier state, plus a fresh-clone `doctor --deep --json` check. Run an independent
security review and read-only test pass before completing the foundation phase.

## Handoff

Status: foundation, efficiency, release, and catalog-audit workstreams are
implemented and validated. The rebrand/publication workstream remains separate:
choose the final public name, define installed-path compatibility, update links
and repository metadata, and create the clean-history repository without
changing the frozen managed-block format marker.
