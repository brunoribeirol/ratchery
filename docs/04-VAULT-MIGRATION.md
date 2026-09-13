# Vault Migration

The Vault migration is conservative. Recognized legacy kit artifacts are backed up externally before replacement. User project content, TCC, academic notes, PDFs/DOCX, `.obsidian`, and unrecognized notes are preserved.

`VAULT-INDEX.md` uses a managed activity block. Human text outside it survives refresh. `vault-fix-yaml` only quotes the narrow frontmatter scalar pattern it reports and creates another backup before `--apply`.
