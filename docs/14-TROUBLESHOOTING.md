# Troubleshooting

## `ratchery` not found
Add `export PATH="$HOME/.local/bin:$PATH"` to `~/.zshrc` and open a new shell.

## Codex asks to trust hooks
Expected for project-local hooks. Trust only repositories you created or reviewed.

## Old SessionEnd ENOENT warning
Current releases do not install SessionEnd persistence hooks by default. If an existing repository migrated from an older 8.x setup still has an Ratchetry SessionEnd hook, run:

```bash
ratchery refresh
ratchery doctor --deep
```

The refresh removes the old Ratchetry-owned close hook while preserving user-owned hooks.

## QMD says blocked
Run `ratchery tools-status --probe`. QMD <=2.6.3 or an unparseable version is intentionally disabled. Do not bypass the gate merely to silence the warning. Install a verified stable release with the upstream project-local trust fixes, then retry.

## QMD not configured
After a safe version is installed, run `vault-qmd-status`, then `vault-qmd-setup` to see the explicit plan. Only rerun with `--apply` if desired.

## Doctor fails
Fix the reported semantic error. Do not reinstall repeatedly as a substitute for understanding the failure.

## Memory says no matching Vault project exists

Run `ratchery memory status --path . --json` and compare the reported
error with the repository's `.agents/state/project-id` and the `project_id` in
the intended Vault project's `Home.md`. Do not copy an ID from another project.
If this repository was moved or reinstalled, run its normal `init`/`refresh`
path so the existing UUID-bound Vault project is reused.

## Memory rejects a symlink or duplicate project UUID

This is fail-closed behavior. Replace a symlinked Vault root/project/Home/handoff
with reviewed regular files and directories, or resolve duplicate `Home.md`
identities before retrying. The command will not guess which project owns the
handoff.

## A pending handoff blocks a new write

Inspect it with `ratchery memory handoff show --path . --json`. Clear it
after consuming it, or use `--replace` only when intentionally superseding it;
both applied clear and replacement create private backups.

## Memory rejects handoff permissions after sync

`Handoff.json` must be private to the current user (`0600` or stricter). Some
sync/restoration tools do not preserve mode bits. Inspect the file and storage
boundary, then restore private permissions before retrying; do not bypass the
check for a shared filesystem.
