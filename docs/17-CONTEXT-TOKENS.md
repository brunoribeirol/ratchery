# Context and Token Efficiency

The setup optimizes by **not loading** irrelevant material, not by stacking compression tools into every session.

## Main avoidable costs
Long sessions, broad file reads, verbose tool output, giant always-on instruction files, unnecessary MCP/tool definitions, repeated architecture rediscovery, and copying raw logs/transcripts into memory.

## Strategy
- small shared AGENTS/CLAUDE contracts;
- path-scoped rules;
- progressive-disclosure Skills;
- bounded initial reads from project profile;
- native search/code intelligence first;
- ast-grep for structural patterns when useful;
- Graphify only for architecture-wide questions where a graph reduces broad reads;
- QMD snippets only after a safe version is explicitly configured;
- subagents for noisy bounded investigations only;
- one measured output optimizer only for known verbose workloads, with raw fallback;
- ccusage offline aggregates for measurement, never vendor percentages as evidence.

## Session hygiene
Continue the same session for the same objective. Use `workspace-save` at meaningful boundaries. Start a fresh session for an unrelated objective. Avoid full-repository reads unless architecture-wide evidence is actually required.

## Measurement
Do not promise fixed token-reduction percentages. The primary metric is **cost
per successful task**, not raw tokens alone: a compressor that hides the error
and forces another run can be more expensive even when its first output is
smaller.

Use `ratchery benchmark capture` on exact sessions when possible, then
`benchmark compare`. Snapshots retain aggregate token/cost/task counts only and
live outside the repository in local XDG state. Capture requires a clean Git
worktree and records non-sensitive commit, model, client, task-set, environment,
and arm-configuration IDs. Run the same prompt and starting state several times
before promoting an experimental tool. Full protocol: `BENCHMARKING.md`.
