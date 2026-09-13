# Rollback and Uninstall

Vault backups live under `~/.local/state/ratchery/backups`. Runtime backups live under `~/.local/state/ratchery/runtime-backups`. Provider-neutral handoff replacement/clear backups live under `${XDG_STATE_HOME:-~/.local/state}/ratchery/memory-backups/`. A recognized legacy-kit migration also creates a full pre-migration Vault copy outside the Vault.

Use `ratchery vault-rollback <backup-dir>` only after inspecting the manifest. Project config updates also create external file backups under `${XDG_STATE_HOME:-~/.local/state}/ratchery/project-backups/`; their directories are private (`0700`) and their files/manifests are `0600`. Each manifest records only the source path relative to its project.

Do not delete the pre-migration full Vault backup until the installed release has been used successfully on real projects and the restored notes have been inspected.

Handoff backups are plain validated `Handoff.json` files in private timestamped
directories. Inspect the intended backup and project UUID before manually
restoring it; the CLI deliberately has no bulk or automatic handoff restore or
purge. Once a handoff backup is no longer needed, remove its reviewed timestamp
directory according to your own retention policy; it contains the old handoff
verbatim and is never loaded automatically.

## Runtime rollback after a successful upgrade

Each `${XDG_STATE_HOME:-~/.local/state}/ratchery/runtime-backups/<stamp>/`
directory contains a `manifest.json` plus the previous `runtime/`. Inspect both
before restoring anything. The installer automatically restores the previous
Ratchetry runtime when a post-install step fails. During the one-time
pre-rebrand migration, failure removes the incomplete Ratchetry runtime and
repoints `agent-workspace` to the preserved legacy runtime.

There is intentionally no automatic “restore this arbitrary directory” runtime
command: a stale runtime can reintroduce vulnerable sandbox templates. Prefer
reinstalling a verified release. Use a manual restore only during incident
recovery, after checking the backup's manifest and running `doctor-global`.

## Remove legacy private-development files

After both command names report the same Ratchetry version and
`ratchery doctor-global --deep` passes, the following old paths are no longer
read by the primary command:

```text
~/.local/share/agent-workspace/
~/.config/agent-workspace/config.json
~/.local/state/agent-workspace/
```

Inspect them before removal. The state directory can contain backups or
benchmark evidence you may want to retain. Removing those exact reviewed paths
does not remove `~/.local/bin/agent-workspace`; that small compatibility link is
owned by the current 1.x installer.

## Uninstall Ratchetry

Ratchetry has no background daemon or package dependency to remove. Before
uninstalling, inspect and retain any Vault/runtime/project/handoff backups you
need. Then remove only the installed runtime, its two command links, and the
Ratchetry config/state paths under the prefix/XDG roots you actually used.

Initialized repositories and Vault notes are intentionally not removed. Their
managed blocks and hook configuration must be reviewed project by project;
silently deleting them could also delete adjacent human-owned configuration.
