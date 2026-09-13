# Historical Decision Matrix — 1.0 Redesign

Primary source: [`research-external.md`](research-external.md), external
tool/framework research originally performed on 2026-08-28 with dated addenda.
The table also cites the internal v8.2.1 baseline and `setup-v5.md`; those are
provenance labels for inputs intentionally excluded from the public repository,
not links or current behavior specifications.

This matrix records how the 1.0 redesign was selected; its “current state”
columns describe the pre-redesign baseline and are deliberately historical.
For current behavior use `README.md`, `ARCHITECTURE.md`, `PROJECT_CONTEXT.md`,
`TOOL_POLICY.md`, and `ROADMAP.md`. New tool proposals must re-check current
upstream facts instead of treating this table as live market research.

Legend: **KEEP** = carry forward unchanged · **CHANGE** = carry forward, modified · **REMOVE** = drop · **NEW** = introduce in v1.0

---

## A. Core engine (carried from v8.2.1's `lib/agent_workspace.py`)

| Feature | Source | Current state | Decision | Rationale |
|---|---|---|---|---|
| Config/state (XDG paths) | v8.2.1 | Real, working | **KEEP** | No issue found; XDG compliance is correct cross-platform default. |
| Atomic writes + per-file/vault backups | v8.2.1 | Real, tested | **KEEP** | Core safety property for an installer; audit confirmed atomicity + rollback-on-failure. |
| Managed-block merge engine | v8.2.1 | Real, tested | **KEEP** | This is exactly the "never destroy human content" mechanism the brief requires (§13, §25). |
| JSON/hook merge with ownership tracking | v8.2.1 | Real, tested | **KEEP** | Prevents silently clobbering user-added hooks — verified by test. |
| Project profiling (`profile()` — size + capabilities) | v8.2.1 | Real, tested | **CHANGE** | This *is* the seed of the Adaptive Engine (§5), but it only outputs a "size" label, not a risk/criticality Tier. Extend to a full T0–T3 classifier (see §B). |
| Command detection → `docs/COMMANDS.md` | v8.2.1 | Real | **KEEP** | Low-risk, useful, no security surface. |
| Conditional skills install/removal | v8.2.1 | Real, tested | **CHANGE** | Mechanism is sound; extend the trigger set beyond 4 hardcoded capabilities to the new Skill Registry (§D). |
| Vault engine (migration, dashboard, wikilinks, frontmatter lint) | v8.2.1 | Real, tested | **KEEP** | Matches §13 requirements almost exactly; do not rewrite working Obsidian logic. |
| Project↔Vault linking (durable UUID) | v8.2.1 | Real, tested | **KEEP** | Genuine collision-avoidance algorithm; no better alternative found in research. |
| QMD integration (version-gated, HOME-scoped) | v8.2.1 | Real, security-hardened | **KEEP** | Research confirms `tobi/qmd` is the healthy, actively-maintained project (29k stars, proportionate ratios); v8.2.1's version gate (≥2.6.4) and HOME-scoping already match its own Aug 2026 security-hardening release. Add Codex CLI verification (unconfirmed by upstream docs). |
| Doctors (`doctor_project`, `global_doctor`, `preflight`) | v8.2.1 | Real, tested | **KEEP + EXTEND** | Extend to validate the new Tier/Risk-Ratchet state (§B) and Context Engine config (§C). |
| CLI (20 subcommands, argparse) | v8.2.1 | Real | **CHANGE** | Keep the pattern; add subcommands for tier classification, tool-router status, cost report (see below). |
| `install.sh` (idempotent, atomic, backup, rollback) | v8.2.1 | Real, tested | **KEEP** | Meets §25 requirements as-is; no redesign needed. |
| `tests/run-tests.sh` | v8.2.1 | Real, but has 1 bug | **CHANGE** | Fix the macOS `/tmp`-symlink `HOME` resolution bug (audit §7) before anything else — trivial, but blocks "tests actually pass on Bruno's machine." |

## B. Adaptive Engine / Tiering / Governance (NEW — biggest gap in v8.2.1)

