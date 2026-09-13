# File Reference

- `AGENTS.md`: shared repository contract.
- `CLAUDE.md`: Claude adapter.
- `.agents/runtime/agent_workspace.py`: per-project hook runtime.
- `.agents/state/project-id`: durable UUID.
- `.agents/state/project-profile.*`: adaptive profile.
- `.agents/state/task-policy.json`: risk/classification metadata without prompt text.
- `.agents/state/ownership.json`: managed-surface metadata.
- `.agents/state/mcp-enabled.json`: repository-shared opt-ins for optional MCP
  servers, used to preserve an explicit team decision across clone/refresh.
- `${XDG_STATE_HOME:-~/.local/state}/ratchery/benchmarks/`: local
  per-project aggregate token/cost/task snapshots outside the repository; no
  prompts, responses, raw usage rows, session IDs, paths, or project labels.
- `<vault>/projects/<slug>/Handoff.json`: the single bounded pending
  provider-neutral handoff, resolved by project UUID and excluded from QMD's
  Markdown index.
- `<vault>/projects/<slug>/.Handoff.lock`: an empty private advisory-lock file
  used only to serialize Ratchetry handoff mutations; it contains no
  memory or agent output and may persist between commands.
- `${XDG_STATE_HOME:-~/.local/state}/ratchery/memory-backups/`: private
  copies created before an explicit handoff replacement or clear.
- `.claude/settings.json`: Claude sandbox/permissions/hooks.
- `.codex/config.toml`: Codex permission/agent config.
- `.codex/hooks.json`: Codex hooks.
- `docs/COMMANDS.md`: managed detected commands + human notes.
- `docs/CURRENT_STATE.md`: confirmed local session-to-session working state;
  projects may deliberately ignore it while keeping contributor-facing facts in
  committed specs, ADRs, and the changelog. An exact ignore entry suppresses
  the otherwise-helpful missing-file warning from `doctor`.
- `docs/PROJECT_CONTEXT.md`: durable repo-local context.
- `tools.lock.json`: versioned optional-tool family, activation, network, and
  benchmark policy; it is a catalog, not an installation lockfile.

Project configuration backups live under
`${XDG_STATE_HOME:-~/.local/state}/ratchery/project-backups/`. Backup
directories are mode `0700`; copied files and manifests are `0600`; manifests
identify the source relative to the project rather than storing its absolute
path.
