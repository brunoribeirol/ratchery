# Installation

This is the real `install.sh` flag reference and install/upgrade behavior.

There are two supported boundaries:

- `install.sh` installs a verified source/release tree into a user prefix and
  then configures that user account.
- A package manager installs only the immutable runtime. The user then runs
  `ratchery setup` explicitly; a Formula must never choose a Vault or mutate
  agent configuration during `brew install`.

## Prerequisites

- **Python 3.11+** (required). Ratchetry parses and semantically validates the generated
  Codex security policy with the standard-library `tomllib` module; Python 3.10 cannot
  perform that check without adding a dependency. `preflight` therefore fails below 3.11,
  and project `doctor --json` reports an error instead of silently skipping TOML security
  validation.
- **git** — not strictly required to install, but `preflight()` warns if it's missing
  ("Git CLI not found; project Git initialization and Git-aware hooks will be limited").
- **Optional: an existing Obsidian Vault directory.** Supply `--vault PATH` only when you
  want curated durable memory. Ratchetry never creates or guesses a Vault; an explicitly
  supplied path must already exist.
- Claude Code and/or the Codex CLI are optional at install time; the framework's
  `.claude/`/`.codex/` project files are generated either way. When installed, Claude Code
  must be **2.1.187+** and Codex CLI must be **0.138.0+** so the generated credential and
  permission-profile contract stays within Ratchetry's supported/tested range. `preflight`,
  project `doctor`, and `doctor-global` reject an installed client whose version is older
  or cannot be verified.
- **macOS, Linux, or WSL2** is the tested installer/runtime path. In particular,
  provider-neutral handoff mutations require POSIX descriptor and advisory-lock
  primitives and fail closed rather than writing without them on another platform.

## Every install.sh flag

From `install.sh`'s own argument parser (verified by reading the script directly):

```text
Paths:
  --projects-root PATH            Default parent for projects (default: ~/Projects)
  --prefix PATH                   Install prefix (default: ~/.local)

Optional memory:
  --vault PATH                    Existing Obsidian vault
  --no-vault                      Explicitly disable Vault memory

Behavior:
  --project-layout MODE           flat | categorized (default: flat)
  --vault-migration MODE          safe | preserve (default: safe)
  --external-tools POLICY         none | recommended (default: none)
  --dry-run                       Run preflight + show migration/install plan; write nothing
  --yes                           Skip interactive confirmation
```

Notes on each:

- `--vault` — optional. When supplied, it must already exist (`[[ -d "$VAULT" ]]` is
  checked before anything runs). On a fresh install, omitting both memory flags starts in
  core-only mode. On an upgrade, omission preserves the existing memory selection.
- `--no-vault` — explicitly stores `vault_path: null`. It disables the integration but
  never deletes or rewrites the old Vault. It is mutually exclusive with `--vault`.
- `--project-layout` — `flat` puts new projects directly under `--projects-root`;
  `categorized` also creates `personal/academic/learning/work/experiments/archived`
  subdirectories (see `CATEGORIES` in `lib/agent_workspace.py` and
  `setup_projects_workspace()`).
- `--vault-migration` — `safe` (default) detects and safely replaces a recognized legacy
  Vault Agent Memory Kit v1.0 installation (external backup first); `preserve` skips that
  detection/replacement. See `docs/04-VAULT-MIGRATION.md`.
- `--external-tools` — `none` (default) installs nothing beyond the framework itself;
  `recommended` additionally runs `ratchery tools-install-recommended`, which — per
  its own implementation and printed banner — **still installs nothing automatically**; it
  only prints guidance. The versioned catalog (`tools.lock.json`) includes
  profile/on-demand/experimental retrieval, output, observability, scanner, and
  MCP-security candidates; you review and install each one yourself.
- `--dry-run` — runs `preflight`, runs `vault-plan` only when `--vault` was supplied,
  prints the candidate, target paths, memory state, layout, and tool policy, and exits.
  **Writes nothing to disk.**
- `--yes` — skips the interactive `Continue? [y/N]` confirmation prompt; useful for
  non-interactive/CI installs.

## Homebrew

