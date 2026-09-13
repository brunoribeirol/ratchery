# QMD Security Gate

## Why the integration was hardened

QMD 2.6.3 was reported to trust project-local `.qmd/index.yml` configuration too broadly. A cloned repository could provide an `update:` shell command executed by `qmd update`, and project-local configuration could also select external collection paths or custom model URIs without an adequate trust boundary.

Relevant upstream reports:

- https://github.com/tobi/qmd/issues/886
- https://github.com/tobi/qmd/issues/889

The upstream repository now documents trust gating on current main, but the last stable changelog entry observed when this baseline was cut was 2.6.3. Therefore Ratchetry chooses a conservative policy.

## Policy

- QMD is never auto-installed or auto-updated.
- QMD <=2.6.3 is blocked by Ratchetry integration.
- An unparseable QMD version is also blocked.
- Use a verified stable release newer than 2.6.3 containing the project-local trust fixes.
- Ratchetry always uses the dedicated named index `ratchery-vault`.
- QMD commands launched by Ratchetry run with `$HOME` as cwd, not from arbitrary repositories.
- Setup and reindex remain explicit `--apply` actions.
- If QMD is unavailable/blocked, `vault-search` falls back to lightweight lexical search.

This design makes QMD an optional accelerator rather than a dependency or security boundary.
