# Work Plan: Provider-neutral memory handoff

## Objective

Add a small, provider-neutral handoff protocol to the existing curated Vault
memory workflow so Claude Code, Codex, or another CLI can continue work without
copying a transcript or loading an automatic memory service.

## Non-goals

- Do not import Greenlight's task queue, PR runner, or orchestration layer.
- Do not install, start, configure, or contact `ai-memory`.
- Do not capture prompts, assistant responses, tool payloads, or sessions.
- Do not make Kiro or any additional agent client a directly supported runtime.
- Do not perform the Ratchery rebrand or command-path migration in this change.

## Evidence and assumptions

- The existing `workspace-save`/`workspace-resume` Skills and per-project Vault
  tree are the lowest-cost durable-memory path.
- The useful pattern considered during the Greenlight review is a concise,
  revision-bound handoff; its execution/orchestration layer is outside the
  product's stated scope. The upstream could not be retrieved during the final
  2026-09-12 re-check, so implementation must remain independent of its code and
  unverified behavior.
- The repository is T1 (`openspec-light`) and the change touches durable data,
  filesystem boundaries, CLI output, tests, and public documentation.
- `ai-memory` can provide automatic cross-machine/team capture, but its daemon,
  hooks, MCP surface, retention, and prompt/tool capture require a separate
  measured security trial before activation.

## Affected contracts and files

- New bounded handoff schema and validation in `lib/memory_engine.py`.
- New `memory` CLI group in `lib/agent_workspace.py`.
- Provider-neutral save/resume behavior in the global Skill assets.
- Vault session-log template and public memory/security/tool documentation.
- Unit and integration coverage plus the release manifest.

## Risks

- A handoff could accidentally persist a secret or sensitive path.
- A forged project/Vault identity could redirect a write to another project.
- Symlinked Vault paths could redirect a write outside the configured Vault.
- An overwrite or clear could destroy an unconsumed handoff.
- Claims about `ai-memory` could imply that an unconfigured backend is active.
- The extra CLI surface could add context/documentation burden without a real
  cross-agent continuation path.

## Workstreams and ownership

- Primary agent: schema, Vault boundary, CLI integration, docs, tests, manifest.
- Independent reviewer/security-reviewer/test-runner: isolated review and test
  evidence after implementation when service availability permits.

## Acceptance criteria

- One pending handoff is stored outside the repository in the exact Vault
  project selected by its durable project UUID.
- Input is bounded, schema-validated, secret-screened, and never executed.
- Git commit/dirty provenance is derived by the CLI, not accepted from input.
- Writes reject symlinks, wrong file types, identity mismatches, silent
  replacement, and path traversal.
- Clear is a dry run unless `--apply`; replacement creates a recoverable Vault
  backup.
- Human and JSON status/show modes share the same derived facts.
- The workflow is explicit only; no lifecycle hook or network call is added.
- `ai-memory` is described as an experimental alternative and never reported
  as enabled merely because its executable exists.

## Validation plan

- `python3 -m unittest tests.test_memory_engine tests.test_memory_cli`
- `python3 -m py_compile lib/*.py scripts/*.py tests/*.py`
- `ruff check lib/ scripts/ tests/ bin/`
- `python3 scripts/verify-doc-links.py`
- `python3 scripts/verify-manifest.py`
- `make test`
- `make release-smoke`
- Focused diff review and security scan of the new boundary.

## Handoff

Implementation owner: primary agent. Current state: complete. The final clean
release-candidate snapshot contains 267 shipped files; its integration suite,
306 unit tests, manifest/pin/link checks, Ruff, and archive installation smoke
all pass. Publication and rebranding remain a separate workstream.
