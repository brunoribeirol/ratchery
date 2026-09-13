---
name: search-vault
description: Retrieve concise, relevant knowledge from the configured Obsidian Vault. Use for prior decisions, session summaries, reusable bugs, commands, references, or project memory; do not use for source code that is already in the current repository.
---

# Search Vault

Use the Vault as curated memory, not as the source of truth for current code.

1. Start with the current project's `Home.md` when its vault slug is known.
2. Prefer `ratchery vault-search "$ARGUMENTS" -n 8`.
3. If QMD is configured, consume result snippets first and open only the notes required to answer the task.
4. If QMD is unavailable, use the command's lexical fallback rather than scanning the entire Vault.
5. Prefer decisions, reusable bugs, commands, references, and recent session summaries over raw clippings.
6. Verify any repository-specific fact against the current repository before acting on it.
7. Never copy raw transcripts or secrets into durable memory.

Return a short list of the notes used and the conclusion they support.