The official tap packages the immutable `v1.1.0` runtime and was validated on
macOS and Linux:

```bash
brew install brunoribeirol/tap/ratchery
ratchery --version
```

Installation deliberately does not choose a projects root, enable a Vault, or
write agent configuration. Preview and apply user-scoped setup separately:

```bash
ratchery setup --projects-root "$HOME/Projects" \
  --project-layout categorized --external-tools none --dry-run
ratchery setup --projects-root "$HOME/Projects" \
  --project-layout categorized --external-tools none --yes
ratchery doctor-global --deep
```

Update or remove the packaged runtime with Homebrew:

```bash
brew update
brew upgrade ratchery
brew uninstall ratchery
```

Uninstalling the Formula does not delete `~/.config/ratchery`,
`~/.local/state/ratchery`, initialized project files, or an optional Vault.
Those are user-owned state and must be reviewed separately.

If another installation appears earlier in `PATH`, `brew --prefix ratchery`
identifies the Homebrew prefix. Inspect the packaged command directly with:

```bash
"$(brew --prefix ratchery)/bin/ratchery" --version
```

## Setup after a package-manager install

`ratchery setup` is the supported post-install command for Homebrew and other
runtime-only package managers. It uses the same managed blocks, ownership
checks, Vault backup, project-workspace layout, preflight, and doctor paths as
the source installer, but it does not copy or replace the installed runtime.

Preview first:

```bash
ratchery setup --projects-root ~/Projects \
  --project-layout categorized --external-tools none --dry-run
```

Apply after reviewing the plan:

```bash
ratchery setup --projects-root ~/Projects \
  --project-layout categorized --external-tools none --yes
```

The flags are `--vault` (enable/select an existing directory), `--no-vault` (explicitly
disable memory), `--projects-root`
(default `~/Projects`), `--project-layout flat|categorized`,
`--vault-migration safe|preserve`, `--external-tools none|recommended`,
`--dry-run`, and `--yes`. Without `--yes`, setup requires an interactive yes;
EOF or any other answer fails closed without writing. The `recommended` tools
policy still installs nothing—it prints reviewable guidance only.

Omitting both memory flags preserves an existing selection. In a fresh HOME there is no
selection, so the same short command creates a core-only configuration. This avoids both a
mandatory Vault for newcomers and silent memory loss during upgrades.

The command is idempotent. Running it again refreshes Ratchetry-owned global content and
preserves human-owned content. With `--vault`, it also creates the same external Vault
backups used by `vault-install`; without `--vault`, no Vault is read or written. If the
final doctor finds malformed configured Vault content, setup returns non-zero with repair
guidance; it does not silently call a fixer.
Vault, projects-workspace, and global managed targets must be real directories
and regular files rather than symlinks; setup rejects an unsafe layout before
writing configuration.

## Dry-run example

```bash
bash install.sh --projects-root ~/Projects --dry-run
```

This runs `preflight` (Python/git/Claude/Codex/QMD checks), reports that Vault memory is
optional and unconfigured, then prints the candidate version, target runtime path,
projects root, layout, and tools policy. No file is touched. Supplying
`--vault ~/ObsidianVault` additionally prints the Vault migration plan (`vault_plan()`'s
list of backups, legacy-kit replacements, and metadata cleanup) while remaining read-only.

## Real install

```bash
bash install.sh --projects-root ~/Projects \
  --project-layout categorized --external-tools none --yes
```

To enable durable memory during installation—or later on the same install—pass an existing
Vault explicitly:

```bash
ratchery setup --vault ~/ObsidianVault --projects-root ~/Projects \
  --project-layout categorized --external-tools none --yes
ratchery vault-doctor
```

When you first open an initialized repository with Codex, review the checkout
and accept Codex's repository-trust prompt. Codex intentionally ignores the
repository's `.codex/config.toml` until the user grants that trust; Ratchetry
cannot and does not write a user-level trust decision for you. Claude likewise
keeps Ratchetry-managed MCP calls pending explicit permission.

## Upgrade behavior: idempotent, atomic, auto-rollback

Re-running `install.sh` against an existing installation is safe and idempotent — the same
flags produce the same end state. The install mechanism in `install.sh`:

