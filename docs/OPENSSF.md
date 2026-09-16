# OpenSSF evidence and application boundary

Status: **preparation only**. Ratchetry publishes an automated OpenSSF
Scorecard result, but it has not yet earned or displayed an OpenSSF Best
Practices badge.

These are separate programs:

- [Scorecard](https://scorecard.dev/viewer/?uri=github.com/brunoribeirol/ratchery)
  automatically evaluates repository practices. Its published result is the
  only OpenSSF badge currently displayed in README.
- [Best Practices](https://www.bestpractices.dev/en/criteria/0) is a public,
  mostly self-certified questionnaire. The current service supports both its
  metal series (Passing/Silver/Gold) and the OSPS Baseline series.

For this single-maintainer v1 project, the honest initial targets are the metal
**Passing** level and **OSPS Baseline Level 1**. Silver, Gold, and Baseline Level
2+ include maturity or multi-maintainer expectations that Ratchetry must not
claim yet.

The current OSPS Baseline at preparation time is
[`v2026.08.28`](https://baseline.openssf.org/). Record the exact version shown
by the application when answers are submitted; do not silently carry an older
questionnaire forward.

## Public evidence map

Use the URLs below as evidence while completing the application. They are an
index, not pre-filled answers; the maintainer must read each current criterion
and choose Met, Unmet, Unknown, or N/A with a literal justification.

| Evidence area | Public evidence | What it establishes |
|---|---|---|
| Purpose and acquisition | [README](https://github.com/brunoribeirol/ratchery#readme), [Installation](https://github.com/brunoribeirol/ratchery/blob/main/docs/INSTALLATION.md) | Problem, audience, supported install/setup boundary, first commands |
| Feedback and contributions | [Issues](https://github.com/brunoribeirol/ratchery/issues), [CONTRIBUTING](https://github.com/brunoribeirol/ratchery/blob/main/CONTRIBUTING.md), [Code of Conduct](https://github.com/brunoribeirol/ratchery/blob/main/CODE_OF_CONDUCT.md) | Public issue tracker, PR workflow, acceptable-change and conduct rules |
| License | [MIT LICENSE](https://github.com/brunoribeirol/ratchery/blob/main/LICENSE) | Standard-location OSI-approved FLOSS license |
| User/interface documentation | [Start Here](https://github.com/brunoribeirol/ratchery/blob/main/docs/00-START-HERE.md), [User Guide](https://github.com/brunoribeirol/ratchery/blob/main/docs/USER-GUIDE.md), [Commands](https://github.com/brunoribeirol/ratchery/blob/main/docs/COMMANDS.md) | Basic operation and external CLI contracts |
| Version/change control | [Commits](https://github.com/brunoribeirol/ratchery/commits/main), [tags](https://github.com/brunoribeirol/ratchery/tags), [CHANGELOG](https://github.com/brunoribeirol/ratchery/blob/main/CHANGELOG.md) | Public Git history, unique SemVer releases, human release notes |
| Security reporting | [SECURITY](https://github.com/brunoribeirol/ratchery/blob/main/SECURITY.md), [private report form](https://github.com/brunoribeirol/ratchery/security/advisories/new) | Private intake, requested report contents, acknowledgement target |
| Build and tests | [Makefile](https://github.com/brunoribeirol/ratchery/blob/main/Makefile), [CI workflow](https://github.com/brunoribeirol/ratchery/actions/workflows/ci.yml) | Standard test entry point and public cross-platform automation |
| New-feature test policy | [CONTRIBUTING](https://github.com/brunoribeirol/ratchery/blob/main/CONTRIBUTING.md#running-the-tests), [tests](https://github.com/brunoribeirol/ratchery/tree/main/tests) | Tests required for behavior changes and recent public evidence |
| Static analysis | [CodeQL workflow](https://github.com/brunoribeirol/ratchery/blob/main/.github/workflows/codeql.yml), [Ruff/ShellCheck CI](https://github.com/brunoribeirol/ratchery/blob/main/.github/workflows/ci.yml) | Python SAST plus blocking lint/shell analysis before stable release |
| Supply-chain integrity | [Publishing](https://github.com/brunoribeirol/ratchery/blob/main/docs/PUBLISHING.md), [Releases](https://github.com/brunoribeirol/ratchery/releases) | Signed immutable tags, checksums, SPDX SBOM, deterministic archive, Sigstore provenance |
| Repository posture | [Scorecard](https://scorecard.dev/viewer/?uri=github.com/brunoribeirol/ratchery), [Scorecard workflow](https://github.com/brunoribeirol/ratchery/blob/main/.github/workflows/scorecard.yml) | Automated public repository-health evidence; not a substitute for source SAST |
| Governance reality | [MAINTAINERS](https://github.com/brunoribeirol/ratchery/blob/main/MAINTAINERS.md) | Accurately records the current single-maintainer state |

## Answers that repository files cannot prove

The maintainer must supply or mark these honestly in the live form:

- secure-design/common-vulnerability knowledge;
- actual response history for bugs, enhancement requests, and vulnerability
  reports over each criterion's stated window;
- whether any medium-or-higher vulnerability is currently known and unpatched;
- any N/A answer involving cryptography, passwords, network protocols, or
  dynamic analysis;
- current account protections and repository settings that a file cannot
  enforce; and
- the exact OSPS Baseline version presented by the application on submission.

Do not convert “no report received” into a response-time claim, and do not use a
green Scorecard as proof that no source vulnerability exists.

## Submission sequence

1. Merge the stable-preparation PR and require its six CI jobs plus CodeQL to
   pass on the exact commit.
2. Publish and verify signed stable `v1.0.0`, its four assets, checksums, SPDX
   SBOM, and both attestations.
3. Sign in at [bestpractices.dev](https://www.bestpractices.dev/en/projects/new)
   with the maintainer account and create the Ratchetry project entry.
4. Complete metal Passing and OSPS Baseline Level 1 using current live wording,
   this evidence map, and explicit justifications.
5. Add a badge only after the public application reports the earned level. Use
   the exact application-generated project ID/URL; never guess it in advance.

The application is a human attestation and therefore cannot be completed or
approved by repository automation alone.
