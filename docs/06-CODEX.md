# OpenAI Codex

Codex receives the shared `AGENTS.md`, project `.codex/config.toml`, deterministic hooks, and the same active agent set as Claude Code. Four baseline agents are retained for compatibility and a fresh T0 project also activates `developer`; tier, capabilities, and explicit opt-ins can add more. Project network is disabled by default and secret-like environment variables are filtered from subprocesses.

Repository config and project hooks require trust/review in the client. Ratchetry preserves user-owned hook groups during `refresh` and only replaces groups identified as Ratchetry-owned; it never writes Codex's user-level repository-trust decision. Ratchetry-managed MCP profiles use explicit prompt approval, tool allowlists, timeouts, and output limits.

The hook's Git-root probe starts with a minimal environment and the runtime
scrubs caller-controlled Git routing again before accepting a discovered root.
Codex filesystem rules deny home and nested project-local credential files;
network remains disabled unless a reviewed workflow deliberately changes it.

Default hooks are `UserPromptSubmit` and `PreToolUse`; this setup does not depend on SessionEnd for persistence.

`ratchery doctor-global --deep` runs `codex doctor` on CLIs that support it. Failures are reported as diagnostic warnings rather than silently ignored.
