# Publishing and Release Verification

This document separates controls committed in the repository from settings
that a maintainer must enable on GitHub. A green workflow is not evidence that
the repository settings below exist.

## What a release publishes

Pushing a version tag runs `.github/workflows/release.yml`. The build job has
read-only repository access and produces:

- `<name>-<version>.tar.gz` — deterministic source archive built from exactly
  the files and modes recorded by `MANIFEST.json`;
- `<name>-<version>.spdx.json` — SPDX 2.3 SBOM for the archive and its files;
- `MANIFEST.json` — per-source-file sizes and SHA-256 values; and
- `SHA256SUMS.txt` — SHA-256 values for the three artifacts above.

Before upload, the read-only build job safely extracts the exact archive into a
temporary HOME/config/state, installs it with external tools disabled,
initializes a Git fixture, and requires the installed `doctor --json` to report
no errors. It then uploads exactly those four files. A separate attestation job
downloads them without checking out or
executing repository code; only that isolated job receives OIDC and
attestation permissions and creates GitHub/Sigstore SLSA build provenance plus
the SBOM attestation. After attestations pass, a third job receives only
`contents: write`, downloads the same four files, and creates the GitHub
Release.

The SBOM intentionally lists no third-party runtime packages: Ratchetry's core
is Python standard-library-only. SHA-1 file values exist only to implement the
SPDX 2.3 package-verification-code algorithm; SHA-256 remains the integrity
check used for release artifacts.

## Verify a downloaded release

Download all four assets into one directory, then verify their bytes:

```bash
sha256sum -c SHA256SUMS.txt       # Linux
shasum -a 256 -c SHA256SUMS.txt  # macOS
```

Verify that GitHub attested the archive from this repository's release
workflow:

```bash
gh attestation verify ratchery-X.Y.Z.tar.gz --repo brunoribeirol/ratchery
```

Inspect before extraction:

```bash
tar -tzf ratchery-X.Y.Z.tar.gz
```

The archive contains one top-level `ratchery-X.Y.Z/` directory, regular files
only, normalized ownership/timestamps, and no `.git` or `.github` directory.
The installer revalidates the manifest and stages only its verified file
snapshots, so a dirty checkout's `.git`, ignored state, build output, and
untracked files are not copied into the installed runtime.

## Rebuild locally

From the exact release tag:

```bash
python3 scripts/verify-manifest.py
SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)" \
  python3 scripts/build-release.py --repository brunoribeirol/ratchery
```

Rebuilding the same tree with the same epoch produces byte-identical files.
The unit suite proves this in two independent output directories and validates
the archive inventory, SPDX relationships/checksums, and unsafe-input
rejections.

Exercise the same artifact-install boundary locally without touching real user
configuration:

```bash
make release-smoke
```

## Maintainer release procedure

1. Inspect the repository visibility and actual hosted-feature availability
   before creating a tag. On GitHub Free, Pro, or Team, artifact attestations
   require a public repository; private attestations require Enterprise Cloud.
   Never push a private tag that the mandatory attestation job cannot process.
2. Add a dated `CHANGELOG.md` entry and bump `VERSION` in
   `lib/agent_workspace.py`; the installer derives the same version through
   the validated manifest.
3. Stage every intended release change using explicit paths, including new
   files, then run `python3 scripts/gen-manifest.py` last. The generator refuses
   untracked or partially staged release candidates instead of guessing what
   should ship. Review and stage the resulting `MANIFEST.json` with the release
   changes.
4. Run `make test` and `make release-smoke` (including the Action-pin and exact
   artifact-install gates), manually dispatch the
   credential-free client compatibility canary, and confirm its source-free
   preparation job plus every minimum/current Claude/Codex leg passes without
   inference. The client jobs must install packages before downloading the
   generated fixture; only Claude's required native-binary lifecycle step may
   run. Do not use `claude doctor` as canary evidence: require separate,
   closed-stdin, time-bounded version and pending-MCP parsing steps.
   For optional example dependencies, treat a newer upstream release as an
   advisory: retain the reviewed exact pins unless compatibility or a known
   vulnerability justifies change, but require isolated install/import checks
   and a vulnerability audit before release.
5. Build once locally with the command above and inspect all four outputs.
6. Merge through the protected `main` branch. For the first release on a plan
   without private Rulesets, validate the final private commit first, then use
   the ordered public-launch procedure below before tagging.
7. Create a new signed annotated tag:
   `git tag -s vX.Y.Z -m "vX.Y.Z" <commit>`, then push it. Never move,
   replace, or reuse a published tag.
