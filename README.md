# Ratchetry

[![CI](https://github.com/brunoribeirol/ratchery/actions/workflows/ci.yml/badge.svg)](https://github.com/brunoribeirol/ratchery/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/brunoribeirol/ratchery/badge)](https://scorecard.dev/viewer/?uri=github.com/brunoribeirol/ratchery)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](docs/INSTALLATION.md)
[![Stdlib only](https://img.shields.io/badge/dependencies-stdlib%20only-brightgreen)](docs/ARCHITECTURE.md)
[Docs](docs/00-START-HERE.md) · [Architecture](docs/ARCHITECTURE.md) · [Issues](https://github.com/brunoribeirol/ratchery/issues)

Ratchetry is a local-first setup for safer, lower-waste AI-assisted development. It turns
a normal repository into a ready-to-use Claude Code and OpenAI Codex workspace with
reviewable permissions, risk-aware project rules, curated agents and Skills, bounded
context, diagnostics, refresh, and rollback.

The practical goal is simple: stop rebuilding your agent setup in every repository, stop
loading every possible tool into every session, and stop relying on prompt text as the
only safety boundary. Ratchetry does not call a model, run a daemon, upload your code, or
auto-install third-party tools.

It is **batteries included, not batteries always running**. The setup ships broad capability,
but specialized agents, process, external tools, and repository context load only when the
project or task justifies their token, permission, dependency, and maintenance cost.

> **Maximum useful capability, minimum justified cost.**

## The shortest useful path

```bash
brew install brunoribeirol/tap/ratchery
ratchery setup --projects-root "$HOME/Projects" --dry-run
ratchery setup --projects-root "$HOME/Projects" --yes

cd /path/to/your/repository
ratchery init
ratchery tier-set   # confirms low-risk defaults; use --help and real risk flags when needed
ratchery doctor --deep
```

That installs the dependency-free core, explicitly configures your user workspace, and
configures the current repository. Obsidian memory is an optional enhancement, not a
prerequisite. Setup preserves human-owned configuration and installs no external optimizer,
scanner, MCP server, or memory service.
On later setup/upgrade runs, omitting both memory flags preserves the existing choice;
`--no-vault` is the explicit way to disable the integration without deleting Vault files.

The Adaptive Engine is the control plane inside that setup. It combines a codebase profile
with explicit human-owned risk facts to select a T0-T3 policy, then applies a one-way risk
ratchet so recorded rigor cannot quietly drop without an acknowledged, logged decision.
The canonical product contract is [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md).

> **Compatibility note:** `ratchery` is the primary command and its config lives
> at `~/.config/ratchery/`. Existing private-development installs may keep using
> `agent-workspace` during the 1.x migration window; both commands execute the
> same installed runtime. The old name is not used for new documentation or paths.

## What's in v1.1

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
Vault:    not configured by default (optional Obsidian memory)
Runtime:  ~/.local/share/ratchery
Command:  ~/.local/bin/ratchery
Config:   ~/.config/ratchery/config.json
State:    ~/.local/state/ratchery/
```

## Install

### Homebrew

The verified public tap is the shortest supported installation path on macOS or Linux:

```bash
brew install brunoribeirol/tap/ratchery
ratchery --version
ratchery setup --projects-root "$HOME/Projects" \
  --project-layout categorized --external-tools none --dry-run
ratchery setup --projects-root "$HOME/Projects" \
  --project-layout categorized --external-tools none --yes
ratchery doctor-global --deep
```

The Formula installs only the immutable runtime. `setup` remains an explicit, reviewable
step and defaults to core-only mode for a new user. It never guesses a Vault path or
auto-installs optional tools.

### Source installation

Use `--dry-run` first to preview every planned change. This path installs the same core
without a memory backend:

```bash
git clone https://github.com/brunoribeirol/ratchery.git
cd ratchery
bash install.sh --projects-root "$HOME/Projects" \
  --project-layout categorized --external-tools none --dry-run
bash install.sh --projects-root "$HOME/Projects" \
  --project-layout categorized --external-tools none --yes
```

Then:

```bash
ratchery --version
ratchery doctor-global --deep
ratchery tools-status
```

Full flag reference and upgrade/rollback behavior: `docs/INSTALLATION.md`.

Package managers install only the immutable runtime. They must never guess a
Vault path or write agent configuration during package installation. Preview
and apply the supported onboarding contract explicitly:

```bash
ratchery setup --projects-root "$HOME/Projects" \
  --project-layout categorized --external-tools none --dry-run
ratchery setup --projects-root "$HOME/Projects" \
  --project-layout categorized --external-tools none --yes
```

### Optional durable memory

If you want curated cross-session memory and provider-neutral handoffs, point Ratchetry at
an existing Obsidian Vault. The same command upgrades a core-only installation:

```bash
ratchery setup --vault "$HOME/Obsidian Vault" --projects-root "$HOME/Projects" \
  --project-layout categorized --external-tools none --dry-run
ratchery setup --vault "$HOME/Obsidian Vault" --projects-root "$HOME/Projects" \
  --project-layout categorized --external-tools none --yes
ratchery vault-doctor
```

Omitting both `--vault` and `--no-vault` preserves an existing memory selection. Use
`ratchery setup --no-vault ...` only when you intentionally want core-only mode; it changes
configuration but never deletes the Vault or its notes.

The Homebrew Formula passed the stable-asset/checksum boundary, strict online
new-formula audit, style check, source installation, isolated setup/doctor tests,
and protected macOS/Linux jobs recorded in `docs/PUBLISHING.md`.

Release archives are deterministic and ship with SHA-256 checksums, an SPDX
2.3 SBOM, and GitHub/Sigstore provenance. Verification commands and the exact
publication boundary are documented in `docs/PUBLISHING.md`.
The public [OpenSSF evidence map](docs/OPENSSF.md) distinguishes the automated
Scorecard from the separately self-certified Best Practices programs; Ratchetry
does not display a Best Practices badge before the application earns it.

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
