# Provider-neutral memory and handoffs

Ratchetry keeps durable memory explicit, local-first, and independent of a model
provider. Repository code and committed documentation remain authoritative;
memory is a concise navigation and continuation aid.

## Default backend

`curated-vault` is the built-in backend. It stores human-readable project notes
and session summaries in the configured Obsidian Vault. No Obsidian API,
network service, model call, embedding, or automatic lifecycle capture is
required.

The provider-neutral baton is a single machine-readable file:

```text
<vault>/projects/<project-slug>/Handoff.json
```

The CLI resolves `<project-slug>` by the repository's durable project UUID, not
by a possibly colliding directory name. The JSON file is deliberately outside
QMD's Markdown collection, so a pending handoff does not become an always-on
retrieval or context cost.

## Inspect memory

```bash
ratchery memory backends
ratchery memory status --path .
ratchery memory doctor --path . --json
ratchery memory plan curated-vault
ratchery memory plan ai-memory
```

`backends`, `status`, and `plan` never run an optional binary. Discovering an
`ai-memory` executable only reports that it is present; it does not report the
backend as enabled or trustworthy.

## Write a handoff

Supply one reviewed JSON object on standard input. Free text is intentionally
not accepted as command-line arguments, where it would remain in shell history
or a process listing.

```bash
ratchery memory handoff write --stdin <<'JSON'
{
  "source_client": "claude-code",
  "target_client": "codex",
  "objective": "Finish the memory documentation.",
  "completed": ["Implemented and tested the schema."],
  "changed_files": ["lib/memory_engine.py", "docs/MEMORY.md"],
  "checks": [
    {
      "command": "python3 -m unittest tests.test_memory_engine",
      "status": "passed",
      "summary": "Schema tests passed."
    }
  ],
  "open_risks": ["The full release smoke test has not run."],
  "next_action": "Run the full suite and inspect the final diff."
}
JSON
```

`target_client` may be `any` and defaults to it. Client identifiers are labels,
not an allowlist: a future or unsupported CLI can consume the same record by
calling the command or reading its JSON output. `source_client` is likewise a
self-declared label, not an authenticated identity; verify the Git provenance
and repository state instead of treating the label as proof of authorship.

The CLI derives and stores these fields itself:

- schema version and creation timestamp;
- durable project UUID and Vault slug;
- current Git commit and dirty state.

Callers cannot supply or override provenance. Check results remain
self-attested handoff data; they are not CI attestations.

## Resume and clear

```bash
ratchery memory handoff show --path .
ratchery memory handoff show --path . --json
ratchery memory handoff clear --path .          # dry run
ratchery memory handoff clear --path . --apply
```

Showing a handoff never consumes it. On resume, compare its target, commit, and
changed paths with the repository before acting. Clear only after the useful
facts have been verified and incorporated.

Only one handoff can be pending. A second write fails rather than silently
discarding the first. `--replace` is an explicit decision and creates a private
backup first. Clear is also backed up and is a dry run unless `--apply` is
present. Backups live under the user's XDG state directory with private
directory/file modes. Mutations take a non-blocking per-project POSIX advisory
lock across read, backup, identity revalidation, and replace/delete; a
concurrent Ratchetry mutation fails instead of racing.

Backups are intentionally not indexed or restored automatically, and v1 does
not silently purge them. They contain the old handoff verbatim, so apply the
same data-minimization rule and periodically remove reviewed, obsolete backup
directories according to your retention policy.

## Data minimization and limits

The input schema accepts exactly:

- `source_client` and optional `target_client`;
- `objective` and `next_action`;
- bounded arrays for `completed`, repository-relative `changed_files`,
  `checks`, and `open_risks`;
- each check has exactly `command`, `status`, and `summary`; status is
  `passed`, `failed`, `skipped`, or `not-run`.

Input and stored output are capped at 64 KiB, list counts and individual fields
are bounded, duplicate JSON keys, multiline fields, and control/format
characters are rejected, and
changed paths cannot be absolute or contain traversal. A narrow credential
tripwire rejects common private-key and API-token forms without printing the
matching value.

The tripwire is not DLP. Review the handoff before writing it. Never include:

- prompts, responses, transcripts, hidden reasoning, or raw tool output;
- credentials, tokens, private keys, environment values, or customer data;
- full source files or generated logs;
- claims that a check ran when it did not.

The Vault root, `projects` directory, selected project, `Home.md`, and
`Handoff.json` are opened through anchored directory descriptors. Symlinks,
wrong node types (including FIFOs), oversized files, duplicate project UUIDs,
and concurrent Ratchetry mutations are rejected. The configured Vault
path itself must not be a symlink; canonical ancestor paths are accepted.
Backup directories/files use the same no-follow, descriptor-anchored boundary.
An existing handoff with any group/other permission bits is rejected; fix the
sync/storage permissions before reading it.

These mutation guarantees require the POSIX file and lock primitives available
on the project's tested macOS, Linux, and WSL2 path. Other platforms fail the
memory mutation closed rather than falling back to an unlocked write.

## Why this is not an orchestrator

The handoff transfers facts; it does not launch agents, manage terminals,
create pull requests, assign tasks, or decide who works next. A concise
revision-bound baton was the useful design pattern considered during the
Greenlight review. Ratchetry implements that pattern independently; importing a
task queue or PR handover runtime would add permissions and operational cost
that do not belong in this setup. The referenced upstream repository was not
retrievable during the final 2026-09-12 verification, so no source or
unverified behavior from it is a dependency of this feature.

## Experimental automatic backend

[`ai-memory`](https://github.com/akitaonrails/ai-memory) remains an experimental
one-of alternative for a demonstrated team/multi-machine need. Its daemon,
hooks, MCP tools, spool/database, retention, authentication, automatic capture,
and injected context are materially different from the explicit handoff above.

`ratchery memory plan ai-memory` prints the required evaluation order but
does not install, start, contact, or configure it. A trial starts with native
hooks in repository allowlist mode, loopback networking, no LLM/embedding
provider, no Claude prompt/assistant capture, reviewed capture exclusions, and
one memory backend at a time. Promotion requires a reproducible comparison
against `curated-vault` using cost per successful task plus privacy, recovery,
latency, and retrieval-quality evidence.

This keeps provider neutrality in v1 without making every user pay the security,
context, dependency, and operations cost of automatic memory.