8. Confirm the Release contains all four assets and both attestations verify.

## Homebrew tap after first publication

Do not create a formula before the first Ratchetry artifact is verified. A
package-manager install also cannot run the current interactive/user-specific
`install.sh`, because Homebrew formulae must not configure a maintainer's Vault
or write agent files into the build user's home. After the final identity and
first verified release exist:

1. Freeze the public command and installed runtime namespace, then provide a
   supported post-install setup command for the user's Vault/projects paths.
2. Create `<final-owner>/homebrew-tap`; keep the formula small and install the
   release archive into `libexec`, exposing only the stable command from `bin`.
3. Pin the formula URL to an immutable `vX.Y.Z` asset and copy its SHA-256 from
   the verified `SHA256SUMS.txt`; never use a moving `latest` URL.
4. Make `brew test` run the installed command from the bottle and a temporary,
   isolated setup/doctor smoke without network or real home configuration.
5. Run `brew audit --strict --online`, `brew style`, and install tests on
   supported macOS and Linux runners before documenting the tap in README.
6. Automate formula bumps only after the signed tag, archive smoke,
   attestations, and GitHub Release all succeed; use a narrowly scoped token for
   the tap repository.

Until those gates pass, the release archive plus checksum/attestation path is
the supported distribution mechanism.

## GitHub settings checklist for private staging and public launch

These settings do not travel with a clean-history copy. Configure and verify
them after the private `brunoribeirol/ratchery` repository exists. Changing
visibility, tagging `v1.0.0-rc.1`, and publishing stable `v1.0.0` are three
separate maintainer decisions.

### Capability preflight

Record actual availability before changing settings or pushing a tag; do not
infer it from a green local test:

- Artifact attestations work for public repositories on current GitHub plans,
  but private/internal repositories require Enterprise Cloud. If unavailable
  privately, stop private staging at a validated commit and tag only after a
  separately approved public launch.
- Rulesets work for public repositories on GitHub Free and for private
  repositories on Pro, Team, or Enterprise Cloud. If unavailable privately,
  prepare the intended rules and activate them immediately after the visibility
  change, before tagging or announcing the repository.
- SARIF upload works for public repositories. Private/internal use requires an
  eligible organization repository with GitHub Code Security enabled. The
  OpenSSF Scorecard Action separately limits private-repository support to
  GitHub Advanced Security and recommends additional read scopes for private
  repository metadata. Ratchetry therefore skips Scorecard while private and
  runs its single analysis job only after public visibility.
- Private vulnerability reporting is a public-repository intake feature. Enable
  it during the public-launch transaction, not while the repository is private.

Do not buy a higher GitHub plan solely to make the staging order match this
guide. The fail-closed public sequence below preserves attestations without
adding recurring infrastructure cost.

### Repository basics

- [ ] Set `main` as the default branch. Enable Issues immediately; enable
  Discussions when the repository is made public and there is a moderation
  plan.
- [ ] Add a concise description, homepage if one exists, and discovery topics
  such as `claude-code`, `codex`, `ai-agents`, `obsidian`, `developer-tools`,
  and `security`.
- [ ] Upload a 1280x640 social-preview image only after the final name and
  visual identity are settled.
- [ ] Keep `FUNDING.yml` absent until a real funding destination exists.
- [ ] Keep `CITATION.cff` absent unless users actually need an academic/research
  citation; it is not a generic maturity badge for a CLI.

### `main` branch ruleset

- [ ] Create an **active GitHub Ruleset** targeting the default branch, not
  only a legacy branch-protection rule. Do this privately when the plan permits;
  otherwise make it the first control applied after public visibility.
- [ ] Require a pull request, all six `test (<os>, py<version>)` matrix checks,
  the branch to be up to date, and conversation resolution.
- [ ] Block force pushes and deletion and require verified signed commits.
- [ ] With only one maintainer, require zero approving reviews for now rather
  than creating an impossible governance claim. Raise this to one only after a
  real second maintainer exists.
- [ ] Give no routine bypass. Keep an emergency maintainer bypass narrowly
  scoped and visible in the ruleset if account recovery requires one.

Required signing has contributor cost. `CONTRIBUTING.md` therefore calls it
out explicitly; test a PR from a fork and a Dependabot PR before launch so the
chosen GitHub merge method does not strand unsigned commits.

### Release-tag rulesets

