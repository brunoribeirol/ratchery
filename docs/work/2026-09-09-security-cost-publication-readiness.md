# Work Plan: Security, Cost, and Publication Readiness

## Objective

Finish the smallest defensible pre-publication scope for Ratchetry: integrate the
current setup-first/cost-security work in reviewable commits, harden the remaining
Claude and MCP escape surfaces, turn benchmark labels into a reproducible task-set
contract, add local read-only budget warnings, continuously check the generated
configuration against real supported clients, and bring public documentation into
agreement with the resulting behavior.

## Non-goals

- Do not add another default agent, Skill, MCP server, scanner, memory system, graph
  engine, output optimizer, or runtime dependency.
- Do not auto-install third-party software, start paid agent runs, or spend model
  tokens on the user's behalf.
- Do not make Sentrux, RTK, Serena, QMD, Context Mode, or Graphify default-on.
- Do not implement a daemon or a prompt-blocking budget hook before the accuracy and
  failure behavior of read-only warnings are measured.
- Do not rename the product, CLI, config/state directories, release artifacts, or
  frozen `agent-workspace:v8` merge-format markers until the final public name and
  compatibility policy are explicitly settled.
- Do not create a remote repository, change GitHub settings, publish a release, push,
  or tag without explicit authorization and a confirmed destination.

## Evidence and assumptions

- The current `main` worktree contains a large unstaged transformation spanning the
  adaptive engine, security runtime, cost evidence, release supply chain, tests, and
  documentation. It must be reviewed and integrated before unrelated feature work is
  layered on top.
- A clean-clone validation of the intended current inventory has passed previously,
  but the final committed inventory and manifest must be validated again after commit
  boundaries and all new work are complete.
- `benchmark capture/compare` safely stores aggregate-only ccusage evidence, but the
  documented `core-suite-v1` has no canonical task definitions, fixtures, verifier,
  or sampling rule. It is currently only a user-supplied label.
- Claude's current permission contract supports disabling bypass mode. Codex's current
  MCP contract supports tool allowlists, approval modes, timeouts, and per-tool output
  token limits. Ratchetry's generated profiles do not yet consume all of those controls.
- The Serena MCP command is fixed to a release tag, not an immutable full commit SHA.
- The normal CI validates Ratchetry's parsers and generated text, but does not run a
  compatibility canary against both the minimum-supported and current Claude/Codex
  clients.
- Fifteen global Skills remain a reasonable progressive-disclosure inventory; adding
  more capability is not required to complete this phase.

## Affected contracts and files

- Current transformation: the existing modified/untracked files shown by `git status`.
- Security/MCP: `assets/project/.claude/settings.json`,
  `lib/agent_workspace.py`, `tests/test_doctor_tier_json.py`, integration tests, and
  the canonical security/MCP user and developer documentation.
- Benchmark task sets: a new small versioned `benchmarks/` contract, benchmark CLI
  dispatch/validation, `lib/efficiency.py`, focused tests, and benchmark documentation.
- Budget warnings: `lib/agent_workspace.py`, `lib/efficiency.py`, focused tests, and
  user documentation. The data boundary remains aggregate-only and offline by default.
- Client compatibility: a separate scheduled/manual GitHub workflow and its contract
  tests/documentation; it must not make the normal low-cost CI depend on changing
  third-party clients.
- Release/publication: `README.md`, `CHANGELOG.md`, `SECURITY.md`, `CONTRIBUTING.md`,
  `docs/PUBLISHING.md`, other canonical guides, action/release metadata, links, and
  `MANIFEST.json` after the final name/repository decision.

## Risks

- Splitting the already-large worktree mechanically can create invalid intermediate
  commits. Each commit must be coherent and pass the checks relevant to its own
  contract; temporary-index techniques must never overwrite the user's real index.
- MCP tool names and behavior are upstream contracts. A stale allowlist can remove a
  needed capability; a broad allowlist can preserve the attack/context surface this
  phase is intended to reduce.
- An immutable package commit reduces replacement risk but does not establish upstream
  trust by itself. Installation remains explicit and reviewable.
- A benchmark runner can create the misleading appearance of scientific evidence.
  Task success, repeated trials, identical provenance, quality floors, and sample size
  must remain visible; a single cheaper session cannot produce `KEEP`.
- Native client checks can add network, latency, and upstream flakiness. Keep them
  scheduled/manual and credential-free rather than on every pull request.
- Cost thresholds are estimates, not billing controls. Read-only warnings must never
  claim to be authoritative invoices or universal pre-spend enforcement.
- Rebranding before the compatibility policy is decided can break installed commands,
  managed markers, upgrade paths, release verification examples, and existing users.

## Workstreams and ownership

The primary agent owns integration and final decisions. Read-only security review and
test review may be isolated after each implementation phase when that improves signal.

