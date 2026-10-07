# Capabilities and Workflows

Ratchetry ships a curated capability catalog rather than loading every available agent,
Skill, MCP server, or tool into every session. This document explains how to choose an
outcome, inspect the exact contract, and verify the catalog without invoking a model or
accessing the network.

## Start with the goal

```bash
ratchery workflows list
ratchery workflows recommend --goal "understand this repository"
ratchery workflows recommend --goal "implement a feature"
ratchery workflows recommend --goal "audit security"
ratchery workflows show prepare-release
```

`recommend` uses explicit phrases from the versioned workflow registry. Its result is an
advisory plan: nothing is installed, enabled, invoked, or edited. If no phrase matches, use
`workflows list`; Ratchetry does not guess through a hidden model call.

The shipped workflows are:

- `understand-repository` -- bounded exploration, then investigation/architecture only if
  evidence requires it;
- `implement-feature` -- tier-appropriate plan/spec, vertical red/green/refactor slices,
  implementation, broader tests, and review;
- `debug-failure` -- reproduce, minimize, test competing hypotheses, prove the root cause,
  then apply an approved minimal fix with regression evidence;
- `security-audit` -- read-only threat boundary and verified findings;
- `security-hardening` -- selected findings, approval, fixes, closure tests, and re-review;
- `prepare-release` -- inventory, dependency/security, artifacts, and immutable-action gate;
- `migrate-system` -- impact/rollback map, spec, approval, execution, and verification.

## Inspect Skills and agents

```bash
ratchery skills list
ratchery skills show security-hardening
ratchery skills validate
ratchery skills eval

ratchery agents list
ratchery agents show security-reviewer
ratchery agents validate
ratchery agents eval
```

`show` resolves the canonical registry metadata with the shipped files and reports:

- semantic version and Ratchetry origin;
- Claude and Codex coverage;
- permission ceiling and network policy;
- positive signals and explicit non-triggers;
- source/resource paths and a computed SHA-256 digest;
- the clients' native agent permission declarations when applicable.

The digest is observational evidence, not a remote trust claim or signature. Validation
fails on registry/disk drift, missing client pairs, unsafe/symlinked assets, invalid policy,
unknown eval references, or failing behavior fixtures.

## What the behavior evals prove

The fixtures are deterministic and zero-LLM. They submit short task descriptions to the
same explicit signal/anti-signal matcher used for advisory capability recommendations and
assert required and forbidden selections. This catches catalog drift and dangerous
over-selection cheaply in CI.

They do **not** claim to measure the private routing behavior of Claude or Codex. Real-client
compatibility remains a separate no-inference canary, and task quality/cost remains a
separate repeated benchmark.

## Security hardening boundary

Use `security-audit` when the requested outcome is findings only. Use
`security-hardening` only when verified findings exist and remediation is requested. Each
finding must include:

```text
id | severity | asset | evidence | scenario | remediation | closure_test | status
```

The workflow stops at an explicit approval step before a fix. A finding never grants
permission to install dependencies, change schema/auth, write unrelated files, commit,
push, publish, or expose a secret. Resolution requires both the evidence path and closure
test to pass, followed by independent re-review for sensitive or cross-cutting changes.

## Technology radar

```bash
ratchery radar status
ratchery radar show mcp-registry
ratchery radar stale
ratchery radar validate
ratchery radar watch
ratchery radar watch --json
```

The radar records the source, current review decision, rationale, licensing-review state,
last review, and next recheck for technologies Ratchetry may learn from. The decisions are:

- `adopted` -- incorporated into Ratchetry's current design;
- `trial` -- bounded experiment with explicit evidence;
- `assess` -- worth continued review, not approved for activation;
- `hold` -- deliberately deferred or rejected for current product scope.

The regular radar commands and the default `watch` mode are offline and read-only. `watch`
shows the exact strict GitHub repository endpoints eligible for a later metadata query but
does not contact them. An explicit `ratchery radar watch --online` query may read bounded
public repository metadata from `api.github.com`; it never retrieves source files, follows
redirects, installs a package, edits the radar, or promotes a candidate.

The daily `Technology Watch` workflow runs that same advisory query with only
`contents: read` and writes its report to the workflow summary. Upstream activity,
popularity, licensing metadata, or a third-party audit is a prompt for human review, never
an automatic trust or adoption decision. Arbitrary Skill import, MCP installation, issue
creation, pull requests, and unattended repository updates remain out of scope.