| Feature | Source | Current state | Decision | Rationale |
|---|---|---|---|---|
| Risk/criticality classifier (T0–T3) | X-PRO (concept only) + v8.2.1's `profile()` (partial) | v8.2.1 has size-only classification; no risk/criticality dimension exists in code | **NEW** | X-PRO's repo itself is 0-star/unproven (research §1) — do not depend on it — but its scoring model (criticality × complexity → tier, with PII/payments/life-safety flags) is the clearest tiering pattern found anywhere in the survey. Reimplement natively as a deterministic YAML-driven scorer layered on top of `profile()`'s existing size/capability signals. |
| Risk ratchet (rigor can't silently decrease) | X-PRO (concept) | Absent | **NEW** | Explicit requirement (brief §6). Implement as an append-only decision log (`~/.agents/state/<project>/tier-history.jsonl`) — a tier downgrade requires an explicit `--acknowledge-downgrade` flag + written rationale, mirroring X-PRO's one-way-ratchet override model. |
| Tier → required agents/skills/policies mapping | NEW, informed by X-PRO's Required/Recommended/Deferred/Discarded gating | Absent | **NEW** | This is what makes tiers *do* something instead of being a label — drives which agents/skills auto-load (§10, §11) and which docs/tests/security gates are required (§21, §22). |
| Steering files (`product.md`/`structure.md`/`tech.md`) | Kiro "Steering" concept (pattern only, not the product) | Absent (v8.2.1 has one flat `docs/PROJECT_CONTEXT.md`) | **NEW** | Kiro itself is proprietary/excluded (research §5), but the topic-scoped, selectively-loaded steering-file pattern is free to reimplement and fits the Context Engine's "load only what's needed" goal better than one monolithic file. |
| Spec-driven planning phase (requirements → design → tasks) | GitHub Spec Kit (reference/companion) | Absent | **NEW, tier-gated** | Current Spec Kit is an extensible harness with presets, workflows, and bundles—not one rigid flow and not the only dual-client option. Ratchetry uses its own dependency-free full template only at T3; teams may install Spec Kit separately. |
| Lightweight delta spec mode | OpenSpec (reference/companion) | Absent | **NEW, tier-gated** | Current OpenSpec explicitly supports Claude and Codex with core/custom workflows. Ratchetry uses a native lightweight delta template at T1/T2 and makes no fixed token-saving claim; T0 has no mandatory spec. |
| BMAD-style multi-persona pipeline | BMAD-METHOD | Absent | **REMOVE (do not adopt)** | Heaviest token cost of the group, documented breakage against both Claude Code and Codex CLI command discovery (research §2). Not worth the integration cost for this framework's stated "minimum always-on cost" principle. |
| Kiro / Kiro Crew | Kiro (AWS) | Absent | **REMOVE (do not adopt)** | Core harness proprietary/credit-metered; competing platform, not a library. Only the steering-file pattern (above) is salvaged. |

## C. Context Intelligence Engine (NEW)

| Feature | Source | Current state | Decision | Rationale |
|---|---|---|---|---|
| "Retrieve what's necessary" retrieval policy | Brief §7, informed by Chroma's "context rot" research | Absent as an explicit engine (v8.2.1 relies on Skill descriptions + `initial_file_budget`) | **NEW, but built on existing `initial_file_budget`** | `profile()` already sets a size-driven initial read budget (audit §2) — extend this into an explicit decision table: search vs. index vs. summarize vs. memory-recall vs. Graphify vs. Serena vs. plain grep, keyed by task type + repo size, documented in a policy file agents actually read. |
| Steering-file selective loading | Kiro pattern (see §B) | Absent | **NEW** | Same rationale as §B — small topic-scoped files loaded on demand instead of one large context dump. |
| `.claudeignore` generation per project | setup-v5.md | **Absent — confirmed real regression** (audit §9) | **NEW (revive)** | Audit explicitly flags this as a genuine functional gap, not a principled removal — closes it. |

## D. Tool Router (NEW — real selection logic, not just doc recommendations)

| Tool | Source | Current v8.2.1 state | Decision | Rationale |
|---|---|---|---|---|
| QMD | v8.2.1 (real) + research | Integrated, security-gated | **KEEP the integration, profile/task-routed** | The integration and lexical fallback are core code; the external QMD binary remains optional, explicitly configured, and never auto-installed. |
| Serena | v8.2.1 (doc-only) + research | Recommendation string only | **CHANGE → real optional integration** | Research's safest pick: proportionate adoption signals, MIT, verified native dual-CLI support, real differentiation over grep. Wire as an actual optional MCP profile (not auto-injected — matches v8.2.1's own "don't auto-inject MCP" principle), with the community `serena-slim` tool-set noted to manage its ~24k-token definition overhead. |
| Context7 | v8.2.1 (doc-only) + research | Recommendation string only | **CHANGE → real optional integration** | Second safest pick: proportionate ratios, MIT, native dual-CLI docs, solves a well-documented failure mode (hallucinated APIs). Optional MCP profile, opt-in per project. |
| Graphify | v8.2.1 (doc-only) + research | Recommendation string only | **CHANGE → optional, with an explicit trust caveat** | Technically the most novel tool (zero-token local AST graph) and it's the tool behind this user's own installed `/graphify` skill — but research flags its 112k-star count as a textbook fake-star signature. Keep as an optional, user-installed tool; do not treat its marketing numbers as an adoption/trust signal in any doc this framework ships; judge only by hands-on output quality. |
| RTK (shell-output compression) | setup-v5.md + research | Reviewable install/init guidance; no automatic install | **CHANGE → experimental until locally measured** | RTK changes the evidence the agent sees. Claude uses a rewrite hook, while Codex currently uses instruction files rather than the same enforcement path. Preview both integrations separately, keep telemetry disabled, verify raw failure-output recovery, and promote only after repeated bundled-suite `benchmark capture/report` evidence shows lower cost per successful task without a quality regression. `tools.lock.json` records the reviewed v0.48.0 metadata; the printed install template requires the independently verified full commit SHA because a tag is mutable. Vendor percentages are not Ratchetry evidence. |
| Caveman | setup-v5.md + research | **Absent entirely** | **CHANGE — revive only the read-only repo-navigation subagent pattern, reject the compression Skill/Proxy** | Audit confirms clean removal with no architectural reason; research independently confirms the "caveman-speak" compression claim (65%) is contradicted by JetBrains' own measurement (8.5%), and the compression engine is BSL-1.1 (not OSI-approved OSS). The bounded, read-only "explore by file/line reference" subagent pattern is genuinely useful and low-risk — reimplement that specific behavior as one of the Core agents' allowed patterns, not as a dependency on the `caveman` package. |
| ripgrep / find / git | Brief §8 | Not itself "integrated" (assumed available) | **KEEP as default path** | Explicit brief requirement: simple search must stay simple search, never force Graphify+Serena+QMD for a string lookup. Encode this as the Tool Router's first, cheapest rule. |
| ast-grep | v8.2.1 + current tool policy | Detected locally | **KEEP as profile capability** | Syntax-aware search only when text search is ambiguous; local scan and no permanent MCP schema cost. |
| gitleaks / Trivy / Semgrep / Checkov / OSV / Syft / Grype | current security research | Catalogued, never installed automatically | **PROFILE / ON-DEMAND** | Start with the smallest scanner matching the artifact/risk. Additional scanners must add findings or required formats beyond the primary scanner; database/network/latency/false-positive cost is explicit. |
| ccusage | current upstream + cost proposal | Expanded local report wrapper and aggregate snapshot source | **KEEP as optional observability** | Reads sensitive local usage history and may refresh pricing unless offline, so it is not “no security surface.” Benchmark capture runs offline from the user's home and persists totals only; task success plus cost, not token volume alone, drives decisions. |
| Context Mode / Agent Scan | current targeted research | Catalogued only | **EXPERIMENTAL / ON-DEMAND** | Context Mode adds MCP/hooks/storage and overlaps with RTK; Agent Scan's external service/token/data-flow and command boundary do not fit a universal local-first core. Neither is auto-installed. |

