---
name: structural-search
description: Find syntax-aware code patterns that text search cannot identify reliably. Use for API migrations, call-shape discovery, import patterns, or repetitive refactors; prefer native search for simple string lookup.
---

# Structural Search

1. Confirm that syntax-aware matching is actually needed.
2. If `ast-grep` or `sg` is installed, inspect its help/version and use read-only search first.
3. Scope searches to the relevant language and directories.
4. Show representative matches before proposing automated rewrites.
5. Never execute a repository-wide rewrite merely because a pattern matched.
6. Fall back to native search when the installed tool does not support the language or pattern safely.
7. Report the pattern, match count, representative files, and any false-positive risk.
