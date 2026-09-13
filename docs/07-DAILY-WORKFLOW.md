# Daily Workflow

```bash
cd /path/to/repository
ratchery doctor
claude   # or codex
```

For an existing repo, run `ratchery init` once. Run `refresh` after meaningful stack/manifest/monorepo changes, not after every edit.

Trivial tasks: focused edit + targeted check. Standard tasks: trace callers/contracts/tests. Complex/high-risk tasks: use `work-plan`, isolate noisy research, validate in layers, then focused review.

Use `workspace-save` after work worth preserving. When another client or later
session will continue unfinished work, write one reviewed provider-neutral
handoff; on resume, inspect its target and Git provenance before trusting it:

```bash
ratchery memory handoff show --path . --json
ratchery memory handoff clear --path .          # dry run
```

The handoff is a bounded baton, not a transcript or an automatic memory feed.
Start a new AI session when the objective is unrelated. See `MEMORY.md` for the
write schema and explicit clear operation.