## E. Security

| Feature | Source | Current state | Decision | Rationale |
|---|---|---|---|---|
| Native sandbox config (Claude `settings.json` + Codex `config.base.toml`) | v8.2.1 | Real, doctor-enforced | **KEEP** | Audit found no bypass; `failIfUnavailable`/`allowUnsandboxedCommands:false` correctly fail closed. |
| Secondary regex PreToolUse hook (secrets/destructive commands) | v8.2.1 | Real, tested, correctly framed as "secondary" in docs | **KEEP + document limits explicitly** | Audit confirms literal-substring bypass exists in theory (obfuscated path construction) but is out-of-scope for a string hook by design — Layer 1 (OS sandbox) is the real boundary. State this limitation explicitly in `docs/security.md` rather than implying the hook alone is sufficient — this directly addresses the brief's "BASH SECRET BYPASS" concern (§14) with an accurate, non-overclaiming description instead of a false sense of security. |
| Prompt-injection defense architecture | NEW, from research (lethal trifecta, Action-Selector/Dual-LLM patterns, Anthropic/OpenAI docs, real CVEs) | Absent as an explicit policy; implicitly relies on Claude Code/Codex's own sandbox | **NEW** | Brief §15 explicitly requires this. Adopt research's synthesis: (1) never combine untrusted-content exposure + private-data access + external egress in one unattended step; (2) tag AGENTS.md/CLAUDE.md/README content as **untrusted project content**, never framework policy, in every agent/skill spec; (3) isolate any web/MCP-fetch tool's output into a bounded, non-instructive summary before it reaches the main loop. This is a documentation + agent-spec-design change (allowed-tools, non-triggers), not new infrastructure. |
| CoSAI Project CodeGuard security rules | NEW (research §8) | Absent | **NEW, optional** | Model-agnostic, native dual-CLI support, free, neutral OASIS governance (post Cisco donation). Young as an independent repo (152 stars) — adopt as an optional security-rules module, track closely, not a hard dependency. |
| `.claudeignore` | setup-v5.md | Absent (real gap) | **NEW (revive)** | See §C — closes a genuine functional/security-adjacent gap (keeps `node_modules`/build output/secrets-adjacent paths out of context by default). |

