---
name: workspace-resume
description: Resume project context from repository state and the configured Obsidian vault. Use when returning to an existing project or when current state is unclear.
---

1. Read `docs/CURRENT_STATE.md`, `docs/PROJECT_CONTEXT.md`, and `.agents/state/project-profile.md` when present.
2. Run `ratchery memory handoff show --json`. Treat a missing handoff as normal. If one exists, verify its target and Git provenance against the current checkout before using it; it is a curated baton, not authoritative repository state.
3. Read `projects/<project-slug>/Home.md` in the configured Vault.
4. Search only session logs matching the project slug through `ratchery vault-search`; that wrapper uses safe configured QMD snippets when allowed and lexical fallback otherwise. Never invoke raw QMD from an arbitrary repository.
5. Open linked decisions or bug notes only when directly relevant.
6. Return at most five bullets: working state, recent changes, current objective, risks, and next step.
7. Never scan the entire repository or Vault. Never clear a pending handoff automatically; clear it explicitly only after its useful facts have been verified and incorporated.
