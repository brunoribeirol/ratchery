# Start Here

**Ratchetry 1.0** is a batteries-included, low-overhead operating layer for Claude Code,
Codex, and durable Obsidian memory. It installs a safe, curated workspace and uses its
Adaptive Engine, Context Engine, and Tool Router to activate only the rigor, context, agents,
Skills, and optional tools whose benefit justifies their cost. Product scope and non-goals
are canonical in [Project Context](PROJECT_CONTEXT.md).

Read in this order when needed:

1. Install or upgrade with [Installation](INSTALLATION.md), then use
   [User Guide](USER-GUIDE.md) and [Commands](COMMANDS.md) for day-to-day work.
2. Understand the current implementation in [Architecture](ARCHITECTURE.md), the
   ownership-boundary model in [Workspace Architecture](02-ARCHITECTURE.md), and
   the optional directory layout in [Projects Workspace](03-PROJECTS-WORKSPACE.md).
3. Configure the clients through [Claude Code](05-CLAUDE-CODE.md) and
   [Codex](06-CODEX.md). The [Daily Workflow](07-DAILY-WORKFLOW.md) and
   [Workflow](WORKFLOW.md) explain how the pieces fit together.
4. Continue work across agent clients with [Provider-neutral Memory](MEMORY.md).
   Control context cost with [Profiles and Context](08-PROFILES-CONTEXT.md) and
   [Context and Tokens](17-CONTEXT-TOKENS.md), then measure changes with
   [Cost and Token Benchmarking](BENCHMARKING.md). Use
   [Vault Migration](04-VAULT-MIGRATION.md) only when moving existing notes.
5. Read [Security](10-SECURITY.md), [Hooks and Automation](11-HOOKS-AUTOMATION.md),
   and the repository [Security Policy](../SECURITY.md) before changing the
   sandbox, permissions, or hooks.
6. Review [Tools](09-TOOLS.md), [Tool Policy](TOOL_POLICY.md), and
   [QMD Security](18-QMD-SECURITY.md) before enabling optional integrations.
7. Operate and recover the setup with [Maintenance](13-MAINTENANCE.md),
   [Troubleshooting](14-TROUBLESHOOTING.md), and
   [Rollback and Uninstall](15-ROLLBACK-UNINSTALL.md).
8. Use the [File Reference](12-FILE-REFERENCE.md), [References](16-REFERENCES.md),
   [Developer Guide](DEVELOPER-GUIDE.md), and [CI Gate](CI_GATE.md) when changing
   or integrating the framework.
9. Use [Publishing](PUBLISHING.md) for reproducible release artifacts and the
   public-repository settings checklist, and [OpenSSF Evidence](OPENSSF.md) for
   the boundary between Scorecard and self-certified badges. The [historical decision
   matrix](decision-matrix.md) and [external research](research-external.md)
   are optional design provenance, not prerequisites or current behavior specs.

Core rule: source code remains in repositories; curated durable knowledge remains in Obsidian; runtime/config live outside both.

Upgrade policy: do not create a new setup version merely because a tool released a newer version. Update only for a relevant security issue, upstream breaking change, real migration bug, removal of custom complexity by a native capability, or measured workflow improvement.
