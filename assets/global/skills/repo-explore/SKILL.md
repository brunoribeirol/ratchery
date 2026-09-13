---
name: repo-explore
description: Orient in a large, unfamiliar repository by locating code via file:line references instead of reading whole files. Use as a bounded, read-only first pass before touching an unfamiliar codebase or subsystem; avoid when the relevant file(s) are already known.
---

# Repository Exploration

This is a native reimplementation of the "caveman explore" pattern flagged for revival in the
project's decision review -- a bounded, read-only, evidence-by-reference approach to orientation.
It does not depend on the `caveman` package or any external tool; it is a discipline applied with
this project's own Read/Grep/Glob/Bash. No token-savings figures are claimed here: cite the pattern,
not a percentage.

1. State the specific question this exploration must answer before searching (e.g. "where is X
   validated", "what calls Y", "how is Z configured"). Do not explore without a target question.
2. Search first, read second. Use Grep/Glob (or the structural-search skill, when pattern-based
   matching is needed) to find candidate locations before opening any file.
3. Return evidence as `path:line` references with a one-line quote or paraphrase of what's there --
   not full file contents. Only read a full file when a reference alone can't answer the question.
4. Keep the read set to the smallest number of files that answers the question. Prefer 5-10 sharp
   references over a handful of full-file reads.
5. Stay read-only. This skill locates and cites code; it does not evaluate correctness (use
   focused-review), assess security (use security-scan or security-rules-check), or edit anything.
6. If the question turns out to require architecture-wide or impact-wide reasoning across many
   files, hand off to the repo-investigate skill (which may in turn reach for Graphify) rather than
   expanding this pass file by file.
7. Return: the original question, the file:line evidence map, and any uncertainty or dead end
   worth flagging -- not a narrative walkthrough of everything that was searched.
