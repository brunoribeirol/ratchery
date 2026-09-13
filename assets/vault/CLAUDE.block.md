@AGENTS.md

# Claude Code Vault Adapter

- Treat this Vault as curated long-term memory, not as the primary code workspace.
- Use the shared `workspace-resume` and `workspace-save` Skills for repeatable workflows.
- Prefer targeted retrieval and snippets before opening full notes.
- Do not bulk-read `projects/` (including any project's own `session-logs/` subfolder), `references/`, `academic/`, or `tcc/`.
- Do not write full conversations, hidden reasoning, credentials, raw terminal output, or entire source files to the Vault.
- Do not claim an automatic action occurred without verifying the resulting file or tool output.
