# Claude Code

`CLAUDE.md` is a short adapter to the shared repository contract in `AGENTS.md`. `.claude/rules/` carries path-scoped stack rules. Four backward-compatible baseline agents plus the tier/capability/on-demand set are available; a fresh T0 project starts with five. Use `ratchery agents-status` for the effective set.

Security is layered: permissions deny + sandbox filesystem/credential denial + subprocess environment scrub + deterministic PreToolUse guard. Sandbox is configured to fail closed, bypass-permissions mode is disabled, and the unsandboxed retry escape hatch is disabled. Ratchetry-managed MCP tools remain explicit opt-ins under `permissions.ask`.

The hook uses Claude's `CLAUDE_PROJECT_DIR` in exec form (`command` plus
`args`), avoiding shell-based Git-root interpolation. Home and project-local
credential files are denied in the permission, filesystem, and credential
layers; `doctor` checks that the complete shipped baseline remains present.

Use native search/code intelligence before external symbolic tooling. For broad architecture in genuinely large repositories, `architecture-map` may prefer Graphify when it is already installed and a graph materially reduces broad reads.

The custom `explorer`, `reviewer`, and `security-reviewer` agents declare `permissionMode: plan`. `test-runner` omits that override because tests may legitimately create caches/artifacts; it still has no Write/Edit tools.

Default hooks are intentionally limited to `UserPromptSubmit` and `PreToolUse`. There is no default SessionEnd persistence hook: durable memory is saved explicitly with `workspace-save`, avoiding fragile close-time behavior when a workspace is moved or deleted.
