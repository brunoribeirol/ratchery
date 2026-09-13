# Ratchetry

[![CI](https://github.com/brunoribeirol/ratchery/actions/workflows/ci.yml/badge.svg)](https://github.com/brunoribeirol/ratchery/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](docs/INSTALLATION.md)
[![Stdlib only](https://img.shields.io/badge/dependencies-stdlib%20only-brightgreen)](docs/ARCHITECTURE.md)
[Docs](docs/00-START-HERE.md) · [Architecture](docs/ARCHITECTURE.md) · [Issues](https://github.com/brunoribeirol/ratchery/issues)

Ratchetry turns a normal repository into a well-configured workspace for Claude Code and
OpenAI Codex: safe permissions, curated agents and Skills, reusable templates, durable
Obsidian memory, cost-aware context rules, diagnostics, refresh, and rollback.

It is **batteries included, not batteries always running**. The setup ships broad capability,
but specialized agents, process, external tools, and repository context load only when the
project or task justifies their token, permission, dependency, and maintenance cost.

> **Maximum useful capability, minimum justified cost.**

The Adaptive Engine is the control plane inside that setup. It combines a codebase profile
with explicit human-owned risk facts to select a T0-T3 policy, then applies a one-way risk
ratchet so recorded rigor cannot quietly drop without an acknowledged, logged decision. The
tier can require documentation, agents, Skills, testing, and security review; the CI gate
(`action.yml`) verifies machine-checkable configuration, but does not pretend that file
presence proves a human review or test was performed.

Ratchetry builds on the persistent-memory and context-efficiency problem explored by
[`claude-code-memory-setup`](https://github.com/lucasrosati/claude-code-memory-setup), then
productizes the wider Claude Code + Codex + Obsidian operating layer: deterministic local
safeguards, preservation of human configuration, adaptive rigor, and optional tools selected
only when their benefit exceeds their cost. The canonical product contract is
[`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md).

> **Compatibility note:** `ratchery` is the primary command and its config lives
> at `~/.config/ratchery/`. Existing private-development installs may keep using
> `agent-workspace` during the 1.x migration window; both commands execute the
> same installed runtime. The old name is not used for new documentation or paths.

## What's in v1.0

- **Safe dual-CLI workspace** -- shared `AGENTS.md` contract, minimal Claude adapter,
  fail-closed sandbox, credential/environment protection, restricted network, and a
  deterministic secondary hook for obvious dangerous operations.
- **Durable provider-neutral memory** -- stable project-to-Vault identity,
  explicit `workspace-resume`/`workspace-save`, and one bounded Git-aware
  handoff that Claude Code, Codex, or another CLI can exchange without storing
  a raw prompt, transcript, secret, or full tool output.
- **Cost-aware context** -- small topic-scoped steering files, generated `.claudeignore`,
  bounded initial reads, native search first, and optional indexes/MCP/tools kept out of the
  default path.
- **Curated capabilities** -- four baseline read/review/security/test agents plus tier-gated,
  capability-conditional, and on-demand agents and Skills. The global installer provides core
  Skills; project `init`/`refresh` installs only the applicable project agent/Skill set.
- **Adaptive control plane** -- deterministic T0-T3 classification, risk ratchet, capability
  detection, and a unit-tested Tool Router. Use `tier`, `tier-set`, `agents-status`, and
  `tools-recommend` to inspect the decisions.
- **Measured efficiency** -- offline ccusage inspection, no-state budget/spike
  warnings, and a digest-bound six-task A/B protocol with repeated-sample
  quality/cost reports. Ratchetry never starts paid benchmark runs or enables a
  tool from one cheap sample.
- **Reversible lifecycle** -- dry-run installation, managed blocks that preserve human text,
  owned-hook merging, backups, `refresh`, project/global doctors, and rollback.

See `docs/ARCHITECTURE.md` for how the pieces fit together and
`lib/adaptive_engine.py`'s module docstring for the tiering model. The historical
`docs/decision-matrix.md` and dated `docs/research-external.md` preserve design
provenance; they are not current behavior specifications.

## Why not just \<X\>?

Short version -- current scope is in `docs/PROJECT_CONTEXT.md`; historical and
external evidence is in `docs/decision-matrix.md`/`docs/research-external.md`:

| Instead of... | Ratchetry's difference |
|---|---|
| **GitHub Spec Kit** | Spec Kit structures feature delivery. Ratchetry configures the surrounding workspace: safety boundaries, memory, context, agents/Skills, diagnostics, and proportional policy. They can be used together. |
| **OpenSpec** | OpenSpec manages change artifacts and spec workflows. Ratchetry can select a light/full spec bar from project risk, but does not reimplement OpenSpec's workflow. |
| **Kiro's steering files** | Ratchetry adopts the useful topic-scoped context pattern in an open setup shared by Claude Code and Codex, without requiring the Kiro platform. |
| **BMAD-METHOD** | BMAD is a multi-persona delivery methodology. Ratchetry is a lower-overhead workspace layer and does not require a persona pipeline for ordinary work. |
| **A single `AGENTS.md`/`CLAUDE.md` file** | Prose is part of the setup, but cannot by itself install sandbox policy, preserve hooks, manage memory, adapt project rigor, or diagnose drift. |

## What Ratchetry deliberately will not do

These are decisions with reasoning behind them, not gaps in the backlog. Read this before
opening an issue or PR for one of them; the full argument is in `docs/PROJECT_CONTEXT.md` and
`.agents/steering/product.md`.

| Non-goal | Why |
|---|---|
| **Maximize agent/Skill/tool counts** | "Available" must never mean "loaded in every session". A bigger roster that costs context on every task makes the setup worse, not better. |
| **Auto-install external tools** | Every optional tool carries a supply-chain, permission, and maintenance cost the user has to accept explicitly. `tools-install` prints a pinned command; it never runs one. |
| **Treat popularity as a trust signal** | Star counts, vendor percentages, and adoption numbers are not evidence. Promotion of an optional optimizer requires a local benchmark on the user's own workload. |
| **Become a general orchestrator or model host** | Ratchetry configures the workspace an agent runs in. Driving task queues, terminals, or other agents' sessions is a different product with a different failure surface. |
| **Overwrite human-owned configuration** | Managed blocks, owned hook groups, atomic writes, backups, and dry runs exist so a refresh can never silently eat a user's edits. |
| **Auto-fix or auto-delete on diagnosis** | `doctor` and `agents-status` report; they never repair. Removing an orphaned agent or rewriting drifted config stays an explicit, named action. |
| **Silently lower rigor** | The risk ratchet will not downgrade a recorded tier without a logged acknowledgement, and a project running below a tier it once held keeps saying so on every `doctor` run. |

## Canonical paths

```text
Projects: ~/Projects
Vault:    ~/Obsidian Vault
Runtime:  ~/.local/share/ratchery
Command:  ~/.local/bin/ratchery
Config:   ~/.config/ratchery/config.json
State:    ~/.local/state/ratchery/
```

## Install

Create or select an existing Obsidian Vault before running the installer; the path supplied
to `--vault` must already exist. Use `--dry-run` first to preview every planned change.

```bash
git clone https://github.com/brunoribeirol/ratchery.git
cd ratchery
bash install.sh --vault "$HOME/Obsidian Vault" --projects-root "$HOME/Projects" \
  --project-layout categorized --external-tools none --dry-run   # preview, no writes
bash install.sh --vault "$HOME/Obsidian Vault" --projects-root "$HOME/Projects" \
  --project-layout categorized --external-tools none --yes
```

Then:

```bash
ratchery --version
ratchery doctor-global --deep
ratchery vault-doctor
ratchery tools-status
```

Full flag reference and upgrade/rollback behavior: `docs/INSTALLATION.md`.

Release archives are deterministic and ship with SHA-256 checksums, an SPDX
2.3 SBOM, and GitHub/Sigstore provenance. Verification commands and the exact
publication boundary are documented in `docs/PUBLISHING.md`.

## New project

```bash
ratchery new my-project --category personal
```

## Existing repository

```bash
cd /path/to/repository
ratchery init
ratchery tier-set --pii --users public # review/record real risk facts (required)
ratchery tier                          # see the resulting tier
ratchery doctor --deep
```

Until `tier-set` has been run at least once, the displayed tier is explicitly provisional
and `doctor`/the CI gate fail. Running `tier-set` with no flags confirms the documented
low-risk defaults; pass flags whenever the project handles greater risk.

Day-to-day usage: `docs/USER-GUIDE.md`. Extending the framework (new Skill/Agent/tool
integration): `docs/DEVELOPER-GUIDE.md`.

## Continue work in another agent

The built-in memory backend is explicit and provider-neutral. It keeps at most
one reviewed handoff in the matching project directory of the configured Vault;
nothing is captured automatically and the JSON is not added to QMD's Markdown
index.

```bash
ratchery memory status --path .
ratchery memory handoff show --path . --json
ratchery memory handoff clear --path .          # dry run
ratchery memory backends
```

`workspace-save` writes a handoff only when another client/session will really
continue the work. Writes accept bounded JSON on stdin, derive Git provenance,
reject secret-like material and unsafe paths, and refuse silent replacement.
See [`docs/MEMORY.md`](docs/MEMORY.md) for the schema and write example.

## Optional QMD

Ratchetry never auto-installs QMD. QMD <=2.6.3 is blocked. After manually installing and
verifying a safe stable version newer than 2.6.3:

```bash
ratchery vault-qmd-setup          # plan only
ratchery vault-qmd-setup --apply
ratchery vault-qmd-status
```

## Measure cost before adding tools

Ratchetry never turns a vendor's token-saving claim into a default. With a
manually installed `ccusage`, capture aggregate-only A/B evidence and compare
cost per successful task:

```bash
ratchery usage --source codex --period daily --offline
ratchery budget check --source codex --max-cost-usd 5 --max-tokens 200000
ratchery benchmark show core-suite-v1
ratchery benchmark capture baseline-1 --source codex \
  --session-id BASELINE_SESSION_ID --task-set core-suite-v1 \
  --model MODEL_ID --client-version codex-VERSION \
  --environment-id ENVIRONMENT_ID --configuration native \
  --attempted-tasks 6 --successful-tasks 6
ratchery benchmark capture candidate-1 --source codex \
  --session-id CANDIDATE_SESSION_ID --task-set core-suite-v1 \
  --model MODEL_ID --client-version codex-VERSION \
  --environment-id ENVIRONMENT_ID --configuration rtk-v0.48.0 \
  --attempted-tasks 6 --successful-tasks 6
```

Repeat each arm in fresh sessions at least three times, then use `benchmark
report` with repeated `--baseline`/`--candidate` names. Ratchetry reports
distributions and a quality floor but never makes an automatic adoption
decision. Budget checks are local, offline, read-only estimates; only
`--enforce` opts into exit 3 on a crossed threshold.

Snapshots live outside the repository in local XDG state and contain aggregates
plus reproducibility IDs — no prompt, response, session ID, source code, project
label, or raw usage rows. See
[`docs/BENCHMARKING.md`](docs/BENCHMARKING.md) for the reproducible protocol,
limitations, security profiles, and date-window alternative.

Capture requires a clean checkout and records its current commit. Keep that
checkout unchanged through each measured session: the value is capture-time
provenance, not an attestation over historical ccusage rows.

## Exit codes

- `0` -- success.
- `1` -- the command ran but failed (e.g. a doctor/audit check found errors, an
  unhandled I/O error such as permission denied or disk full, or an explicit
  failure the command reports).
- `2` -- invalid usage (missing/unknown arguments), argparse's own convention.
- `3` -- a `budget check --enforce` threshold or spike warning fired. Without
  `--enforce`, the same observation is advisory and exits 0.

## Examples

`examples/` has five project fixtures showing how the Adaptive Engine's tier changes
requirements: `t0-python-script`, `t1-backend-api`, `t2-data-pipeline`, `t3-ai-application`,
`critical-system`. Each README walks through the actual scoring math.

## Stability policy

Do not add a new integration merely because an optional tool got a new version or a star
count. Every Tool Router addition should be justified the way `docs/research-external.md`
diligences it: what it solves, maturity, license, footprint, and dual-CLI (Claude Code +
Codex) compatibility -- not popularity.

Start at `docs/00-START-HERE.md`. Security model: `SECURITY.md`. License: `LICENSE` (MIT).