1. If a previous runtime exists at `$SHARE` (`$PREFIX/share/ratchery`), it is copied
   to a timestamped backup under `$STATE/runtime-backups/<stamp>-v<previous-version>/`
   before anything else changes.
2. The new package is staged into a **separate directory** next to the target:
   `$PREFIX/share/.ratchery-<version>-$$` (PID-suffixed to avoid collisions).
3. The old `$SHARE` is renamed to `$SHARE.previous` (not deleted yet).
4. The staged directory is atomically renamed (`mv`) into place as the new `$SHARE`.
5. **If that final `mv` fails**, the script immediately restores `$SHARE.previous` back to
   `$SHARE` and exits non-zero — the previous working install is never left in a broken
   half-written state. Only on success is `$SHARE.previous` removed.

This is a stage-then-atomic-rename pattern with automatic rollback on failure, not a
package-manager transaction log — but it achieves the same practical guarantee: an install
that fails partway through does not corrupt an existing working installation.

### Upgrade from the pre-rebrand command

If no Ratchetry runtime exists but
`$PREFIX/share/agent-workspace/MANIFEST.json` is a regular, non-symlinked file,
the installer treats that directory as the previous private-development
runtime. It backs up the complete directory into Ratchetry state, installs the
new runtime separately, and exposes both names:

```text
$PREFIX/bin/ratchery        -> $PREFIX/share/ratchery/bin/ratchery
$PREFIX/bin/agent-workspace -> $PREFIX/share/ratchery/bin/ratchery
```

The compatibility name does not install or load a second runtime. A regular
legacy `${XDG_CONFIG_HOME:-~/.config}/agent-workspace/config.json` is accepted
only when the new config does not exist; the confirmed install writes the same
settings into `${XDG_CONFIG_HOME:-~/.config}/ratchery/config.json`. Symlinked
legacy config/runtime/manifest inputs are rejected rather than followed.

The old runtime and config are deliberately not deleted during upgrade. First
run `ratchery doctor-global --deep`, exercise a real initialized project, and
inspect the Ratchetry runtime backup. Only then follow the reviewed legacy
cleanup instructions in `15-ROLLBACK-UNINSTALL.md` if you want to reclaim the
small amount of disk space.

Per-project config merges during `refresh` follow the same "never destroy" discipline
described in `ARCHITECTURE.md`'s managed-block section — re-running `ratchery
init`/`refresh` on an already-initialized project is also idempotent and preserves
human-owned content.

## Verifying success

```bash
ratchery doctor-global --deep
ratchery --version
agent-workspace --version  # temporary 1.x compatibility alias
bash tests/run-tests.sh
```

`doctor-global --deep` checks: the projects root exists, `~/.claude/CLAUDE.md`,
`~/.codex/AGENTS.md`, and `~/.agents/skills` exist, Python version, Claude/Codex CLI
presence and security-capable version, QMD's security-gate state, and — with `--deep` — runs `codex
doctor` if the Codex CLI is present and `qmd doctor` if a safe QMD version is configured,
then runs the Vault doctor (`vault_audit()`) only when memory is configured. An absent
Vault is healthy optional state; an explicitly configured path that disappears is an error.

`bash tests/run-tests.sh` is the bash integration suite (see `DEVELOPER-GUIDE.md` for what
it covers); it runs `install.sh` end-to-end against isolated `$HOME` fixtures in both
core-only and configured-Vault modes, so
a clean pass is a strong signal the installer itself works on your machine, not just that the
Python unit tests pass.

Also useful right after install: `ratchery tools-status` (command-path discovery with
no optional binary execution) and `ratchery tools-recommend` (read-only Tool Router
guidance based on the repository profile, command discovery, and explicit MCP opt-ins).
Use `--probe` only when you intend to execute version/QMD checks. If you explicitly install
ccusage, `ratchery usage --offline`
shows local token/cost data, `ratchery budget check --help` documents
no-state estimated thresholds, and `ratchery benchmark --help` documents
the aggregate evidence loop; see `BENCHMARKING.md` before comparing tools.
