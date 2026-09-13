---
name: workspace-save
description: Save durable project state and concise knowledge after meaningful work. Use near the end of a task, phase, or session; never store raw prompts, transcripts, or secret values.
---

# Workspace Save

1. Update `docs/CURRENT_STATE.md` with confirmed state, changed files, validation, risks, and next steps.
2. Create or update one concise Vault session log only when the work is worth retaining. Summarize outcomes, not the conversation. Write it to this project's own `projects/<slug>/session-logs/` folder in the Vault -- never to a shared global `session-logs/` bucket; each project owns its own log history.
3. Update the project `Home.md` only with durable information.
4. Create a decision or bug note only when it is reusable and non-trivial.
5. Never persist raw user prompts, transcripts, hidden reasoning, full tool output, credential values, or sensitive customer data.
6. Preserve user-written content and use meaningful wikilinks.
7. When another agent client or later session will continue unfinished work, create one reviewed provider-neutral handoff with `ratchery memory handoff write --stdin`. Include only `source_client`, optional `target_client`, objective, completed items, repository-relative changed files, checks (`command`, `status`, `summary`), open risks, and next action. The CLI derives project/Git provenance and rejects unknown, oversized, or secret-like input.
8. Inspect an existing handoff before deliberately passing `--replace`; never use the handoff as a transcript, activity log, or automatic capture channel.
9. Run `ratchery vault-refresh` after durable Markdown Vault changes so the dashboard reflects recent activity. `Handoff.json` is intentionally outside the QMD Markdown index and does not require a refresh.
10. Suggest a Conventional Commit message when code changed.
