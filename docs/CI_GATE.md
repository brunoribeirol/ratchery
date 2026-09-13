# CI gate: enforcing `doctor` on pull requests

`.agents/state/tier.json` and friends are git-committed, so a project's
recorded tier and its risk ratchet are already shared across a team via the
repository. But nothing stops a pull request from merging without an agent
ever having run `ratchery doctor` in a live session — compliance was,
until now, voluntary. This repository ships a reusable composite GitHub
Action (`action.yml`) that closes that gap: it runs `ratchery doctor`
as an explicit CI step and fails the run on any error.

## Usage (downstream project)

```yaml
# .github/workflows/doctor.yml
name: ratchery doctor
on:
  pull_request:
    branches: [main]

jobs:
  doctor:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: brunoribeirol/ratchery@v1
        with:
          path: .
          deep: "true"
```

No install step, no dependency beyond Python 3.11+ — the action runs its own
bundled `lib/agent_workspace.py` directly (stdlib-only), it does not require
`ratchery` to be installed on the runner.

## Inputs

| Input | Default | Meaning |
|---|---|---|
| `path` | `.` | Existing project directory relative to `GITHUB_WORKSPACE`; absolute paths and paths/symlinks that escape the checkout are rejected. |
| `deep` | `true` | Also run `doctor`'s slower security probe (spawns the PreToolUse hook against a synthetic denied command). Only `"true"`/`"false"` are accepted; set `"false"` to skip it on tight CI budgets. |

## Outputs

| Output | Meaning |
|---|---|
| `doctor-result` | The raw JSON `ratchery doctor --json` printed: `{"errors": [...], "warnings": [...], "tier": "...", "tier_name": "...", "commit": "...", "dirty": false}`. Use it in a later step (e.g. to post a PR comment) via `${{ steps.<id>.outputs.doctor-result }}` if you give the action step an `id`. |

### Provenance fields

`commit` and `dirty` say **which tree** the verdict describes. A stored result
without them records that a checkout was healthy but never which checkout, so it
cannot be re-checked later against the exact revision that produced it. `commit`
is the resolved `HEAD` (null outside a Git repository or on a checkout without
one) and `dirty` is true when the worktree had uncommitted changes while
`doctor` ran. Neither field ever fails the gate on its own: unlike `benchmark
capture`, which refuses to measure an unclean tree, `doctor` must stay runnable
in a dirty tree, on a shallow checkout, and outside Git entirely.

## What a failing gate means

The job fails with the same errors `ratchery doctor --deep` would
print locally — missing managed files, a disabled sandbox setting, a tier
requirement not met, and so on. Fix it the same way you would in a live
session: run `ratchery doctor --deep` (without `--json`) locally for
the human-readable version, then `ratchery refresh` if the fix is
"reinstall the managed files this project is missing."

## What this gate deliberately does not do

- It does not run `ratchery tier`. `tier` recomputes and *writes*
  tier state and can install new agent files as a side effect — not the
  right primitive for a read-only CI check. Recompute tier locally
  (`ratchery tier`) and commit the result the same way you would any
  other reviewed change to `.agents/state/`.
- It does not auto-fix anything. Consistent with the rest of this project's
  "never destroy or silently change without an explicit action" policy, the
  gate only reports.
