# Ratchetry Ultimate — External Research (2025–2026)

Original research date: 2026-08-28. Targeted revalidation: 2026-09-07. Numerical
popularity/release values below remain a dated snapshot, not a current trust signal. The
revalidation corrected Spec Kit/OpenSpec positioning, added newer entrants/Sentrux, and
uses upstream documentation for current capabilities. Do not repeat raw marketing numbers
or third-party token/time benchmarks as product claims without a reproducible local eval.

**2026-09-07 primary sources:** [Spec Kit overview](https://github.com/github/spec-kit/blob/main/docs/index.md),
[Spec Kit bundles](https://github.com/github/spec-kit/blob/main/docs/reference/bundles.md),
[OpenSpec supported tools](https://github.com/Fission-AI/OpenSpec/blob/main/docs/supported-tools.md),
[OpenSpec workflows](https://github.com/Fission-AI/OpenSpec/blob/main/docs/workflows.md),
[OpenSpec v1.12.0](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.12.0),
[Codex MCP](https://developers.openai.com/codex/mcp),
[Sentrux](https://github.com/sentrux/sentrux), and
[specs.md](https://github.com/fabriqaai/specs.md).

---

## 1. X-PRO (xprodotai)

**Sources:** https://github.com/cdiegocom/xprodotai · https://xprodotai.cdiego.com/

1. **What it solves** — The gap between best-practice catalogs (AWS/Azure Well-Architected, Google SRE, 12-factor, DORA) and the fact that no project needs full rigor everywhere. Makes "how much process to apply" a deterministic, auditable computation instead of ad hoc judgment, specifically to feed AI coding agents calibrated guardrails.
2. **How it works** — YAML "answers" file scores the project on Criticality (0–15) and Complexity (0–8) plus risk flags (PII, payments, life-safety). A Python generator (`xpro_gen.py`) maps scores to a base Tier (T0–T3) and runs 40 practices across 4 EA layers (Business/Application/Data/Infrastructure) through a gating function assigning Required/Recommended/Deferred/Discarded status. Overrides act as a **one-way ratchet** — risk flags can only raise required rigor, never lower it. Outputs plain Markdown, notably `AI-AGENT-RULES.md`, meant to be fed directly to Claude Code/Cursor/Copilot as guardrails. An `x-pro.lock` file pins catalog version + answers digest for reproducibility.
3. **What's best about it** — The tiering/risk-ratchet governance model itself: explicit, versioned, auditable calibration of engineering rigor per project, with documented trade-offs and reactivation triggers for deferred practices. None of BMAD/Spec Kit/OpenSpec/Kiro have an equivalent explicit tier/risk model.
4. **Mature?** — No. GitHub shows 0 stars, 1 fork, 0 issues, 0 PRs. Three commits total, most recent ~June 28, 2026. No releases/tags.
5. **License** — MIT.
6. **Maintenance status** — Solo, single-day-commit-history dump by one author (Carlos Diego C. P., AWS Ambassador). No community activity, no CI/tests visible.
7. **Cost** — Free, local Python script + Markdown catalog, no hosted service.
8. **Context/token footprint** — Not benchmarked; not itself an agent/MCP server — a static generator producing Markdown an agent reads once/references. Likely low ongoing cost (read-once, not regenerated per turn).
9. **Compatibility with Claude Code** — Explicitly designed for it (docs name Claude Code, Cursor, Copilot); no plugin/MCP, just Markdown files referenced e.g. from CLAUDE.md.
10. **Compatibility with Codex CLI** — Not explicitly named but agent-agnostic by design; nothing blocks pointing Codex CLI at the same output file.
11. **Should it be integrated?** — Conceptually yes as a design pattern; not as a dependency given zero maturity.
12. **Optional or core?** — The *idea* (tiering/ratchet) should inform core architecture; the actual codebase should be treated as reference-only, not a runtime dependency.
13. **Should it be discarded?** — Discard the artifact (0 stars, no tests, no CI, no releases, single author, unproven). Do not discard the idea — reimplement natively.
14. **Verdict** — X-PRO is not a tool to integrate, it's a blueprint to steal from. The tier/ratchet governance model (criticality × complexity → required rigor, irreversible-only escalation, documented deferral trade-offs) is the clearest articulation of this pattern found in the whole survey, but the repo itself is a brand-new, single-author, zero-star, zero-release proof-of-concept. Cite it, borrow the catalog structure, do not depend on it.

---

## 2. BMAD-METHOD

**Sources:** https://github.com/bmad-code-org/BMAD-METHOD · releases page · issues #773, #479, #1152, #1045 · discussion #2322

1. **What it solves** — Turns unstructured "vibe coding" into an agile-flavored, multi-persona pipeline (analyst → PM → architect → dev → QA) so AI-driven development keeps decisions explicit and context durable across a full lifecycle (Clarify → Plan → Build & Verify → Learn & Adjust).
2. **How it works** — npm-installed (`npx bmad-method install`), specialized "agent" personas and "bmad-*" workflows (bmad-build, bmad-loop, bmad-spec, etc.) invoked as slash-style commands, plus web bundles for ChatGPT/Gemini. Requires Node 20.12+, Python 3.10+, `uv`.
3. **What's best about it** — Breadth/depth of the agile role-play model; documented support across 42+ agent platforms; strong for teams wanting full PRD → architecture → story → dev → QA traceability.
4. **Mature?** — Very: ~43–52k GitHub stars, ~6k forks, 2,000+ commits, active npm package, weekly/biweekly minor releases (v6.4.0 → v6.11.0 within a few months of 2026).
5. **License** — MIT.
6. **Maintenance status** — Active and high-velocity, but turbulent — many open compatibility-breaking issues against both Claude Code and Codex CLI.
7. **Cost** — Free/OSS; runs on top of whatever LLM/agent you already pay for.
8. **Context/token footprint** — Heaviest of the spec-driven group: ~31,667 tokens/workflow run reported by independent comparisons; large projects cited at up to ~230M tokens/week (~$2,000+/month/dev in one comparison). In a head-to-head CRM-build benchmark: BMAD 5.5 hours vs. Spec Kit 90 min vs. OpenSpec 12 min (anecdotal, but directionally consistent with its heavier design).
9. **Compatibility with Claude Code** — Works but with real friction: open issues about slash commands not being discovered under `.claude/commands/bmad/` after Claude Code command-manifest changes. A community plugin (`aj-geddes/claude-code-bmad-skills`) exists to smooth this over.
10. **Compatibility with Codex CLI** — Explicitly broken/partial: "BMAD prompts (alpha) don't show up as slash commands in Codex" (issue #1045); Codex uses a different `$command` convention BMAD doesn't natively match.
11. **Should it be integrated?** — Conditionally — only the spec/story/task decomposition workflow, not the full persona stack, given cost and compatibility churn.
12. **Optional or core?** — Optional "heavy mode" only, not core, given footprint and current breakage against both target CLIs.
13. **Should it be discarded?** — Not outright — most battle-tested/adopted spec framework surveyed — but discard as a default; keep as opt-in for teams wanting deep agile traceability who can absorb the token cost.
14. **Verdict** — Most mature and widely adopted spec-driven framework by far, but that maturity comes with real weight: multi-persona workflows burning significantly more tokens than lighter alternatives, plus documented breakage against both Claude Code's command discovery and Codex CLI's `$command` convention. Treat as a reference implementation and optional heavy-mode integration, not a core dependency.

---

## 3. GitHub Spec Kit

**Sources:** https://github.com/github/spec-kit · releases page · https://github.github.com/spec-kit/

1. **What it solves** — Makes specifications the generative source of truth rather than throwaway scaffolding — "Spec-Driven Development" (SDD) reverses the usual flow so specs directly drive implementation.
2. **How it works** — `specify-cli` ships a default Spec → Plan → Tasks → Implement flow,
but the current product is an extensible harness rather than one mandatory rigid sequence.
Users can run steps individually, automate workflows, persist stacked presets, and package
versioned team setups as bundles. It supports Claude Code, Codex, and many other agents.
3. **What's best about it** — Mature, first-party dual-client support plus a real
distribution/composition model (extensions, presets, workflows, catalogs, bundles) that a
team can provision and update rather than reconstruct for every task.
4. **Mature?** — Very: ~120–132k GitHub stars (grew from ~71k Feb 2026 to 111k by June 2026), ~11.9k forks. Reached v1.0.0 Aug 21, 2026, v1.0.1 two days later — very active cadence.
5. **License** — MIT.
6. **Maintenance status** — Very active, official GitHub project, rapid iterative releases, first-party backing.
7. **Cost** — Free/OSS; cost is whatever the underlying agent already charges.
8. **Context/token footprint** — The default multi-artifact SDD flow is structurally heavier
than a single delta note, but upstream publishes no controlled, comparable token benchmark.
Presets/workflows also make the actual footprint configuration-dependent. Do not publish the
old anecdotal CRM timing as evidence of token cost.
9. **Compatibility with Claude Code** — First-class: `/speckit.*` slash commands, documented.
10. **Compatibility with Codex CLI** — First-class: documented "skills mode" via `$speckit-*`, matching Codex's own convention (unlike BMAD's mismatch).
11. **Should it be integrated?** — Yes — most credible, best-maintained, most explicitly dual-compatible of the spec-driven tools.
12. **Optional or core?** — Strong candidate for core if the framework wants a spec-driven planning phase — GitHub-maintained, agent-agnostic, native dual-CLI support without workaround friction.
13. **Should it be discarded?** — No.
14. **Verdict** — A credible optional companion and design reference for full phase-gated
work, but no longer accurately described as the only dual-client or team-provisioning
option. Ratchetry should keep its native templates dependency-free and interoperate rather
than bundle Spec Kit.

---

## 4. OpenSpec

**Sources:** https://github.com/Fission-AI/OpenSpec · releases page · https://openspec.pro/ · https://www.jamasoftware.com/blog/openspec-guide/

1. **What it solves** — Artifact-guided change planning with a smaller default workflow and
custom/expanded workflow selection, without Python setup.
2. **How it works** — npm-installed (`npm install -g @fission-ai/openspec@latest`, Node 20.19+, TS/JS), invoked via `openspec init` and slash commands (`/opsx:propose`). Produces plain-Markdown proposals, living specs, task checklists, archives. Key architectural difference: a **diff-based context strategy** feeding the agent only isolated "spec deltas" for the proposed change rather than full existing-codebase/spec context — the main driver of its lower token cost. Also has a "Stores" (beta) feature for cross-repo/team planning.
3. **What's best about it** — Brownfield-friendly workflow artifacts with a configurable
`core` profile and custom/expanded workflows. Its smaller default surface is compatible
with cost-conscious use, but the old timing comparison is not a controlled token benchmark.
4. **Mature?** — High: ~66.6k GitHub stars, ~4.6k forks. Near-weekly releases v1.4.0 (June 1, 2026) → v1.11.0 (Aug 26, 2026), recently adding Zed editor support, Command Code integration, "Stores" beta.
5. **License** — MIT.
6. **Maintenance status** — Active, near-weekly releases, steady feature shipping.
7. **Cost** — Free/OSS; docs recommend pairing with high-reasoning models (Opus-4.7-class) for best results, which has its own cost implication.
8. **Context/token footprint** — Potentially smaller in the default/core configuration, but
profile, workflow, and delivery choices change the installed artifacts. No upstream
controlled result justifies a universal "lightest" claim.
9. **Compatibility with Claude Code** — Yes, listed among 30+ supported tools, slash-command style (`/opsx:propose`).
10. **Compatibility with Codex CLI** — Explicit and first-class in current upstream docs:
`openspec init --tools codex` installs project Skills and Codex command artifacts. The
default `core` profile and custom workflow selection are documented for Codex as for other
supported clients.
11. **Should it be integrated?** — Yes, especially the token-efficiency pattern — worth adopting as a default "lightweight" spec-driven mode.
12. **Optional or core?** — Good candidate for core when minimizing token spend on incremental/brownfield changes matters; pair as the "light" counterpart to Spec Kit's "structured/heavy" mode.
13. **Should it be discarded?** — No.
14. **Verdict** — A strong optional companion/design reference for lightweight and
brownfield work, with verified Claude and Codex support. Ratchetry's native light template
should remain a dependency-free policy selected at T1/T2, not be marketed as OpenSpec
itself or as proof of a fixed token saving.

---

## 5. Kiro (AWS)

**Sources:** https://kiro.dev/ · https://kiro.dev/pricing/ · https://kiro.dev/crew/ · https://github.com/kirodotdev/kirocrew · https://www.forbes.com/sites/janakirammsv/2026/08/06/aws-open-sources-kiro-crew-but-keeps-the-agent-harness-closed/

1. **What it solves** — Structures "vibe coding" into requirements → design → sequenced tasks before implementation, with parallel multi-agent execution and property-based testing for edge cases unit tests miss.
2. **How it works** — Delivered as IDE (VS Code/Code-OSS fork, Open VSX), CLI, web, mobile, plus the separately open-sourced **Kiro Crew** orchestrator. Converts prompts into executable specs (requirements + architecture + tasks), runs parallel session-persistent agents against them. Supports AGENTS.md, Skills.md, MCP, Agent Client Protocol (ACP). Headless CLI for CI/CD; integrates Figma, Postman, Datadog, Stripe, Terraform.
3. **What's best about it** — Property-based testing baked into spec-to-code; parallel multi-agent execution; first-party AWS enterprise features (IAM/SSO, governance, usage dashboards) — the only tool surveyed aimed at enterprise governance out of the box.
4. **Mature?** — GA May 7, 2026 (announced July 2025) — young GA product, AWS-backed. No GitHub-repo-equivalent maturity signal since core product is hosted/proprietary.
5. **License** — **Split.** Kiro Crew (orchestration layer) is Apache 2.0, fully OSS. The core Kiro CLI agent harness/runtime **remains proprietary and closed-source**, metered by usage credits (confirmed by Forbes coverage).
6. **Maintenance status** — Active, AWS-backed, continued feature releases post-GA (Crew open-sourced ~Aug 2026).
7. **Cost** — Credit-based: Free (50 credits/mo + open-weight models + Sonnet 4.5), Pro $20/mo (1,000 credits), Pro+ $40 (2,000), Pro Max $100 (5,000), Power $200 (10,000). Extra credits $0.04 each. Model-choice multipliers (Opus 2.2x, Sonnet 1.3x, Haiku 0.4x).
8. **Context/token footprint** — Not published in raw token counts, but the credit-multiplier system is an explicit, transparent cost-tiering mechanism — though proprietary/platform-locked, not independently measurable.
9. **Compatibility with Claude Code** — Not a plug-in — a competing platform that happens to offer Claude models as one of several choices inside its own closed harness. No native way to run Kiro's spec workflow inside Claude Code.
10. **Compatibility with Codex CLI** — Same — competing/parallel product. ACP is the only plausible open integration seam; nothing indicates Codex CLI is a supported Kiro Crew harness today.
11. **Should it be integrated?** — No, not as a dependency. The Kiro Crew orchestrator (Apache 2.0) is worth studying for its ACP-based multi-agent pattern; the core product is proprietary and platform-locked.
12. **Optional or core?** — Neither — exclude from the dependency tree; treat as competitive/design reference only.
13. **Should it be discarded?** — Yes as an integration target — its most valuable ideas sit behind a closed, credit-metered, AWS-proprietary harness architecturally competing with (not complementing) a Claude Code/Codex CLI framework. Kiro Crew alone could be evaluated separately as an orchestration reference.
14. **Verdict** — AWS's own competing agentic IDE, not something to integrate — its best ideas (property-based testing, parallel multi-agent execution, spec-to-task pipeline) are locked behind a proprietary, credit-metered CLI harness barely three months into GA. The one reusable piece is the separately open-sourced Kiro Crew orchestrator (Apache 2.0, ACP-based) — worth a look purely as a design reference. Discard Kiro-as-a-whole as an integration candidate; treat as competitive intelligence.

### Spec-driven frameworks — cross-cutting summary
- **X-PRO**: steal the governance model, discard the code.
- **Spec Kit**: mature optional full-workflow companion; not a required dependency.
- **OpenSpec**: verified dual-client optional companion and reference for a smaller core flow.
- **BMAD-METHOD**: most adopted overall, heaviest on tokens, real friction with both target CLIs — optional/opt-in only.
- **Kiro**: exclude as integration target; only Kiro Crew (Apache 2.0) worth studying.

---

## 6. Agent OS (buildermethods/agent-os)

**Sources:** https://github.com/buildermethods/agent-os · discussion #310 · CHANGELOG.md · https://landscape.jimmysong.io/projects/agent-os/

1. **What it solves** — Reduces inconsistency in AI-generated code by giving agents persistent, structured knowledge of a codebase's standards, and by improving spec quality before implementation begins (avoiding "vibe coded" drift from conventions).
2. **How it works** — File-based system with commands (`/shape-spec`, standards discovery/indexing) that extract patterns/conventions from an existing codebase into documented standards files, intelligently inject the relevant subset into an agent's context based on the task, and structure spec creation via targeted questioning before build. v3 (2026) narrowed scope to standards injection + spec shaping, deferring task execution/review to the host tool.
3. **What's best about it** — Tool-agnostic (Claude Code, Cursor, Antigravity, others); lightweight, markdown/file-based, no runtime dependency; deliberate scope discipline in v3 rather than feature creep.
4. **Mature?** — Fairly: created July 2025, 5,343 stars, only 2 open issues (well-triaged), active commits through mid-2026, structured CHANGELOG, discussion-driven roadmap.
5. **License** — MIT.
6. **Maintenance status** — Active; pushed as recently as May 2026, v3 reflects ongoing design iteration; a commercial "Builder Methods Pro" community exists alongside the free OSS core.
7. **Cost** — Free/OSS; optional paid "Builder Methods Pro" for community/support, not required.
8. **Context/token footprint** — Not independently benchmarked; footprint scales with how much of the standards library is relevant per task (selective injection by design) rather than being fixed.
9. **Compatibility with Claude Code** — Yes, explicitly designed for it.
10. **Compatibility with Codex CLI** — Not explicitly confirmed; framework-agnostic by design (markdown + commands) so likely portable, but not named alongside Claude Code/Cursor/Antigravity in sources found — flag as unverified.
11. **Should it be integrated?** — Yes.
12. **Optional or core?** — Optional-but-recommended — a spec/standards convention, not a runtime dependency, fits well as opt-in.
13. **Should it be discarded?** — No — clean, mature, low-risk, MIT, addresses a real gap (standards drift).
14. **Verdict** — A well-maintained, appropriately-scoped, MIT-licensed convention for spec-driven development and codebase-standards injection; its v3 pivot toward doing one thing well makes it a good complementary optional module, though Codex CLI compatibility should be verified hands-on before being marketed as such.

---

## 7. AWS/Kiro "Steering" concept

**Sources:** https://builder.aws.com/content/3ELQi0SxjCJDdqFRtdLKiaCfcv5/kiro-steering-bringing-infrastructure-level-consistency-to-ai-assisted-development · https://kiro.dev/pricing/ · https://repost.aws/articles/AROjWKtr5RTjy6T2HbFJD_Mw/

1. **What it solves** — The "blank slate" problem: agents that don't persist project-specific architecture/conventions/tech-stack knowledge across sessions and produce code ignoring team standards.
2. **How it works** — Kiro reads modular "steering" markdown files at session start from `.kiro/steering/` (project) or `~/.kiro/steering/` (global): auto-generated `product.md` (goals/personas), `structure.md` (architecture/folders), `tech.md` (stack/tooling), plus custom steering files teams add (security, logging standards). Pairs with Kiro's spec-driven workflow (EARS-notation requirements → design → tasks) and enforcement "hooks."
3. **What's best about it** — Clean separation of concerns by topic (vs. one monolithic instruction file), improving selective loading and maintainability; auto-scaffolded on init; the *pattern* is portable independent of the Kiro product.
4. **Mature?** — The concept is well-documented and production-used in the AWS ecosystem; Kiro itself GA'd Nov 2025, actively marketed in 2026 with case studies.
5. **License** — Kiro itself proprietary; the steering-files convention (plain markdown) is not license-encumbered and freely reproducible.
6. **Maintenance status** — Active, live AWS product with ongoing updates.
7. **Cost** — Same Kiro credit pricing as above.
8. **Context/token footprint** — Selective per-session loading of small topic-scoped files is the design intent; no independent benchmark found — footprint scales with number/size of steering files maintained.
9. **Compatibility with Claude Code** — Not a plug-in — proprietary Kiro feature — but the pattern maps directly onto CLAUDE.md and could be replicated as multiple topic-scoped files loaded via imports.
10. **Compatibility with Codex CLI** — Same — not natively compatible, but AGENTS.md could adopt an analogous multi-file steering convention.
11. **Should it be integrated?** — Yes — as a pattern to reimplement, not a dependency (Kiro can't be embedded).
12. **Optional or core?** — Core pattern worth adopting (multi-file, topic-scoped persistent context), implemented natively rather than depending on Kiro.
13. **Should it be discarded?** — No — but "integrating Kiro directly" isn't applicable; only the concept transfers.
14. **Verdict** — Not a tool to integrate but a proven UX pattern (structured, auto-scaffolded, topic-separated persistent context) worth reimplementing natively — likely as a `structure.md`/`tech.md`/`product.md` split loaded via CLAUDE.md/AGENTS.md imports — since it demonstrably improves on a single monolithic memory file at zero dependency/cost.

---

## 8. Cisco Project CodeGuard → now CoSAI's Project CodeGuard

**Name verification:** Renamed/rehomed. In February 2026, Cisco donated Project CodeGuard to the **Coalition for Secure AI (CoSAI)**, an OASIS Open Project. Canonical repo moved to `github.com/cosai-oasis/project-codeguard`, governed by CoSAI's "AI Security Risk Governance Workstream" SIG.

**Sources:** https://www.oasis-open.org/2026/02/09/cisco-donates-project-codeguard-to-coalition-for-secure-ai/ · https://www.coalitionforsecureai.org/ciscos-donation-of-project-codeguard-to-cosai-a-new-chapter-in-securing-ai-generated-code/ · https://github.com/cosai-oasis/project-codeguard · https://blogs.cisco.com/ai/cisco-donates-project-codeguard-to-the-coalition-for-secure-ai · https://tessl.io/blog/double-your-coding-agents-ability-to-write-secure-code-with-the-codeguard-skill/

1. **What it solves** — Security vulnerabilities introduced by AI coding agents (skipped input validation, hardcoded secrets, weak crypto, unsafe functions, missing auth) by preventing them at generation time rather than catching them via post-hoc scanning.
2. **How it works** — Model-agnostic security skills/rules framework in a unified markdown format, with translators converting it into IDE/agent-specific formats. Rules split into "Core Rules" (foundational: hardcoded-credential detection, crypto validation) and "OWASP Rules" (technology-specific: SQLi, XSS, Kubernetes hardening, mobile). Covers design guidance, generation-time prevention, and AI-assisted code review.
3. **What's best about it** — Genuinely agent-agnostic (Claude Code, Codex, Cursor, Windsurf, GitHub Copilot, Antigravity); now under neutral multi-vendor governance (CoSAI/OASIS) rather than single-vendor control; addresses an underserved gap (secure-by-construction vs. scan-after-the-fact).
4. **Mature?** — Early-stage as an independent OSS project: ~152 stars, 30 forks — modest, consistent with a very recent (Feb 2026) donation. CoSAI itself has 40+ industry partners giving institutional weight.
5. **License** — Open source under CoSAI/OASIS governance (OASIS Open Projects typically use Apache-2.0/CC-BY); exact SPDX identifier not confirmed — verify directly against the repo's LICENSE file.
6. **Maintenance status** — Active — recent donation with visible CI activity, governed by a dedicated CoSAI SIG rather than a single company's roadmap.
7. **Cost** — Free/OSS.
8. **Context/token footprint** — Not benchmarked; rule/skill markdown files translated per-agent, footprint depends on how many rule files load (similar in nature to Agent OS's standards injection).
9. **Compatibility with Claude Code** — Yes, explicitly named, including a dedicated Claude Code skill packaging (per third-party coverage).
10. **Compatibility with Codex CLI** — Yes, explicitly listed among supported agents.
11. **Should it be integrated?** — Yes.
12. **Optional or core?** — Recommend core for any framework claiming production-readiness — security-by-construction is defensible and visible to recruiters/leads/investors; multi-agent translator design avoids vendor lock-in.
13. **Should it be discarded?** — No.
14. **Verdict** — Real and well-governed (now CoSAI/OASIS, not single-vendor Cisco), directly relevant, model-agnostic, markdown-based, with native Claude Code and Codex CLI support. Young as an independent repo (modest stars, recent donation) — track closely and adopt early rather than treating as fully battle-tested, but low cost (free, markdown-only) makes early integration low-risk.

---

## 9. RTK (Rust Token Killer, rtk-ai/rtk)

**Sources:** https://github.com/rtk-ai/rtk · https://www.rtk-ai.app/ · https://codex.danielvaughan.com/2026/05/19/rtk-codex-cli-token-optimisation-shell-output-compression/ · https://dev.to/arshtechpro/how-rtk-reduces-llm-token-usage-for-ai-coding-agents-2kfd

1. **What it solves** — LLM context/token bloat from verbose raw CLI output (git, npm, docker, build/test logs) dumped unfiltered into an agent's context window.
2. **How it works** — Rust CLI proxy intercepting shell commands, compressing output via smart filtering, grouping, truncation, and deduplication (with repetition counts) before it reaches the LLM. Single dependency-free binary; auto-rewrite hook transparently rewrites `git status` → `rtk git status`, etc.
3. **What's best about it** — Narrow, well-scoped problem (shell-output compression only); extremely lightweight (<10ms overhead, single Rust binary, zero deps); broad coverage (100+ commands, claims 89% average compression across 2,900 real-world samples); first-class hooks for both Claude Code and Codex CLI.
4. **Mature?** — Fast-growing: created Jan 22, 2026, ~77,745 GitHub stars by late Aug 2026 (viral within ~7 months), 2,073 open issues (high engagement but also a triage-backlog risk signal), continuous release cadence (v0.46.0 stable plus frequent RCs through Aug 26–28, 2026).
5. **License** — Apache 2.0.
6. **Maintenance status** — Very active — pushed same day as this research, rapid RC/release cadence.
7. **Cost** — Free/OSS, no paid tier found.
8. **Context/token footprint** — This is the product: claims 60–90% reduction in bash-output tokens, but docs caveat this doesn't map 1:1 to total session/billing token reduction (bash output is only one part of context). Token estimation is approximate (bytes/4 heuristic) — treat quoted percentages as directional, not exact.
9. **Compatibility with Claude Code** — Yes, first-class, `PreToolUse` hook, native binary integration (`rtk init -g`).
10. **Compatibility with Codex CLI** — Yes, first-class (`rtk init -g --codex`), via AGENTS.md and RTK.md instruction files.
11. **Should it be integrated?** — Yes.
12. **Optional or core?** — Optional but high-value, low-risk opt-in default (near-zero overhead, dual-CLI support) — should remain toggleable since it changes what the agent literally sees, which matters for debugging.
13. **Should it be discarded?** — No — but monitor the 2,073-open-issues count and heavy RC-release pattern as a maturity-risk signal; pin a specific stable version rather than tracking `main`.
14. **Verdict** — Real, narrowly-scoped, Apache-2.0, actively-maintained Rust shell-output compressor with explicit first-class dual-CLI hooks — strong, low-risk integration candidate as an optional default. Very recent (Jan 2026) with heavy pre-release cadence, so pin versions and treat precise compression numbers as marketing-adjacent rather than independently audited.

---

## 10. Caveman (JuliusBrussee/caveman)

**Sources:** https://github.com/juliusbrussee/caveman · https://github.com/JuliusBrussee/caveman-code · https://docs.caveman.so/ · https://caveman.so/products/caveman-agent · https://blog.jetbrains.com/ai/2026/07/speak-to-ai-agents-like-cavemen-tosave-tokens/

1. **What it solves** — Positioned as reducing token consumption via (a) compressed "caveman-speak" agent narration and (b) a "caveman explore" repository-understanding feature locating code by file/line without loading whole files.
2. **How it works** — Two components: **the Skill** (MIT, `/caveman` in Claude Code) makes the agent narrate in compressed telegraphic language while leaving code/commands/errors verbatim; **Caveman Proxy/engine** (BSL-1.1) is a local proxy compressing what the agent *reads* before it reaches the provider, using content-type-aware routing (JSON, logs, code, diffs, search results, prose). `caveman explore install` deploys a read-only "FastContext" subagent for repo understanding — locating code by path/line rather than ingesting full files. This is the closest match to a "repository understanding tool" in the description, but is one feature within a broader compression product, not a standalone repo tool.
3. **What's best about it** — The repo-exploration subagent concept (bounded, read-only, locate-by-reference) is genuinely useful for large-repo work; dual Claude Code + Codex CLI support; independently benchmarked by JetBrains (rare for this category), which found no quality/readability degradation.
4. **Mature? — CAUTION FLAG.** On paper very large: created Apr 4, 2026, 101,635 stars, 5,900 forks by late Aug 2026 — viral growth in under 5 months. Treat this the same way as Graphify's star count below: not necessarily reliable as an organic-adoption signal given the pattern (see item 14).
5. **License** — Split: MIT for the Skill/Agent SDK/CLI/client SDKs; **BSL-1.1** (Business Source License) for the engine/proxy runtime, converting to Apache-2.0 ~June 2030. BSL is source-available but **not OSI-approved open source** and typically restricts production/commercial use pre-conversion — verify terms before depending on the proxy.
6. **Maintenance status** — Active — releases through Aug 23, 2026 (v2.3.1), frequent point releases.
7. **Cost** — Free (Skill/CLI, MIT); the compression Proxy is BSL-1.1 (possible commercial-use restrictions pre-2030); "Caveman Cloud" is a separate paid product (currently waitlist).
8. **Context/token consumption footprint — INDEPENDENTLY CONTRADICTED.** Marketing claims 65% token reduction / "33.2% fewer provider-reported input tokens." **JetBrains' independent benchmark (86 paired tasks, ~240 trials, Claude Code 2.1.200, SkillsBench) measured only 8.5% actual savings** under forced-activation (best case) — likely lower under normal auto-triggered use. JetBrains also found the Skill itself adds ~1–1.5k input tokens/turn overhead, and Caveman's own docs admit already-terse workloads can go net-negative.
9. **Compatibility with Claude Code** — Yes, native, `/caveman` slash command.
10. **Compatibility with Codex CLI** — Claimed, via environment-variable wrapping — sounds less mature/first-class than RTK's (requires "ephemeral login handling" per source, more friction).
11. **Should it be integrated?** — Partial yes — specifically the "caveman explore" read-only repo-navigation subagent pattern is worth adopting/reimplementing; the caveman-speak compression Skill is lower-value given the marketing/reality gap.
12. **Optional or core?** — Optional, narrowly scoped to the repo-exploration subagent behavior if adopted at all — audit BSL commercial-use terms before adopting the proxy for anything shipped/sold.
13. **Should it be discarded?** — The full "caveman-speak" Skill/Proxy bundle: largely yes — independently measured savings (~8.5%) are far below marketed claims (65%), and BSL licensing on the actual compression engine adds legal diligence overhead for a modest, unverified benefit. The repo-understanding subagent *concept*: no, worth studying/reimplementing.
14. **Verdict** — Real and growing extremely fast, but the one tool in this survey with a documented, independently-verified gap between marketing claims and measured results (JetBrains: 65% claimed vs. 8.5% measured). The star count (101k in under 5 months) reads more as a viral novelty-marketing signal ("talk like a caveman") than proven engineering value, and split MIT/BSL licensing means the actual compression engine isn't fully open source. Borrow the repo-navigation subagent pattern; pass on the compression Skill/Proxy as a dependency.

---

## 11. Graphify (Graphify-Labs/graphify)

**Sources:** https://github.com/Graphify-Labs/graphify · GitHub API · https://cmustrudel.github.io/papers/icse2026fakestars.pdf · https://www.startuphub.ai/ai-news/cybersecurity/2026/github-fake-stars-reputation-as-a-service

*(This is the underlying open-source project behind the `/graphify` skill installed in this user's own Claude Code environment — treat as directly relevant.)*

1. **What it solves** — Turns a codebase (plus docs, SQL schemas, configs, PDFs, images, video/audio) into a queryable knowledge graph instead of relying on grep/vector search, so an agent can traverse explicit and inferred relationships rather than re-reading files.
2. **How it works** — Local, deterministic tree-sitter AST parsing (no LLM, no tokens, ~40 languages); every graph edge tagged `EXTRACTED` (explicit in source) or `INFERRED` (derived). No vector store — a real traversable graph (Neo4j/Postgres optional backends). An *optional* semantic pass for docs/PDFs/images calls an LLM backend of choice (Anthropic/OpenAI/Gemini/DeepSeek/Kimi/Bedrock/local Ollama). Local video/audio transcription via faster-whisper. Ships as a CLI (`uv tool install graphifyy`) plus an installable skill/rule for 15+ agent tools.
3. **What's best about it** — Zero-token, zero-API code-only path (pure AST, fully offline); explicit provenance tagging so edges can be trust-checked; multi-modal beyond code; git-friendly output with a merge driver, suited to team repos.
4. **Mature? — CAUTION FLAG.** Very active dev (near-daily releases, currently pre-1.0 v0.9.x, 1,586+ commits). **But 112,022 stars on a repo created 2026-04-03 (~5 months old) is an extreme anomaly** — independent research on GitHub fake-star campaigns (CMU/Socket/NCSU study; StartupHub.ai coverage) documents a mature market for purchased/bot stars, and a repo hitting six-figure stars in under 5 months without proportionate forks/issues discourse is a classic fake-star signature. Forks (10,886) and open issues (1,158) are non-trivial but still disproportionately low relative to the star count. **Do not use the star count as a maturity signal** — judge by commit cadence and issue/PR activity instead, which look genuinely active.
5. **License** — Apache-2.0 / MIT dual (Apache-2.0 per repo metadata).
6. **Maintenance status** — Actively maintained: releases roughly daily through Aug 2026, last push 2026-08-28 (today).
7. **Cost** — Free/OSS. Code-only extraction: $0 API cost. Semantic pass costs whatever the chosen LLM provider charges (or $0 with local Ollama).
8. **Context/token footprint** — Code extraction is zero-token (local AST). Generated `GRAPH_REPORT.md`/`graph.json` become artifacts read on-demand rather than re-parsing the repo, which should reduce repeated-read token cost — but no independent third-party benchmark found; this is a vendor claim.
9. **Compatibility with Claude Code** — Native — ships as a `/graphify` skill with PreToolUse hooks (confirmed: this is the exact skill installed for this user).
10. **Compatibility with Codex CLI** — Native: `graphify codex install` + AGENTS.md integration per repo docs.
11. **Should it be integrated?** — Conditionally yes, with a verification step: pilot it on a real repo and judge output quality independently rather than trusting the star count.
12. **Optional or core?** — Optional until the project crosses 1.0 and output correctness is personally validated — pre-1.0, fast-moving tools are risky to make load-bearing.
13. **Should it be discarded?** — Not outright — flag the star-count anomaly explicitly whenever citing adoption; discard only if hands-on testing shows output quality doesn't match marketing.
14. **Verdict** — The most technically novel tool surveyed (only one doing whole-codebase relationship graphing at zero token cost via local AST) and already the tool behind this user's own installed skill — but its GitHub star count (112k on a 5-month-old repo) shows the textbook signature of fake-star inflation, so validate independently before trusting any adoption claim; judge purely on pilot-run output quality, not social proof.

---

## 12. Serena (oraios/serena)

**Sources:** https://github.com/oraios/serena · GitHub API · https://github.com/oraios/serena/blob/main/roadmap.md · https://github.com/mcpslim/serena-slim · https://dev.to/basilskywalk/i-ab-tested-an-mcp-server-that-cut-my-claude-code-token-cost-3egh

1. **What it solves** — Gives coding agents IDE-level semantic code understanding (go-to-definition, find-references, symbol-level rename/move/inline) instead of forcing grep + whole-file reads to infer structure, which wastes tokens and is error-prone at scale.
2. **How it works** — MCP server wrapping LSP backends (open-source LSPs by default, 40+ languages; optional paid JetBrains-plugin backend for deeper analysis). Exposes tools like `find_symbol`, `find_referencing_symbols`, `replace_symbol_body`, operating at symbol/relational level rather than raw text.
3. **What's best about it** — No API/LLM cost of its own (pure LSP, fully local); genuinely differentiated from text-grep MCP servers; broad client support (Claude Code, Codex CLI, Claude Desktop, VSCode, Cursor, JetBrains, Gemini CLI, OpenWebUI).
4. **Mature?** — Yes, verified via GitHub API: 28,581 stars, 1,929 forks, 3,308+ commits, 153 open issues — healthy, proportionate activity typical of legitimate adoption. Created 2025-03-23 (~17 months old).
5. **License** — MIT.
6. **Maintenance status** — Active; last push 2026-08-20.
7. **Cost** — Free (LSP backend, no API costs); optional paid JetBrains-plugin backend for extra features (free trial available).
8. **Context/token footprint** — Real, documented tradeoff: base Serena loads ~29 tools consuming ~23,878 tokens of context overhead just for tool definitions (per third-party `serena-slim` benchmarking). A community fork `mcpslim/serena-slim` claims 50.3% reduction (18 grouped tools) with no functionality loss. Per-call payoff is real: "read 30k raw tokens to understand a module" style tasks reportedly compress to a few hundred tokens via `find_symbol`-style calls.
9. **Compatibility with Claude Code** — Yes, first-class, explicitly tested/documented.
10. **Compatibility with Codex CLI** — Yes, explicitly documented and tested (GPT-5.x per docs).
11. **Should it be integrated?** — Yes — the safest, best-evidenced pick surveyed: real adoption, real differentiation, free, proven dual-client support.
12. **Optional or core?** — Core for any repo above small/medium size where symbol-level navigation materially beats grep — but manage the ~24k-token tool-definition overhead (evaluate `serena-slim` or scope which tools load) so it doesn't eat context budget on smaller tasks.
13. **Should it be discarded?** — No.
14. **Verdict** — The safest, best-evidenced integration of the whole survey: legitimately adopted, actively maintained, free, dual-compatible with Claude Code and Codex CLI, solving a real problem — the only real design decision is managing its tool-definition context overhead via a slimmed tool set or on-demand loading.

---

## 13. Context7 (upstash/context7)

**Sources:** https://github.com/upstash/context7 · GitHub API · https://context7.com/docs/clients/codex · https://upstash.com/blog/context7-mcp

1. **What it solves** — LLMs train on stale library/API docs and hallucinate deprecated methods/signatures. Context7 fetches current, version-specific docs for a library at query time and injects them into context.
2. **How it works** — Two tools: `resolve-library-id` (maps a library name to a Context7 ID) and a docs-fetch tool (`get-library-docs`) pulling version-pinned documentation. Two access modes: MCP server (`@upstash/context7-mcp` via npx, or hosted `https://mcp.context7.com/mcp`) and a standalone `ctx7` CLI/skill mode not requiring MCP at all.
3. **What's best about it** — Directly solves a very common, costly failure mode (hallucinated APIs) with a simple two-tool interface; huge library coverage (9,000+ per third-party writeups); works as MCP or plain CLI; free, API key optional (only for higher rate limits).
4. **Mature?** — Verified via GitHub API: 61,356 stars, 2,957 forks, 948 commits, 65 open issues, created 2025-03-26 (~17 months old) — a much healthier stars:forks:issues ratio than Graphify's, consistent with organic adoption. Backed by Upstash, an established infra company.
5. **License** — MIT.
6. **Maintenance status** — Very active; last push 2026-08-28 (today).
7. **Cost** — Free tier with standard rate limits; free API key raises limits; no paid tier surfaced (appears free-first, likely monetized via Upstash's broader platform).
8. **Context/token footprint** — Not explicitly quantified; bounded by whatever doc excerpt `get-library-docs` returns (typically a targeted snippet, not a full dump) — reasonable to assume moderate/low per-call cost, but no independent benchmark found.
9. **Compatibility with Claude Code** — Yes, first-class: `npx ctx7 setup --claude` / standard MCP config.
10. **Compatibility with Codex CLI** — Yes, explicitly documented across all three Codex surfaces (CLI, Desktop, Cloud) via `codex mcp add` or shared config. Per third-party coverage, "the most widely adopted documentation MCP server in the Codex CLI ecosystem."
11. **Should it be integrated?** — Yes.
12. **Optional or core?** — Core for any agent workflow touching third-party libraries/frameworks with fast-moving APIs (React, Next.js, AWS SDKs, etc.) — the hallucinated-API failure mode is common enough to justify default-on.
13. **Should it be discarded?** — No.
14. **Verdict** — Well-adopted, well-maintained, dual-compatible tool from a credible infra vendor solving a genuinely common pain point at no cost — one of the safer, higher-confidence integrations surveyed. Measure actual per-call token cost before deciding how aggressively to default it on.

---

## 14. QMD

Two distinct GitHub projects share this name — presenting both rather than guessing.

### 14a. tobi/qmd — primary candidate, much larger adoption

**Sources:** https://github.com/tobi/qmd · GitHub API · https://gamgee.ai/blogs/tobi-lutke-qmd-local-semantic-search/ · https://knightli.com/en/2026/05/01/qmd-markdown-search-for-ai-agents/

1. **What it solves** — On-device search over markdown notes, meeting transcripts, docs, knowledge bases — a local "memory" layer an agent can query mid-session instead of guessing project conventions or re-reading files.
2. **How it works** — Three-stage hybrid pipeline: BM25 full-text + vector semantic search, fused via Reciprocal Rank Fusion, then LLM reranking, running locally via `node-llama-cpp` with local GGUF models (no cloud calls). Documents chunked (~900 tokens, tree-sitter-aware as of v2.1.0), preserving markdown section boundaries. Exposes a CLI (`--json`, `--files` flags for agentic use) and an MCP server (`query`, `get`, `multi_get`, `status`; HTTP transport for long-running servers).
3. **What's best about it** — Fully local/private (no data leaves the machine, no API key); fast-moving (releases every 1–4 weeks); official `qmd skill install` for Claude and a stable SDK (`QMDStore`, v2.0.0+).
4. **Mature?** — 29,328 stars, 1,833 forks, 128 open issues (verified via GitHub API) — proportionate ratios suggest organic adoption. Created 2025-12-08 (< 9 months old), versioning at v2.8.3.
5. **License** — MIT.
6. **Maintenance status** — Very active: last push 2026-08-18, a security-focused release (v2.8.3, Aug 16) adding trust gates for update hooks/external paths.
7. **Cost** — Free/OSS, fully local (no API costs); ~2GB disk for cached local models, GPU optional.
8. **Context/token footprint** — Local model inference doesn't consume the host LLM's context tokens; MCP responses return targeted chunks (~900 tokens each) rather than full documents. No independent third-party token benchmark beyond this architectural claim.
9. **Compatibility with Claude Code** — Yes: `qmd skill install`, MCP server integration, Claude Desktop plugin via MCP Registry.
10. **Compatibility with Codex CLI** — Not explicitly confirmed — sources describe Claude Code/Desktop and generic "MCP-compatible agents" but don't name Codex CLI specifically. Plausible via manual MCP config but unverified.
11. **Should it be integrated?** — Conditionally yes, specifically as a project-memory/notes-retrieval layer (distinct use case from Serena/Graphify/Context7, which target code and library docs, not personal notes/decisions/session logs) — overlaps conceptually with this user's own `record-decision`/`workspace-save` Obsidian workflow.
12. **Optional or core?** — Optional — a narrower, more personal problem than the other three, with unverified Codex CLI support.
13. **Should it be discarded?** — No, but confirm Codex CLI support before citing it as dual-compatible.
14. **Verdict** — A credible, actively-maintained, fully local, security-conscious markdown/notes search tool with real, verified adoption — a good optional add for agent-memory/notes retrieval (e.g. over an Obsidian vault) rather than a core codebase tool, pending direct verification of Codex CLI support.

### 14b. ehc-io/qmd — smaller alternate project, same name (disambiguation only)

- Same conceptual space (BM25 + vector search over markdown, MCP server: `qmd_search`, `qmd_vector_search`, `qmd_deep_search`, `qmd_get`).
- Adoption: 16 stars, 2 forks, 0 open issues (verified via GitHub API) — essentially unadopted relative to tobi/qmd.
- License: MIT. Last push 2026-02-25 — ~6 months stale.
- No Codex CLI mention found.
- **Verdict: discard in favor of tobi/qmd** — near-identical concept, dramatically lower adoption, staler.

Source: https://github.com/ehc-io/qmd

---

## Additional findings — other notable 2025–2026 entrants

**OpenCode** — https://opencode.ai/ — SST/Anomaly fork after the original project archived Sept 2025. Terminal-first, provider-agnostic (Anthropic/OpenAI/Gemini/Bedrock/etc.) coding agent with Plan/Build modes, LSP+MCP+custom commands, TUI. Crossed 160k GitHub stars and ~7.5M monthly devs by early 2026 — now the most popular OSS coding agent by star count, and the most direct "layer on top of any model" competitor to the framework being designed here.

**Repomix** — https://github.com/yamadashy/repomix / https://repomix.com. Packs a whole repo into one AI-friendly XML/Markdown/JSON file with per-file token counts, Secretlint-based secret scrubbing, and tree-sitter compression (~70% token reduction). 26.2k stars, ~255k npm downloads/month. Directly relevant to context-engineering layers; its secret-scrubbing step is also a useful reference for a "don't leak credentials into agent context" mitigation, adjacent to the injection-defense theme.

**MCP registry/governance shift** — The official MCP Registry (https://github.com/modelcontextprotocol/registry) launched preview Sept 8, 2025, hit API freeze (v0.1) Oct 24, 2025, and grew to ~2,000 entries; third-party directories (Smithery, "the Docker Hub of MCP") list 7,000–16,000+ servers. Most significant: **in December 2025 Anthropic donated MCP itself to a new Agentic AI Foundation under the Linux Foundation**, making it vendor-neutral. This matters directly for the framework's MCP integration story — governance is no longer Anthropic-only, and the registry's rapid, unaudited growth is exactly the "malicious MCP server" surface covered in the security section below (Anthropic explicitly disclaims security-auditing servers even in its own directory).

**Agent memory frameworks** — landscape consolidated around four names: **Mem0** (https://mem0.ai — key-value memory via dense embeddings; April 2026 shipped a token-efficient single-pass hierarchical extraction algorithm plus a memory-compression engine, directly relevant to context-budget management), **Letta** (formerly MemGPT — OS-inspired three-tier memory: core/archival/recall), **Zep** (temporal knowledge-graph memory for multi-session reasoning), and **Cognee**. Comparative writeup: https://dev.to/agdex_ai/ai-agent-memory-in-2026-mem0-vs-zep-vs-letta-vs-cognee-a-practical-guide-cfa. Relevant if the framework needs cross-session agent memory beyond Claude Code's own conversation history.

**Context compression / "context rot" research** — Chroma's research (https://www.trychroma.com/research/context-rot) established that LLM recall degrades non-linearly as input tokens grow (U-shaped "lost in the middle" curve) — now the standard citation for why context engineering matters. Follow-on 2026 work: "Diagnosing and Mitigating Context Rot in Long-horizon Search" (arXiv 2606.29718) and "End-to-End Context Compression at Scale" (arXiv 2606.09659) — relevant if the framework does its own context-window management on top of Claude Code/Codex rather than delegating entirely to their built-in compaction.

**Orchestration framework consolidation** — Microsoft merged AutoGen + Semantic Kernel into a unified **Microsoft Agent Framework** (Oct 2025, GA targeted end Q1 2026), adding graph-based workflows for explicit multi-agent control paths — a LangGraph-style competitor now backed by Microsoft's enterprise stack. Hugging Face's **smolagents** (Jan 2025, 27k+ stars) takes the opposite minimalist bet: agents write executable Python per step in a sandbox rather than orchestration graphs — a useful design-philosophy contrast (graph-based vs. code-execution-based) if evaluating orchestration architecture.

**GitHub Spec Kit's broader SDD trend** — by 2026, essentially every major agent tool (Claude Code, Cursor, AWS Kiro, Google Antigravity) has shipped its own spec-driven-development flavor. Worth benchmarking the framework's task-decomposition layer against this category broadly, not just the specific tools researched above.

---

## Prompt injection defense patterns

**Core mental model — the "lethal trifecta"** (Simon Willison, security researcher, June 2025): an agent is exploitable when it simultaneously has (1) access to private/sensitive data, (2) exposure to untrusted content (repo files, web pages, MCP responses), and (3) a channel to communicate externally (network calls, git push, file writes an attacker can later read). Removing any one leg neutralizes the attack even without perfect prompt-injection detection. Willison explicitly warns that vendor claims of "95% injection prevention" are a failing bar — the only reliable mitigation is architectural (never combine all three), not filtering.
Source: https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/

**Academic pattern catalog — "Design Patterns for Securing LLM Agents against Prompt Injections"** (Beurer-Kellner, Debenedetti, Tramèr, et al., June 2025, arXiv 2506.08837; covered at https://simonwillison.net/2025/Jun/13/prompt-injection-design-patterns/). Six architectural patterns directly citable for a framework design doc:
- **Action-Selector** — the LLM only picks from a fixed, predefined set of tool calls; tool outputs never feed back into the action-generation loop, so injected content can't cause new actions.
- **Plan-Then-Execute** — the agent commits to a full plan *before* seeing untrusted tool output, so injected content encountered mid-execution can't alter the plan.
- **Dual LLM** — a privileged LLM (no untrusted input) orchestrates a quarantined LLM (processes untrusted content, whose output is treated as inert data, never instructions).
- Plus Context-Minimization, Code-Then-Execute, and Map-Reduce patterns constraining what the untrusted-content-exposed LLM can influence.
Code samples: https://github.com/ReversecLabs/design-patterns-for-securing-llm-agents-code-samples
Related research: Google DeepMind's **CaMeL** — a capability/taint-tracking system so untrusted data literally cannot trigger consequential actions regardless of embedded instructions.

**Anthropic's own guidance (Claude Code Security docs, https://code.claude.com/docs/en/security)** — the most directly actionable source:
- **Permission-based architecture**: read-only by default; edits/bash/network require explicit approval (once or persistent allow rule). Three-tier config: `permissions.allow` / `permissions.ask` / `permissions.deny`.
- **Sandboxed bash tool**: OS-level filesystem + network isolation (`/sandbox`), contains blast radius even if injection succeeds.
- **Working directory boundary**: writes confined to the launch directory and subfolders; reads outside require approval.
- **Isolated context windows for WebFetch**: fetched web content is processed in a separate context window to avoid injecting instructions into the main agent loop — a directly shippable instance of the "Dual LLM" pattern above.
- **Network command approval**: `curl`/`wget` not auto-approved; can be fully denied via `permissions.deny`.
- **Context-aware anomaly detection**: a classifier flags anomalous bash even if previously allowlisted (fail-closed matching).
- **MCP trust model**: MCP servers are configured (checked into source control), not auto-discovered; Anthropic explicitly recommends writing your own MCP servers or using ones from trusted providers, and states it does *not* security-audit third-party MCP servers even in its own directory — the trust decision is pushed to the integrator.
- **Explicit "working with untrusted content" checklist**: review commands before approval, avoid piping untrusted content directly to Claude, verify changes to critical files, use VMs for scripts/tool calls touching external services.

**OpenAI Codex CLI** (https://learn.chatgpt.com/docs/agent-approvals-security) — a parallel but distinct model, useful contrast for a framework layering both:
- Dual-layer control: **sandbox mode** (what can technically execute — Seatbelt on macOS, bwrap+seccomp on Linux, restricted local user account on Windows) separated from **approval policy** (when a human is asked). Default: `workspace-write` sandbox + `on-request` approval, network off by default.
- `network_proxy` allowlist/denylist by domain when network is enabled; deny always wins; DNS-rebinding protection.
- Protected paths even inside workspace-write: `.git`, `.agents`, `.codex` stay read-only.
- Explicit written warning: "Use caution when enabling network access or web search in Codex. Prompt injection can cause the agent to fetch and follow untrusted instructions" — web search defaults to a cached/pre-indexed result set rather than live fetch specifically to shrink injection surface.

**Documented real-world failure cases — evidence this is an active, exploited surface, not theoretical:**
- CVE-2025-54794 / CVE-2025-54795 in Claude Code — path-restriction bypass and command-injection RCE via crafted whitelisted-command strings, no confirmation required, patched in v2.1.90. https://cymulate.com/blog/cve-2025-547954-54795-claude-inverseprompt/
- AGENTS.md injection in Codex CLI silently staging AWS/npm credential exfiltration with zero prompt. https://www.backslash.security/blog/openai-codex-injection-in-agents-md-exfiltrating-credentials
- Codex CLI RCE via `web.run` + Windows binary hijacking, attacker-controlled indexed webpage → persistent code execution outside the sandbox. https://cymulate.com/blog/codex-cli-rce-prompt-injection-mitigations/

**Practical pattern synthesis for the framework** (derived from the above):
1. Never grant network egress and repo-write in the same unattended step — enforce the trifecta break architecturally in the permission schema, not via prompting.
2. Tag content provenance at ingestion (repo file vs. user instruction vs. tool/MCP output) and prevent lower-trust tags from reaching the "decide next action" prompt unfiltered — Action-Selector/Dual-LLM pattern.
3. Treat AGENTS.md/CLAUDE.md/README instructions as *data*, not *directives*, unless a human explicitly promotes them — this is exactly where Claude Code and Codex CLI both currently have real, CVE'd gaps.
4. Isolate any tool that fetches external content (web, MCP) into its own context/sandbox and only pass back structured, non-instructive summaries.
5. Fail-closed on unmatched permission rules; default-deny for MCP servers not explicitly pinned in version control.

---

## Notes on data integrity for this report

Two tools researched (**Graphify**, **Caveman**) surfaced red flags worth carrying forward into any downstream deliverable built from this research:
- **Graphify**: 112k GitHub stars on a repo created ~5 months ago is statistically inconsistent with its forks/issues activity and matches documented fake-star campaign patterns (CMU/Socket/NCSU research). Do not cite its star count as an adoption/trust signal.
- **Caveman**: independently benchmarked by JetBrains at ~8.5% real token savings against a marketed claim of 65% — an 7-8x gap between claim and measured result. Its 101k-star count (also on a ~5-month-old repo) should be treated with the same skepticism as Graphify's.

By contrast, **Serena**, **Context7**, **Agent OS**, **BMAD-METHOD**, **GitHub Spec Kit**, and **OpenSpec** all showed proportionate stars:forks:issues ratios consistent with organic adoption when checked via the GitHub API directly.

---

## 2026-09-07 targeted addendum: Sentrux and newer adaptive workflows

**Sentrux** is a complementary architectural sensor, not a replacement for Ratchetry. Its
`check` command, saved baseline, post-session `gate`, and executable architecture rules
cover structural regression enforcement that Ratchetry deliberately does not implement.
That makes a future optional Tool Router/CI adapter plausible. It remains pre-1.0 and its
architecture score has not been independently validated here, so it must not be
auto-installed, default-on, or used as a trust signal. Re-evaluate after a pinned stable
release and a local false-positive/token/latency benchmark.

**specs.md** now demonstrates adaptive checkpoints, brownfield, monorepo, and Codex support.
Therefore “adaptive rigor” is a category, not a defensible exclusive claim. Ratchetry's
narrower differentiation is the combination of a repository-level explicit risk model,
persistent one-way ratchet, dual-client safety/config lifecycle, and curated memory. New
entrants do not remove that value, but they do require precise positioning.

## 2026-09-08 targeted addendum: cost and security stack

This addendum supersedes RTK section 9's “opt-in default/low-risk” conclusion.
Current stable RTK is v0.48.0. Its own documentation distinguishes Claude's
`PreToolUse` rewrite hook (`rtk init -g`) from Codex's AGENTS/RTK instruction
files (`rtk init -g --codex`), offers a dry-run, keeps telemetry opt-in, and
preserves raw failure output. Those are good controls, but the integration still
changes what evidence the agent receives. The correct classification is
**experimental until a local quality/cost comparison passes**, not a universal
default. Source: https://github.com/rtk-ai/rtk

ccusage has moved to the `ccusage/ccusage` organization and now documents local
aggregate reports across Claude Code, Codex, OpenCode, Gemini, Copilot CLI, and
other coding clients, with per-source namespaces and offline cached pricing.
Older installed releases may still expose Claude-only grammar. It is the
currently selected independently maintained measurement source, not proof of any
optimizer's savings. Ratchetry therefore invokes it explicitly, defaults
benchmark capture to offline, and stores only aggregate totals plus user-scored
task success. Source: https://github.com/ccusage/ccusage

Context Mode addresses a real but overlapping problem: keeping large tool/MCP
results out of the main context. Its current package also introduces an MCP
process, multiple tools/hooks, local storage, and a non-MIT/Apache Elastic-2.0
license. It can be tested for log/API-heavy work but does not meet the minimal
universal-core bar. Source: https://github.com/mksglu/context-mode

The old `mcp-scan` path now redirects to Snyk Agent Scan. Current operation can
require an external service/token, transmits component/Skill information for
analysis, and may execute MCP commands after consent. That can add value in an
MCP-heavy security profile, but it conflicts with “local-first by default” and
must remain explicit/on-demand after a data-flow and command-boundary review.
Source: https://github.com/snyk/agent-scan

For scanners, “install all of them” is rejected. Gitleaks is the narrow explicit
secret-scan baseline; Trivy is the first consolidated candidate for repository,
container, dependency, secret, and IaC coverage; Semgrep is a code-bearing
T2/T3 SAST profile; Checkov is IaC-only; OSV-Scanner, Syft, and Grype are
on-demand when they add findings or required artifact formats. This reduces
duplicated downloads, output, false positives, and supply-chain surface. Sources:
https://github.com/gitleaks/gitleaks · https://trivy.dev/ ·
https://semgrep.dev/docs/ · https://google.github.io/osv-scanner/ ·
https://github.com/bridgecrewio/checkov · https://github.com/anchore/syft ·
https://github.com/anchore/grype

The architectural decision is now executable in `tools.lock.json`: every
optional tool has a family, activation mode, network posture, and benchmark
policy. The aggregate `ratchery benchmark capture/compare/report` loop,
with a digest-bound six-task suite and repeated-sample quality floor,
exists precisely so future promotion is based on cost per successful task on
the user's own repository rather than these upstream claims.

## 2026-09-11 targeted addendum: AkitaOnRails repositories

The useful result of reviewing the current public profile is selective, not an
argument for importing the collection.

**ai-jail** has meaningful defense-in-depth ideas: private home, minimal inherited
environment, capability-off defaults, and project policy that cannot widen trusted
global policy by default. Its own threat model also establishes why it cannot be the
Ratchetry boundary: macOS uses deprecated `sandbox-exec`; native Windows is unsupported;
`--network` is unrestricted; agent-state mounts expose authentication to every process
inside; Docker access is host-root-equivalent; and hostile workloads still require a
disposable VM. Verdict: manual, platform-specific experiment around (never instead of)
native Claude/Codex sandboxing. GPL-3.0-only code is not vendored or linked.
Source: https://github.com/akitaonrails/ai-jail

**ai-memory** solves a real scenario Ratchetry's curated local Vault does not fully solve:
shared cross-agent, cross-machine, multi-user handoffs with attribution/audit. It also
adds a long-running service, database, hooks, MCP surface, authentication, optional
providers, automatic prompt/tool capture, and raw sanitized managed-workstream segments.
Those are deliberate product choices, not free memory. Verdict: experimental **one-of**
backend for teams that demonstrate this need, starting loopback-only/zero-LLM with an
explicit capture/retention policy and an A/B comparison against curated Vault retrieval;
never stack both by default. Source: https://github.com/akitaonrails/ai-memory

**Greenlight (lucasrosati)** was considered as a design input for explicit
cross-agent continuation. Its useful transferable idea is a small handoff with
objective, completed work, revision/provenance, open risk, and one next action.
Ratchetry independently implements only that data boundary in its existing
curated Vault. A task queue, PR runner, remote approvals, and agent orchestration
would require broader repository/network permissions and add operational and
context cost, so they are outside v1. The upstream repository could not be
retrieved during the 2026-09-12 re-check; no source code, runtime dependency, or
unverified product behavior was copied or relied upon.
Reference supplied for the review: https://github.com/lucasrosati/greenlight

**llm-coding-benchmark** is useful as methodology, not a dependency. Its fixed tasks,
quality rubric, normalized results, and cost capture reinforce repeated controlled trials;
its own reported sensitivity to harness prompts/plugins reinforces recording configuration
identity. Ratchetry adopted the independent idea of an automatic bounded configuration
digest rather than importing its Rails/OpenCode-specific runner.
Source: https://github.com/akitaonrails/llm-coding-benchmark

**my-skills** contributed three independently reimplemented review ideas: evidence paths
and verification budgets in planning, threat-model/adversarial/residual-scope structure in
security review, and installation of the exact release artifact before publication. The
personal Skill pack is not installed or copied; it overlaps Ratchetry's smaller existing
Skills and would increase instruction/maintenance surface.
Source: https://github.com/akitaonrails/my-skills

**homebrew-tap** is a useful release-distribution reference only after Ratchetry's final
name, owner/repository, command namespace, and first verified release exist. The current
installer couples runtime placement to user-specific Vault onboarding, which a formula
must not perform inside Homebrew's install boundary. `docs/PUBLISHING.md` records the
required split and later formula tests. Source: https://github.com/akitaonrails/homebrew-tap

`ai-usagebar`, `codemap`, FrankMD, and unrelated framework/application repositories do
not clear the marginal-value bar: they duplicate existing observability, architecture,
or Obsidian capabilities without solving a current Ratchetry gap. No Rust rewrite follows
from these repositories; Rust remains appropriate for an isolated future daemon/sandbox/
high-throughput component only if profiling and product requirements justify one.
