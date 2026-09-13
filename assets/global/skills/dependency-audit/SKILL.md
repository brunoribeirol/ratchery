---
name: dependency-audit
description: Audit project dependencies, lockfiles, version drift, and supply-chain risk. Use when adding or upgrading packages, preparing a release, or investigating dependency vulnerabilities; avoid speculative mass upgrades.
---

# Dependency Audit

1. Detect the package manager from committed manifests and lockfiles. Never replace it without explicit approval.
2. Inspect direct dependencies first, then transitive findings only when they affect the project.
3. Prefer the package manager's native audit/update inspection commands.
4. Distinguish vulnerable, outdated, deprecated, and merely newer versions.
5. Do not upgrade everything. Propose the smallest compatible remediation set.
6. Flag packages installed from Git branches, unpinned URLs, local paths, or install scripts as higher supply-chain risk.
7. Record commands actually run and separate confirmed findings from advisory recommendations.
