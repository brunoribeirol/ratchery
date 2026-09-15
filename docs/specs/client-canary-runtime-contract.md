# Delta Spec: Real-client canary runtime contract

Mode: **openspec-light** (T1/T2 default).

## Why

The first hosted client canary proved that its own test harness was invalid in
three independent ways: it disabled Claude Code's required native-binary
installation step, emitted Codex agent-control keys in a shape rejected by the
declared minimum client, and attempted to nest Codex's Linux sandbox inside a
GitHub-hosted runner that cannot create the required network namespace. These
are release-gate defects, not evidence that Ratchetry's security boundaries
failed.

## What changes

- Generate and validate the Ratchetry project once in a dedicated read-only
  preparation job, then upload only that generated fixture.
- Install each public client in a separate credential-free job before the
  fixture is downloaded. Allow lifecycle scripts only for the official Claude
  Code package because its native binary requires the package's installation
  step; keep scripts disabled for Codex.
- Keep the Codex concurrency cap and interruption policy in the legacy-compatible
  root keys accepted by both the declared minimum line and current clients.
  Reserve `[agents]` exclusively for named role tables.
- Validate that Codex strictly parses the complete generated configuration and
  exposes named permission profiles under the minimum/current CLI spelling,
  without executing a nested OS sandbox in the hosted runner.

## Affected contracts

- `.github/workflows/client-canary.yml`
- `assets/project/.codex/config.base.toml`
- Generated project `.codex/config.toml`
- Scheduled/manual client-canary evidence

## Out of scope

- This canary does not authenticate, run model inference, connect to an MCP
  server, or prove OS-sandbox containment.
- The Claude Code 2.1.187 and Codex CLI 0.138.0 supported floors do not change.
- No third-party client becomes a Ratchetry runtime dependency.

## Tasks

- [x] Reproduce and classify all four failed canary legs.
- [x] Prove the compatibility-safe Codex key layout against an older local CLI.
- [x] Implement the isolated preparation/client workflow.
- [x] Add static regression coverage for installation and config contracts.
- [x] Update operator/security documentation and release evidence.
- [x] Run targeted and full local release validation.

## Validation

```bash
python3 tests/test_client_canary_contract.py
python3 tests/test_doctor_tier_json.py
python3 scripts/verify-action-pins.py
python3 scripts/verify-doc-links.py
make test
make release-smoke
```

The hosted acceptance check is a fresh manual `client-canary.yml` run whose
preparation job and all four minimum/current client legs pass on the exact
protected `main` commit.

## Status

- [ ] Proposed
- [x] In progress
- [ ] Implemented
- [ ] Archived (link the merged PR/commit)