## F. Agents & Skills

| Feature | Source | Current state | Decision | Rationale |
|---|---|---|---|---|
| 4 core agents (explorer, reviewer, security-reviewer, test-runner) | v8.2.1 | Real, tested, `permissionMode` correctly asymmetric | **KEEP** | No issue found; extend the *set*, don't rewrite these. |
| Additional Core/Specialized/Optimization/Operations agents (brief §10) | Brief | Absent | **NEW, tier-gated, lazy-loaded** | Brief requires a large roster (Architect, Developer, Debugger, QA, Documentation, Backend/Frontend/Data/DB/Cloud/Security/AI-ML/Embedded/DevOps/Performance Engineer, Context/Cost Optimizer, Architecture Auditor, Release Manager, Migration Agent). Build all as spec files (purpose/scope/triggers/non-triggers/allowed tools/context policy/expected output/checklist/failure conditions per brief), but the Adaptive Engine decides which load per task/tier — never all-on, per the brief's own "MAXIMUM CAPABILITY, MINIMUM ALWAYS-ON COST" principle (§4). |
| 15 global Skills (progressive disclosure) | v8.2.1 + v1 additions | Real, working | **KEEP** | All are installed/discoverable, but clients load a Skill body only when its description matches. The former “12 always-on + 3 on-demand” split was not enforced anywhere and has been removed rather than presented as a false token-saving boundary. |
| 4 conditional Skills (capability-triggered) | v8.2.1 | Real, tested | **KEEP + EXTEND** | Extend the capability-detection set as domains grow (embedded, AI/ML, cloud) per brief §11's category list. |
| Skill registry/versioning/dependency model | Brief §11 | Absent (flat directories, no manifest) | **NEW, minimal** | Brief explicitly warns against a fake marketplace. Add a lightweight `registry.json` (name, version, category, triggers, dependencies) sufficient for the Tool Router/Adaptive Engine to reason about what's installed — not a plugin marketplace UI. |

## G. Memory & Obsidian

