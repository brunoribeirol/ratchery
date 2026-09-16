# Work Plan: Stable, Homebrew, and OpenSSF readiness

## Objective

Re-derive whether the public `v1.0.0-rc.1` release is healthy enough to begin
stable-release preparation, and separately determine the smallest defensible
paths to a Homebrew tap and an OpenSSF Best Practices badge.

## Non-goals

- Do not create or push `v1.0.0`, move/reuse `v1.0.0-rc.1`, or publish another
  GitHub Release during this audit.
- Do not create a tap repository, Formula, badge application, or new external
  account without a separately reviewed implementation and explicit approval.
- Do not weaken Rulesets, signatures, provenance, checksums, sandboxing, or
  secret-scanning controls to make a gate pass.
- Do not upgrade dependencies merely because a newer version exists.

## Evidence and assumptions

- The recovery record reports a public protected repository, signed immutable
  RC1 tag, four byte-reproduced assets, verified checksums, SPDX SBOM, and two
  verified GitHub attestations.
- Repository code, tests, manifests, release metadata, and GitHub API evidence
  are authoritative; local Vault notes are continuity evidence only.
- The core is Python-stdlib-only. Optional examples, Actions, client-canary npm
  packages, and a future Formula remain separate supply-chain surfaces.
- Current Homebrew and OpenSSF requirements must be checked against official
  upstream guidance rather than inferred from existing repository prose.

## Affected contracts and files

- `README.md`, `CHANGELOG.md`, `VERSION` ownership in `lib/agent_workspace.py`
- `docs/PUBLISHING.md`, `docs/INSTALLATION.md`, `SECURITY.md`, `LICENSE`
- `.github/workflows/{ci,release,scorecard,client-canary}.yml`, Rulesets, and
  public repository security settings
- `MANIFEST.json`, `scripts/build-release.py`, release smoke/contract tests
- `install.sh`, `bin/ratchery`, and isolated consumer installation behavior
- Example dependency manifests and pinned third-party Actions
- A future `homebrew-tap` repository and OpenSSF Best Practices application

## Risks

- Promoting an RC without an anonymous consumer-path test can publish a release
  that works only in the maintainer environment.
- A stable tag is immutable; incorrect version/changelog or non-reproducible
  artifacts cannot be repaired in place.
- Homebrew cannot safely run the current user-specific interactive installer in
  a Formula build, and a premature tap would create an unsupported install path.
- Badge criteria are self-certified trust claims; checking boxes without public
  evidence would overstate project maturity.
- External scanners and registries can be unavailable or noisy. Scanner output
  is evidence to confirm, not an automatic release decision.

## Workstreams and ownership

1. Reconcile local Git/release metadata with the public RC1 and repository
   controls.
2. Run local full gates, release reproducibility checks, secret scanning, and a
   bounded dependency/supply-chain audit.
3. Exercise a clean, isolated public-consumer install and documented first-use
   path without touching the maintainer Vault or home configuration.
4. Compare current stable-release, Homebrew tap, and OpenSSF Best Practices
   requirements against the repository's actual capabilities and evidence.
5. Produce a ranked go/no-go report. Any implementation, external publication,
   or stable tag remains a separate reviewed phase owned by the primary agent.

## Acceptance criteria

- Local `main` is clean, matches the public protected default branch, and all
  intended release files match the manifest.
- The signed RC1 tag and GitHub Release identity agree; the four public assets
  match their checksum file and both attestations verify.
- Full repository tests, action-pin verification, Markdown links, manifest,
  release smoke, and a second deterministic release build pass.
- No confirmed secret, unsafe release permission, vulnerable direct dependency,
  or unreviewed install-script/network surface blocks stable promotion.
- A fresh temporary clone/install/init/doctor flow succeeds from only public
  documentation and leaves the real home, Vault, and projects untouched.
- Stable-release work has an exact minimal change set and retains PR, GPG tag,
  provenance, SBOM, and immutable-release controls.
- Homebrew is either shown ready with an isolated post-install setup contract or
  explicitly blocked with the missing contract and test named.
- Each OpenSSF badge criterion proposed as met has a public evidence URL; unmet
  or inapplicable criteria are reported literally rather than inferred.

## Validation plan

Start with read-only metadata and focused contract tests. Then run the existing
full local gates and release rebuild. Run installed scanners only when present;
use native fallback scans and record unavailable tools. Networked package,
GitHub, Homebrew, and badge checks are bounded to official sources and stop on
connectivity/authentication failure without substituting guesses. No external
mutation occurs in this phase.

## Handoff

Return one of three outcomes for each track: `GO`, `FIX BEFORE GO`, or `DEFER`.
Stable publication, tap creation, and badge submission each require their own
explicit approval after this evidence is reviewed.

## Audit results

### Stable: FIX BEFORE GO

The runtime and release machinery are healthy, but the stable-preparation PR
must close three public-contract gaps before changing the version:

1. `README.md` does not display the public OpenSSF Scorecard badge even though
   `CHANGELOG.md` and the completed delta spec say it does. The public Scorecard
   run is recorded as successful, so restore the badge only after rechecking its
   final URL.
