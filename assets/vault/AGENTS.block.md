# Vault Operating Contract

## Purpose

This Obsidian Vault is the curated long-term knowledge base for software projects, technical decisions, reusable bug solutions, academic work, career development, commands, and references.

The Vault is not a transcript archive and must not duplicate complete repositories.

## Sources of truth

- Project repositories are authoritative for source code, implementation state, commands, tests, migrations, deployment configuration, and repository-specific ADRs.
- The Vault stores concise durable knowledge, cross-session context, reusable lessons, project indexes, and meaningful links.
- When repository and Vault information conflict, inspect the repository and update the stale Vault note.
- Never claim a command, test, deployment, or validation was executed without evidence.

## Retrieval policy

1. Identify the current project slug.
2. Open `projects/<project-slug>/Home.md`.
3. Search only matching session logs and linked notes.
4. Use focused QMD snippets before opening full notes when QMD is available.
5. Open the smallest useful set of notes.
6. Never bulk-read the Vault.

## Note policy

- Every new durable note must contain valid YAML frontmatter.
- Search for an existing note before creating a new one.
- Update an existing note when it represents the same concept.
- Use meaningful Obsidian wikilinks for internal relationships.
- Never create artificial links only to satisfy a numeric requirement.
- Use kebab-case for new files in global knowledge directories.
- Preserve established naming conventions inside existing project folders.
- Operational and technical notes should normally be written in English.

## Durable-write policy

Create or update a bug note only when the root cause was non-obvious, the investigation required meaningful work, the problem may recur, or the solution has reusable value.

Create or update a decision note only when multiple reasonable options existed and the choice affects architecture, security, data, cost, compatibility, operations, or maintainability.

Session logs must be concise summaries containing objective, completed work, significant decisions, reusable bugs, validation, unresolved risks, next steps, and relevant links. They must never be raw transcripts. A pending `projects/<slug>/Handoff.json` is a bounded, CLI-validated baton for another agent/session, not a second history store; verify it against repository state and clear it explicitly after use.

## Project synchronization

When durable project state changes:

- update `projects/<project-slug>/Home.md`;
- keep the summary concise;
- link significant decisions and reusable bugs;
- reference repository paths instead of copying source files;
- preserve user-written content outside explicit managed sections.

## Safety

- Never delete or reorganize user notes without explicit confirmation.
- Never store credentials, tokens, private keys, `.env` contents, or sensitive personal data.
- Never store hidden reasoning, raw command output, full conversations, or complete source files.
- Never invent project state, decisions, validation results, links, or repository paths.
- No executable Ratchetry scripts belong inside the Vault.

## Responsibility boundaries

Repeatable workflows belong in Agent Skills. Deterministic safety and lifecycle behavior belongs in hooks or the external Ratchetry runtime. This file contains only always-on rules that should be loaded in every Vault session.