| Feature | Source | Current state | Decision | Rationale |
|---|---|---|---|---|
| Vault categories (projects/decisions/bugs/session-logs/knowledge/references) | v8.2.1 | Real, working | **KEEP** | Matches brief §12 categories closely already. |
| Hash-only prompt storage, no raw transcripts | v8.2.1 | Real, tested, deliberate | **KEEP** | Correctly rejects v5's chat-import/raw-JSONL Stop-hook pattern — matches brief §12's "don't save secrets/prompts" requirement exactly; do not revive v5's chat-import pipeline. |
| Managed-block dashboard (`VAULT-INDEX.md`) preserving human content | v8.2.1 | Real, tested | **KEEP** | Directly satisfies brief §13's "never destroy manual content" requirement. |
| Local notes/decision retrieval via QMD over the Vault | v8.2.1 + research (tobi/qmd) | Real | **KEEP** | Research independently confirms this is the healthy, well-adopted QMD project; no change needed beyond routing rules (§D). |

## H. OSS packaging, testing, docs (brief §23–29)

| Feature | Source | Current state | Decision | Rationale |
|---|---|---|---|---|
| README/LICENSE/CONTRIBUTING/CODE_OF_CONDUCT/SECURITY/CHANGELOG/ROADMAP | v8.2.1 (partial: README, CHANGELOG exist; rest absent) | Partial | **NEW (fill gaps)** | Required for OSS publication (brief §23, §37). |
| GitHub Actions CI (lint, tests, security scan, release) | Absent | Absent | **NEW** | No CI exists today — required for a credible OSS release. |
| Issue/PR templates | Absent | Absent | **NEW** | Standard OSS hygiene, low cost. |
| License choice | Undecided | v8.2.1 has no LICENSE file | **NEW — recommend MIT** | Matches the license of every well-adopted tool in the research set (Spec Kit, OpenSpec, Serena, Context7, QMD, Agent OS, RTK) — maximizes compatibility for downstream adopters/contributors; no reason found to choose a more restrictive license for a dev-tooling framework meant to be broadly reused. |
| Numbered docs (00–19) | v8.2.1 | Real, accurate (audit confirms docs match code, don't overclaim) | **KEEP + EXTEND** | Add sections for the new Adaptive Engine, Context Engine, Tool Router, Tier/Governance model, prompt-injection policy. |
| Cross-platform (macOS/Linux; Windows partial) | v8.2.1 | Real (stdlib-only Python, POSIX bash) | **KEEP** | Already portable by construction (no personal paths hardcoded found in audit); Windows explicitly out of scope per brief §26. |
| Examples (Python small / backend / data eng / AI app / critical project) | Absent | Absent | **NEW** | Required to demonstrate tier-driven behavior differences (brief §29). |

---

## Summary of net-new work for v1.0

1. **Adaptive Engine**: T0–T3 classifier + risk ratchet + tier→requirements mapping (§B) — the single biggest gap.
2. **Context Engine**: retrieval policy table + steering files + `.claudeignore` generation (§C).
3. **Tool Router**: real routing logic (not just recommendation strings) for QMD/Serena/Context7/Graphify/RTK/ripgrep, with simple-search-stays-simple as the first rule (§D).
4. **Revived from v5, scoped correctly**: RTK (opt-in), Caveman's explore-subagent pattern only (not the compression proxy), `.claudeignore`.
5. **Security additions**: explicit prompt-injection policy (untrusted-content tagging), CoSAI CodeGuard as optional module, explicit documented limits of the secondary hook.
6. **Agent/Skill roster expansion**, tier-gated, spec-file-driven, registry-backed.
7. **Spec-driven planning**, tier-gated: no mandatory spec at T0, a native lightweight
   delta at T1/T2, and a native full phase-gated template at T3. OpenSpec and Spec Kit are
   design references/optional companions, not vendored dependencies.
8. **OSS packaging**: LICENSE (MIT), CI, templates, remaining top-level docs, examples.
9. **One real bug fix carried over**: macOS `/tmp` symlink issue in `tests/run-tests.sh`.

## Explicitly rejected (with reason)

- **BMAD-METHOD** as default — token-heavy, documented breakage on both target CLIs.
- **Kiro / Kiro Crew** as a dependency — proprietary, competing platform.
- **X-PRO, Graphify, Caveman as runtime dependencies** — good ideas, unproven/flagged repos; concepts borrowed natively instead.
- **Full MCP catalog auto-injection** — v8.2.1's own "no auto-injected MCP by default" principle is correct and confirmed by research's security section (MCP registry is large, unaudited, malicious-server surface); keep everything opt-in.
