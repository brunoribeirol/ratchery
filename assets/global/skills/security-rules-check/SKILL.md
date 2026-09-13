---
name: security-rules-check
description: Check a code change against a baseline set of security rule categories (hardcoded credentials, weak crypto, unsafe functions, missing input validation, missing auth checks). Use on a diff or a specific changed file before merge; avoid as a substitute for the full security-scan audit or a real dependency scanner.
---

# Security Rules Check

A lightweight native reimplementation of the Core Rules concept from CoSAI / OASIS Project
CodeGuard -- the same small set of rule categories, checked directly with this project's own
Read/Grep/Bash. This skill does not depend on Project CodeGuard's code, rule engine, or data; it
borrows only the category list as a baseline checklist.

1. Scope the check to the actual diff or the specific file(s) named -- not the whole repository.
   For a repo-wide audit instead, use the security-scan skill.
2. Check each of the five baseline categories against the scoped code:
   - **Hardcoded credentials/secrets** -- literal API keys, passwords, tokens, connection strings
     with embedded credentials.
   - **Weak or misused cryptography** -- deprecated algorithms/modes (MD5/SHA1 for security
     purposes, ECB mode, small key sizes), hand-rolled crypto instead of vetted libraries.
   - **Unsafe functions** -- shell/eval/exec on untrusted input, unsafe deserialization,
     format-string/SQL-string concatenation of untrusted input.
   - **Missing input validation** -- untrusted input (request bodies, query params, file uploads,
     env vars from an external source) used without type/shape/bounds checking before use.
   - **Missing auth checks** -- a new or changed endpoint/handler with no authentication or
     authorization check where sibling endpoints have one.
3. For each category, report either a specific finding (file:line, snippet, why it matches the
   category) or an explicit "checked, none found" -- never skip a category silently.
4. Do not print or log actual secret values found; reference their location and redact the value.
5. Severity-rank findings (block-worthy vs. advisory) rather than treating every match as equal;
   a rule match is evidence to confirm in context, not automatic proof of a vulnerability.
6. This is a fixed baseline sweep, not a full audit -- it does not replace the deeper trust-boundary
   review the security-reviewer agent performs, and it does not implement fixes (hand fixes to the
   security-engineer agent).
7. Return: findings by category and severity, each with file:line evidence and a remediation
   pointer, plus which categories came back clean.
