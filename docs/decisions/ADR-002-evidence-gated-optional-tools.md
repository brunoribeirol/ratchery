# ADR-002: Gate optional tools on local evidence

- Status: accepted
- Date: 2026-09-07

## Context

Semantic code retrieval, document indexes, output compressors, graphs, MCP
servers, scanners, and memory services can reduce work in one context while
adding schemas, processes, dependencies, permissions, and attack surface in
another. Upstream benchmark claims are not directly comparable and frequently
measure only one portion of total session cost.

## Options considered

- Enable every promising tool in the default setup.
- Select one permanent universal stack from upstream benchmarks.
- Keep the stdlib core complete, route optional capabilities by profile/task,
  and require local cost-per-successful-task evidence before promotion.

## Decision

No external optimizer, retrieval engine, MCP server, scanner, or automatic
memory service is enabled or installed by default. Tools are classified as
profile, on-demand, experimental, or disabled. Native search/raw output and
lexical Vault retrieval remain fallbacks. Promotion requires repeatable local
benchmark evidence with the same repository, commit, task set, model, client,
permissions, and environment.

## Rationale

This minimizes baseline tokens, dependency drift, tool-choice ambiguity, and
supply-chain exposure. Aggregate ccusage evidence and task-success counts make
the decision falsifiable instead of relying on marketing percentages.

## Trade-offs

- Users must explicitly install and enable optional tools.
- The best tool may differ by repository size and task type.
- Maintaining the benchmark harness adds some code and documentation.

## Consequences

- `tools.lock.json` is advisory and never an auto-installer.
- Tool discovery must not execute discovered binaries unless the user requests
  a probe.
- Overlapping tools compete in experiments instead of accumulating in the
  always-on context.

## Reversal conditions

A tool may enter the default only after multiple representative projects show
a material improvement in cost per successful task without weakening security
or reliability.