- [ ] Protect `v*`, privately when the plan permits or immediately after public
  visibility otherwise. Use a creation ruleset whose only bypass actor is the
  maintainer/release identity, plus a no-bypass immutability ruleset that blocks
  updates, deletions, and force pushes. Keeping these separate prevents the
  creator's necessary bypass from also bypassing immutability.
- [ ] Require signed commits for tagged revisions. GitHub's ruleset does not
  replace verification of an annotated tag's own signature, so keep tag
  creation restricted and verify that signature as a manual release gate.

### Actions and security features

- [ ] Set the default `GITHUB_TOKEN` permission to read-only and allow write
  only where a job declares it explicitly.
- [ ] Allow only GitHub-owned actions plus the pinned OpenSSF Scorecard action;
  keep every `uses:` reference pinned to a full commit SHA and review
  Dependabot's proposed SHA changes.
- [ ] Enable dependency graph and Dependabot alerts/security updates privately.
  Enable secret scanning, push protection, code scanning/SARIF upload, and
  private vulnerability reporting as soon as the repository visibility/plan
  supports each feature. Record unavailable controls as deferred, not enabled.
- [ ] Run the Scorecard workflow once and verify its badge points at the final
  owner/repository. While private, its only job is visibility-gated off: do not
  add GitHub Advanced Security, a PAT, or broader read scopes solely to run this
  prerelease gate. After public launch, the job receives `id-token: write` and
  `security-events: write`; add a badge only after it publishes a real result.
- [ ] Run the client compatibility canary once; it should have no API secrets,
  model inference, or MCP connection and should pass the preparation job plus
  all minimum/current legs. Do not replace the Codex parser/profile check with
  nested `bwrap` execution on a GitHub-hosted runner.
- [ ] After the signed tag is pushed, confirm artifact attestations are visible
  and `gh attestation verify` succeeds for the first release archive. A failed
  attestation must block publication; do not bypass the `attest` job.

### Private ready-for-public checkpoint

Before requesting a visibility change:

- [ ] Final `main` commit is signed, pushed over HTTPS, manifest-valid, and the
  worktree is clean.
- [ ] All six CI matrix checks, the source-free canary preparation job, and all
  four credential-free client-canary legs pass for that exact commit.
- [ ] Scorecard is recorded as deferred until public launch, and the private
  workflow contains no runnable analysis job.
- [ ] Repository metadata, read-only default `GITHUB_TOKEN`, allowed Actions,
  dependency graph, and Dependabot settings are verified.
- [ ] Plan-supported private Rulesets/security features are active. Every
  unavailable control is recorded with the public step that will enable it.
- [ ] Local installation and Vault diagnostics pass against the same candidate.
- [ ] No `v*` tag or GitHub Release exists unless private attestations were
  positively verified as supported.

### Ordered public-launch transaction

This section still requires a separate explicit maintainer approval. For a plan
without private attestations, execute in order:

1. Reconfirm the private ready-for-public checkpoint and exact commit SHA.
2. Change visibility to public; do not announce it yet.
3. Immediately create/verify the `main` and `v*` Rulesets and enable public
   secret scanning, push protection, code scanning, and private vulnerability
   reporting.
4. Run the public Scorecard job and verify SARIF upload and published results.
5. Create and locally verify the signed annotated `v1.0.0-rc.1` tag, then push
   it once.
6. Require the release workflow, all four assets, checksums, archive smoke, and
   both attestations to pass. Verify the downloaded archive with
   `gh attestation verify`.
7. Re-run unauthenticated links/install/security-contact checks. Only then
   announce the repository. Stable `v1.0.0` remains a later decision.

### Trust signals that require real evidence

- [ ] Apply for the OpenSSF Best Practices **Passing** badge after the public
  URLs, release, contribution process, security channel, tests, and repository
  settings are live. Answer criteria literally; do not display the badge while
  an application is incomplete or self-claims have not been checked.
- [ ] Re-run the public README links, clean-clone installation, CI Action,
  license/provenance checks, and security contact from an unauthenticated
  account before announcement.

Official references: [GitHub artifact-attestation availability](https://docs.github.com/en/enterprise-cloud@latest/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations),
[Ruleset availability](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets),
[SARIF/code-scanning availability](https://docs.github.com/en/code-security/how-tos/scan-code-for-vulnerabilities/integrate-with-existing-tools/uploading-a-sarif-file-to-github),
[OpenSSF Scorecard Action private-repository requirements](https://github.com/ossf/scorecard-action#additional-permissions-for-private-repositories),
[private vulnerability reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/report-privately),
[ruleset rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets),
and [social preview guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview).
