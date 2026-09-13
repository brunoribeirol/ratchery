# Projects Workspace

This directory is an optional, categorized home for repositories managed with
Ratchetry. Each project remains an independent Git repository; do not
initialize Git in `~/Projects` itself.

## Layout

```text
~/Projects/
├── personal/
├── academic/
├── learning/
├── work/
├── experiments/
└── archived/
```

| Directory | Use it for |
| --- | --- |
| `personal/` | Independent products, portfolio work, and open source |
| `academic/` | Research, theses, and institutional deliverables |
| `learning/` | Courses, tutorials, and guided exercises |
| `work/` | Employer, client, internship, and consulting repositories |
| `experiments/` | Short-lived prototypes and uncertain ideas |
| `archived/` | Inactive projects kept for reference |

Move a repository when its purpose changes. For example, promote a useful
prototype from `experiments/` to `personal/` instead of maintaining duplicate
copies.

## Common commands

Create a project and initialize its agent configuration:

```bash
ratchery new personal/my-project
```

Initialize an existing repository:

```bash
cd ~/Projects/personal/my-project
ratchery init
```

Inspect the effective risk tier and installation health:

```bash
ratchery tier
ratchery doctor --deep
```

Run `ratchery --help` for the full command list.

## Boundaries

- Source code belongs in the project repository, not in the Obsidian Vault.
- Durable notes and decisions may be linked from the configured Vault, but the
  repository remains the source of truth for code, tests, and current docs.
- Keep credentials outside repositories. Commit documented examples such as
  `.env.example`, never real secret files.
- Keep work/client code and credentials separate from personal projects.
- Archive inactive repositories rather than leaving ambiguous abandoned copies.

## Useful checks inside a project

```bash
git status --short
ratchery doctor --deep
ratchery tier --json
```

Project-specific build, test, lint, and security commands belong in that
project's own `README.md`, `CONTRIBUTING.md`, or task runner.

## Where the full documentation lives

This file is intentionally only a workspace index. Installation, architecture,
security, integrations, maintenance, and troubleshooting are documented in the
Ratchetry repository. Keeping one canonical manual avoids installing a
large, stale copy into every user's projects directory.
