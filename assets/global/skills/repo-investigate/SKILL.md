---
name: repo-investigate
description: Investigate an unfamiliar or multi-file repository problem with bounded context. Use when the relevant implementation path, callers, ownership, or failure source is not yet known; avoid for obvious single-file edits.
---

# Repository Investigation

Keep the main context clean and make evidence earn every additional file read.

1. Read the nearest `AGENTS.md`, project profile, and only task-relevant documentation.
2. Start with native file search and code intelligence.
3. Use structural search when textual search is ambiguous and `ast-grep`/`sg` is available.
4. Use Serena only when configured and symbol/reference navigation is materially better than native capabilities.
5. For a genuinely large repository, prefer Graphify only when the question is architecture-wide or impact-wide and a graph is likely to reduce broad reads; reuse a fresh graph and build/refresh lazily.
6. Bound exploration. Identify candidate files first, then read the smallest coherent set.
7. Delegate a noisy read-only investigation to the explorer subagent only when it will isolate substantial output or independent work.
8. Return relevant files, call/data flow, evidence, uncertainties, and the smallest next action.
