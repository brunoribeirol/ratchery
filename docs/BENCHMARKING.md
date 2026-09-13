# Cost and Token Benchmarking

Ratchetry does not adopt a token optimizer because its README reports a large
percentage. It measures the outcome on your repository and asks the business
question that matters: **what did one successful task cost?**

The benchmark feature is stdlib-only. It uses an independently installed
[ccusage](https://github.com/ccusage/ccusage) command as a local data source;
Ratchetry never installs it, starts an agent, or spends model tokens for you.

## What is measured

Each snapshot contains only:

- input, output, cache-creation, cache-read, and total tokens;
- ccusage's estimated USD cost;
- attempted and successful task counts supplied by the user;
- success rate and cost per successful task;
- source, a SHA-256 fingerprint of any project filter, date-selection metadata,
  and the ccusage version;
- full Git commit plus non-sensitive task-set, model, client-version,
  environment, and arm-configuration identifiers supplied on capture; and
- a SHA-256 configuration digest derived automatically from the repository's
  agent instructions, client settings/hooks, active agent/Skill/rule files,
  selected tier/profile state, runtime tool catalog, and captured runtime facts.

It does **not** store prompts, responses, raw ccusage rows, session IDs, model
breakdowns, project labels, repository paths, or source code. Snapshots live
under `${XDG_STATE_HOME:-~/.local/state}/ratchery/benchmarks/`, outside
the repository and normal agent context. A namespace made from the project's
UUID and canonical-path fingerprint separates clones and prevents a copied
public UUID from selecting another checkout's evidence.
Relative `XDG_STATE_HOME` values are ignored as invalid XDG configuration. A
resolved state path inside the inspected repository, including one reached
through a symlink, is rejected.

The five user-supplied identifiers are durable evidence labels, not free-form
notes. Use non-secret IDs only; whitespace and path separators are rejected so
a local username, home path, or secret-bearing command cannot be persisted by
accident.

Snapshot schema v2 stores only the final configuration digest, never the files
used to derive it. Collection is bounded, refuses symlinked/special/oversized
configuration, excludes volatile prompt-derived task policy, and never executes
an optional tool. Repeated samples in the same arm must have one identical
digest; baseline and candidate digests may differ because the candidate policy
is the variable being tested. The digest is not a machine attestation: it does
not cover arbitrary environment variables, OS packages, global client files,
or external binary contents. Keep `--environment-id`, client/configuration
versions, and the clean experimental host under human control. Schema v1
snapshots are intentionally rejected instead of being mixed with this stronger
provenance contract.

## Inspect usage without creating a snapshot

```bash
# All sources supported by your installed ccusage release
ratchery usage --period daily --since 20260901 --until 20260907 --offline

# One current ccusage source; JSON stdout contains only ccusage's own output
ratchery usage --source codex --period daily \
  --since 20260901 --until 20260907 --project my-project --json --offline

# One exact session (the ID is passed to ccusage and is not stored by Ratchetry)
ratchery usage --source claude --period session \
  --session-id SESSION_ID --json --offline
```

`--offline` prevents pricing-refresh network access and uses cached pricing.
Costs are estimates, not invoices. An older Claude-only ccusage release may
reject source namespaces such as `codex`; Ratchetry returns that failure rather
than silently dropping the source. Upgrade ccusage explicitly after reviewing
its current release if you need unified source support.

## Read-only budget and spike warnings

`budget check` evaluates the same local aggregate data without storing a
snapshot. It always passes `--offline` to ccusage and never starts, stops, or
intercepts an agent:

```bash
# Today's estimate; reports a warning but exits 0 by default
ratchery budget check --source codex \
  --max-cost-usd 5 --max-tokens 200000

# One known session; warn if it is more than 10x a typical 20k-token session
ratchery budget check --period session --source claude \
  --session-id SESSION_ID --spike-baseline-tokens 20000 \
  --spike-multiplier 10 --json

# Opt into a policy exit for a local script or CI job
ratchery budget check --source codex --max-cost-usd 5 --enforce
```

Without `--enforce`, a crossed threshold is advisory and the command exits 0.
With `--enforce`, any limit or spike warning exits 3. Invalid arguments exit 2;
ccusage or I/O failures exit 1. This is post-usage observability based on
ccusage estimates, not an invoice, daemon, live token counter, or guarantee
that future spend will be blocked.

## Reproducible A/B protocol

The bundled `core-suite-v1` is an inspectable contract, not a magic runner. It
contains six client-neutral prompts, public fixtures, success criteria, a reset
rule, and a minimum of three complete trials per arm. These commands cost no
model tokens:

```bash
ratchery benchmark suites
ratchery benchmark show core-suite-v1
ratchery benchmark validate core-suite-v1
```

`benchmark validate PATH.json` can validate a local experimental task set, but
`capture --task-set core-suite-v1` records the bundled suite ID together with
its SHA-256 digest. A changed official definition therefore cannot be compared
silently with older evidence carrying the same friendly name.

For every candidate tool or policy:

1. Check out the same repository commit and use the same model, prompt,
   permissions, environment, and clean starting state.
2. Run all six tasks from `core-suite-v1` without the candidate. Start each
   task from a fresh checkout/worktree at the recorded commit (not a loose
   fixture directory, because success checks use Git) and record whether it
   actually succeeded; a command exiting zero is not automatically task success.
3. Capture each session while that same commit is still checked out and clean,
   then start a fresh session and repeat with the candidate.
4. Run at least three complete trials per arm. Do not mix unrelated work into
   either measurement.
5. Compare quality first, then cost, tokens, latency, tool calls, and operational
   complexity. Ratchetry currently stores the first four token categories, cost,
   and task success; record latency/tool-call observations in your experiment
   notes without putting raw sessions into durable memory.

For precise trials, capture one exact session per arm:

```bash
ratchery benchmark capture baseline-1 \
  --source codex --session-id BASELINE_SESSION_ID \
  --task-set core-suite-v1 --model MODEL_ID \
  --client-version codex-VERSION --environment-id ENVIRONMENT_ID \
  --configuration native \
  --attempted-tasks 6 --successful-tasks 6

ratchery benchmark capture rtk-1 \
  --source codex --session-id CANDIDATE_SESSION_ID \
  --task-set core-suite-v1 --model MODEL_ID \
  --client-version codex-VERSION --environment-id ENVIRONMENT_ID \
  --configuration rtk-v0.48.0 \
  --attempted-tasks 6 --successful-tasks 6

# Repeat with fresh sessions as baseline-2/-3 and rtk-2/-3, then:
ratchery benchmark report \
  --baseline baseline-1 --baseline baseline-2 --baseline baseline-3 \
  --candidate rtk-1 --candidate rtk-2 --candidate rtk-3
```

The session IDs are used for the local ccusage call but omitted from both
snapshots. `--source` is required with `--session-id` so an upgraded multi-source
ccusage cannot select an ambiguous session namespace.

For a batch isolated by project and date, use windows instead:

```bash
ratchery benchmark capture baseline-week \
  --source claude --project my-project \
  --since 20260901 --until 20260903 \
  --task-set core-suite-v1 --model MODEL_ID \
  --client-version claude-VERSION --environment-id ENVIRONMENT_ID \
  --configuration native \
  --attempted-tasks 6 --successful-tasks 6

ratchery benchmark capture candidate-week \
  --source claude --project my-project \
  --since 20260904 --until 20260906 \
  --task-set core-suite-v1 --model MODEL_ID \
  --client-version claude-VERSION --environment-id ENVIRONMENT_ID \
  --configuration rtk-v0.48.0 \
  --attempted-tasks 6 --successful-tasks 5
```

Use a date window only when those days contain no unrelated work for that
source/project and you can truthfully associate the supplied labels with the
historical runs. Otherwise the result is not causal evidence about the tool.
Capture also requires a valid `HEAD` and a clean worktree; ignored local files
do not affect this check. The recorded commit proves capture-time repository
state, not which commit produced a historical ccusage row. It is not an
attestation: keep the experiment checkout unchanged until capture, or record
the historical protocol separately.

Capture refuses to overwrite a name. `--replace` is explicit because silently
replacing a baseline destroys evidence. Snapshot names accept only letters,
digits, `.`, `_`, and `-`; the storage directory and files must not be symlinks.
The final create is exclusive, so a concurrently created snapshot is not
overwritten after the earlier existence check.

## Reading the comparison

Negative token/cost deltas mean the candidate used less. A zero baseline yields
`n/a`/`null` rather than an invented percentage. Different source, project,
period, selection method, offline posture, ccusage version, attempted-task
count, date-window duration, Git commit, task set, model, client version, or
environment ID is rejected as an incompatible comparison. The configuration ID
is expected to differ: it names the baseline and candidate arms.

`benchmark compare` remains useful for inspecting one compatible pair, but it
never promotes a tool. `benchmark report` additionally requires repeated names,
rejects mixed configurations, reports median/minimum/maximum values, enforces a
configurable success floor, and produces one of
`insufficient-samples`, `quality-regression`, `no-measured-savings`, or
`manual-review-candidate`. Its machine-readable
`automated_adoption_decision` is always `false`.

The report also rejects a configuration-digest change among repeated samples
inside either arm and exposes both arm digests for audit. It does not require
the baseline digest to equal the candidate digest.

A candidate that is cheaper but lowers task success is not an optimization, and
a small successful sample does not prove a universal default. Even
`manual-review-candidate` means a human must weigh latency, permissions,
dependencies, network, maintenance, and repeated project-specific evidence; it
does not mean `KEEP` or automatic activation.

## Recommended experiment order

Start with the least infrastructure:

1. native baseline;
2. RTK **or** Context Mode for verbose-output workloads;
3. Serena versus native search for medium/large symbol-navigation tasks;
4. QMD versus lexical retrieval for documentation-heavy projects;
5. combinations only after individual wins are demonstrated.

Do not activate RTK, Context Mode, Serena, QMD, Graphify, and multiple graph
engines together. Their schemas, hooks, processes, and tool-choice ambiguity can
cost more than they save. The machine-readable activation/network/benchmark
policy for each candidate lives in `tools.lock.json`; the human policy is in
[`TOOL_POLICY.md`](TOOL_POLICY.md).

## Security scanner profiles

Scanners optimize risk, not token count. Run them at explicit boundaries rather
than on every agent tool call:

| Profile | Start with | Add only when justified |
|---|---|---|
| General/public release | Gitleaks plus Ratchetry's existing CI/SBOM checks | Trivy for a consolidated repository/container scan |
| Application T2/T3 | Gitleaks, relevant tests, security review | Semgrep with reviewed rules |
| DevOps/Cloud/IaC | Gitleaks, Trivy | Checkov when its focused IaC findings add value |
| Supply chain/container | Existing SPDX release SBOM, Trivy | Syft/Grype or OSV-Scanner only for required formats or incremental findings |
| MCP-heavy | native sandbox, least privilege, static pinned definitions | Agent Scan/gateway only after reviewing data flow, credentials, commands, and network |

None is auto-installed. Avoid duplicating scanners that report the same result;
compare incremental findings, false positives, download/database cost, and
latency before making a profile mandatory.