2. `docs/CI_GATE.md` tells consumers to use
   `brunoribeirol/ratchery@v1`, but no such ref exists. A moving major-version
   ref would also conflict with the repository's immutable-tag policy. Publish
   and document the exact immutable `@v1.0.0` ref instead.
3. ShellCheck remains explicitly informational with `continue-on-error: true`
   and a comment saying its output has never been triaged. Review the hosted
   result, fix confirmed findings, and either make a bounded ShellCheck job
   blocking or document why Bash syntax/integration coverage is the chosen
   stable contract.

The stable PR must then bump the runtime version to `1.0.0`, add a dated
changelog entry, update release/security wording, regenerate `MANIFEST.json`,
and run the full protected-PR/release/canary gates. The RC tag must not move.

### Homebrew: FIX BEFORE GO

The archive is suitable for installation under a Formula `libexec`, but the
supported post-install onboarding contract required by `docs/PUBLISHING.md`
does not exist as one user-facing command. `install.sh` cannot run in a Formula
build because it writes user-specific Vault/global state, while the CLI exposes
only the lower-level `global-config`, `install-global`, and `vault-install`
steps. Add and test one idempotent setup command before publishing a tap. The
future Formula must also bind the supported Homebrew Python runtime, expose only
`ratchery`, and test setup/doctor under isolated HOME/XDG paths without network.

### OpenSSF Best Practices: GO TO APPLICATION PREP

The public repository has the expected evidence classes: OSI license, public
version control and issue process, contribution and conduct policies, named
maintainer, private vulnerability intake, automated cross-platform tests,
versioned releases, release notes, Scorecard, secret scanning, protected main,
signed immutable tags, SBOM, checksums, and provenance. The Best Practices
questionnaire is a separate self-certification program from Scorecard; prepare
an evidence map and have the maintainer authenticate and attest each answer.
Do not add its badge until the application reports Passing.

Official guidance was refreshed on 2026-09-16. Homebrew still requires a
stable tagged release, immutable URL/checksum, meaningful `test do`, and its
strict online audit for a new Formula. The current OSPS Baseline is
`v2026.08.28`; a new application must use the version shown by the live service.

## Validation evidence

- Clean local clone at `7a7358cbcba03c3079005476caf1f178f0a27811`.
- `make test`: 322 unit tests plus Bash integration passed; Ruff 0.6.2,
  compilation, shell syntax, manifest, Action pins, and Markdown links passed.
- `make release-smoke` passed; two explicit builds produced byte-identical
  archive, SPDX SBOM, manifest, and checksum files.
- Literal README dry-run/install/doctor/Vault/tool-status flow passed in an
  isolated HOME with no Claude, Codex, QMD, or optional tools available.
- High-confidence tracked secret patterns, personal absolute paths, and embedded
  workflow/session URLs produced no findings. Hook and sandbox assets are
  unchanged from the signed RC tag.
- Recovery evidence records the four public RC assets, checksums, attestations,
  Rulesets, read-only default workflow token, secret scanning, push protection,
  private vulnerability reporting, and public Scorecard as verified.
- Core runtime dependency inventory is empty. The only Python dependency file is
  the exact-pinned FastAPI/Uvicorn example. Its prerelease install and
  `pip-audit` passed in the maintainer gate; this run could not repeat the
  networked audit because DNS was unavailable. Gitleaks, Trivy, Semgrep,
  OSV-Scanner, Syft, Grype, Actionlint, and ShellCheck were not installed
  locally; those unavailable tools are residual checks, not claimed passes.

## Implementation outcome — 2026-09-16

### Stable: GO TO PROTECTED PR

The three identified public-contract gaps are fixed. The candidate adds a
least-privilege CodeQL workflow, makes ShellCheck blocking inside the existing
Linux matrix checks, documents the exact immutable `@v1.0.0` Action ref, and
restores only the already-earned Scorecard badge. Runtime and changelog metadata
are now `1.0.0`; the RC tag remains untouched.

The final clean validation copy passed 342 unit tests, the Bash integration
suite, Ruff, Python/Bash syntax, a 285-file generated release manifest, 20
immutable Action pins, 178 Markdown-link checks, installed-archive onboarding,
and release smoke. Two independent builds produced byte-identical archives,
SPDX SBOMs, manifests, and checksum files. Hosted CodeQL and the blocking Linux
ShellCheck execution remain deliberately unclaimed until the protected PR runs.

### Homebrew: GO AFTER VERIFIED STABLE

`ratchery setup` now provides the missing idempotent package-manager onboarding
boundary with dry-run, explicit confirmation, isolated HOME/XDG tests, and
fail-closed checks for symlinked/special managed targets. The release smoke test
executes that installed command and `doctor-global`. Create the tap and Formula
only after the stable GitHub artifact exists, so its URL and SHA-256 are real.

### OpenSSF Best Practices: GO TO HUMAN APPLICATION AFTER STABLE

`docs/OPENSSF.md` now maps public evidence without claiming an unearned badge.
The maintainer must authenticate and answer the current questionnaire; no
automation can truthfully attest the human/process criteria on their behalf.
