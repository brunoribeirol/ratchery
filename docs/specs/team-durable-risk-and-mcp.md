# Delta Spec: Team-Durable Risk and MCP Opt-Ins

Mode: **openspec-light**.

## Why

A new project currently receives a low tier before any human records its real
risk facts. Separately, `mcp enable` records its preservation marker in ignored
local state and configures only Claude while its success message implies both
clients. Those behaviors conflict with a security-first, dual-CLI team setup.

## Behavior

- An absent risk-answer file remains usable for provisional calculation so
  initialization stays non-interactive, but `init`/`tier` must say the result is
  provisional and project `doctor` must fail until `tier-set` records reviewed
  facts. Running `tier-set` with no flags explicitly confirms the defaults.
- MCP opt-ins are repository-shared state. Generated gitignore rules must commit
  `.agents/state/mcp-enabled.json`, and malformed marker state must fail closed.
- `mcp enable context7|serena` configures both Claude (`.mcp.json`) and Codex
  (a dedicated managed block in `.codex/config.toml`) from version-pinned/static
  definitions. It never starts, downloads, or contacts the server.
- Enable refuses to overwrite a same-name user-owned configuration. Disable
  removes only exact Ratchetry-owned definitions and preserves modified/custom
  content.
- `refresh` preserves both client configurations, and `mcp status` reports each
  client separately.
- Project `doctor` verifies that every recorded opt-in remains present for both
  clients and emits an error on drift.

## Compatibility and safety

- Existing projects without the marker are unchanged; their manual MCP entries
  are not claimed or removed.
- MCP remains explicit opt-in and outside the default token/context path.
- The Codex block uses the official `mcp_servers.<name>` TOML shape. Static
  definitions avoid a general-purpose TOML writer or new dependency.
- Context7 remains a remote HTTP server. Serena remains a pinned `uvx` command;
  enabling it writes configuration only, and the user reviews it before launch.

## Validation

- Unit tests cover fresh-clone persistence, malformed markers, user-owned
  collision preservation, dual-client enable/status/disable, and refresh.
- Project doctor tests cover missing Claude/Codex sides for a recorded opt-in.
- Full integration, Ruff, manifest verification, and TOML parsing must pass.

## Status

- [ ] Proposed
- [ ] In progress
- [x] Implemented
