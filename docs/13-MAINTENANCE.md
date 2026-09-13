# Maintenance

Normal maintenance is intentionally small:

```bash
ratchery doctor-global --deep
ratchery tools-status
ratchery memory status --path .
```

The default status command only discovers executable paths. Run
`ratchery tools-status --probe` when you intentionally want installed
version and QMD security/configuration probes.

Per repository, run `refresh` only after meaningful structure/stack changes. Run `vault-refresh` after adding durable global notes if you want the dashboard immediately updated.

`memory status` is read-only. It validates the repository/Vault UUID binding and
the pending handoff, if any. A pending handoff is expected only while work is
being transferred; inspect it and clear it explicitly after its facts have been
verified. Handoff JSON stays outside QMD's Markdown index, so no reindex is
needed.

QMD maintenance is explicit and available only when the installed QMD version passes the security gate. Never run raw `qmd update` from an untrusted repository as part of Ratchetry maintenance.

Do not chase tool releases. Review an Ratchetry update only for upstream breaking changes, security, migration bugs, or measurable workflow value.