1. **Integrate the current transformation**
   - Audit the complete unstaged diff and classify files into coherent existing changes.
   - Regenerate the manifest only after each intended inventory is known.
   - Validate before committing; do not push.
2. **Security and MCP hardening**
   - Disable Claude bypass mode in the generated baseline and enforce it in `doctor`.
   - Pin executable MCP sources immutably.
   - Add minimum MCP tool exposure, prompt-oriented approvals, bounded output, and
     timeouts where the client supports them.
   - Preserve explicit opt-in, dual-client reversibility, and user-owned definitions.
3. **Reproducible cost evidence**
   - Define `core-suite-v1` tasks, fixtures, success criteria, and protocol.
   - Validate task-set identity and repeated compatible samples.
   - Report distribution/quality evidence without automatically starting paid agents.
4. **Budget warnings**
   - Add offline aggregate daily/session/spike checks with human and JSON output.
   - Keep enforcement opt-in and document native Claude print-mode hard limits.
5. **Client compatibility canary**
   - Validate generated Claude/Codex configuration in a credential-free ephemeral
     environment against supported minimum and current stable clients.
   - Run scheduled/manually, not in the normal pull-request matrix.
6. **Documentation and publication readiness**
   - Reconcile every public claim, example, version floor, command, and trust boundary.
   - Remove obsolete internal-history material that does not earn a place in the clean
     public repository while preserving real contributor-facing rationale.
   - Apply the final name/repository/compatibility decision once, then regenerate and
     re-run the full release verification.

## Acceptance criteria

- The pre-existing transformation is represented by coherent, reviewable commits with
  no user-owned staging overwritten and no push performed.
- Claude's generated policy disables permission bypass and `doctor` detects removal.
- Every Ratchetry-managed executable MCP source is immutable; enabled MCP profiles expose
  only the intended tools with explicit approval/output/timeout policy where supported.
- `core-suite-v1` has versioned tasks and success criteria; incompatible task sets or
  provenance cannot be compared, and one sample cannot be promoted as universal proof.
- Budget checks operate offline on aggregate values, expose JSON, persist no raw usage,
  and do not block unless the user explicitly requests an enforcement exit code.
- Scheduled/manual compatibility checks exercise both clients without credentials or
  paid inference and do not burden normal pull requests.
- README, security, architecture, benchmarking, user/developer, contribution, release,
  roadmap, changelog, action, and generated-template documentation agree with code.
- No unexplained `v8.2`/`v9`, old repository URL, old product name, placeholder contact,
  or invalid install/release command remains in the intended public inventory. Frozen
  merge-format markers and clearly necessary migration compatibility remain documented.
- Full tests, lint, integration, manifest, action-pin, Markdown-link, release
  reproducibility, checksum, and diff-whitespace checks pass from a clean checkout.

## Validation plan

Run focused tests after each phase, then from the final clean checkout:

```bash
python3 -m unittest tests.test_doctor_tier_json tests.test_efficiency
bash tests/run-tests.sh
ruff check lib/ scripts/ tests/ bin/
python3 scripts/gen-manifest.py
make test
python3 scripts/verify-manifest.py
python3 scripts/verify-action-pins.py
python3 scripts/verify-doc-links.py
git diff --check
```

Build the release twice with the same `SOURCE_DATE_EPOCH`, compare bytes, verify
`SHA256SUMS.txt`, inspect the archive inventory, and run the credential-free native
client canary separately. Paid benchmark trials happen only after the user supplies an
explicit maximum spend and approves the selected model/client matrix.

## Handoff

Status: implementation and clean-checkout validation complete. The user
authorized local commits after review, but this environment denied every write
to `.git/index.lock` even after explicit escalation; the worktree and a verified
258-file manifest are ready for the maintainer to stage/commit. No external
download, paid inference, remote repository mutation, tag, push, or publication
is authorized merely by this plan.

Final local evidence (2026-09-11): clean `doctor --deep` at T1 with zero
errors/warnings; complete `make test` with 260 unit tests; standalone 260-test
runs on Python 3.11, 3.12, and 3.14; Ruff 0.6.2; 258-file manifest; 15 pinned
Action references; 159 Markdown files checked; two byte-identical releases;
checksums/SPDX verified; and `make test` passing from the extracted archive
with seven expected workflow-only skips. A second requested independent
code/security pass failed solely because the reviewer agents hit their service
quota; the earlier completed independent reviews and their fixes remain
recorded in the implementation/tests.

User decisions required before the publication phase:

1. Final public product name and whether `ratchery` remains the stable CLI and
   installed-directory namespace for compatibility.
2. Final GitHub owner/repository destination.
3. Maximum approved spend and model/client matrix for real A/B benchmark runs.
4. Confirmation that GitHub private vulnerability reporting is the intended sole
   security contact, or provision of another real disclosure channel.
5. Choice and availability of a signing method for release commits and annotated tags.

Everything before those gates can be implemented, tested, documented, and committed
locally without the user downloading files or granting network access.
