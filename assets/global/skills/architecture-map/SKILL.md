---
name: architecture-map
description: Build or verify a high-level architecture map for a medium or large repository. Use for module boundaries, dependency flow, entry points, integrations, or cross-package impact; do not invoke for routine localized edits.
---

# Architecture Map

1. Read the project profile and existing architecture docs before generating anything new.
2. Map entry points, modules/packages, persistence, external integrations, queues/jobs, and trust boundaries from repository evidence.
3. Prefer existing native code intelligence and manifests.
4. For a large repository and a broad architecture/impact question, prefer a fresh Graphify graph when Graphify is already installed and the graph will reduce broad file reads. For small/localized work, stay native. Build/refresh lazily and never install a watch or commit hook automatically.
5. Distinguish observed architecture from inferred relationships.
6. Do not rewrite architecture docs unless the user asked for documentation changes.
7. Return a compact map plus the exact files/manifests that support each major relationship.
