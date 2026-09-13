# References

Primary upstream references for the current stable baseline. Per-tool review
dates and recheck deadlines live in `tools.lock.json` rather than in this page.

## Claude Code
- Documentation: https://code.claude.com/docs/
- Hooks: https://code.claude.com/docs/en/hooks
- Sandboxing: https://code.claude.com/docs/en/sandboxing
- Subagents: https://code.claude.com/docs/en/sub-agents
- Skills: https://code.claude.com/docs/en/skills

## OpenAI Codex
- Documentation: https://developers.openai.com/codex/
- Changelog: https://developers.openai.com/codex/changelog
- AGENTS.md: https://developers.openai.com/codex/agent-configuration/agents-md
- Hooks: https://developers.openai.com/codex/hooks
- Skills: https://developers.openai.com/codex/build-skills
- Subagents: https://developers.openai.com/codex/subagents

Codex CLI 0.149.0 (2026-08-20) expanded `codex doctor`; Ratchetry deep diagnostics use it when available rather than duplicating every native check.

## Optional tools
- QMD: https://github.com/tobi/qmd
- QMD trust issue #886: https://github.com/tobi/qmd/issues/886
- QMD trust issue #889: https://github.com/tobi/qmd/issues/889
- Serena: https://github.com/oraios/serena
- Graphify: https://github.com/Graphify-Labs/graphify
- ast-grep: https://github.com/ast-grep/ast-grep
- Gitleaks: https://github.com/gitleaks/gitleaks
- RTK: https://github.com/rtk-ai/rtk
- ccusage: https://github.com/ccusage/ccusage
- Trivy: https://github.com/aquasecurity/trivy
- Semgrep: https://github.com/semgrep/semgrep
- Checkov: https://github.com/bridgecrewio/checkov
- OSV-Scanner: https://github.com/google/osv-scanner
- Syft: https://github.com/anchore/syft
- Grype: https://github.com/anchore/grype
- Context Mode: https://github.com/mksglu/context-mode
- Snyk Agent Scan: https://github.com/snyk/agent-scan
- ai-memory: https://github.com/akitaonrails/ai-memory
- Greenlight (handoff/provenance design input, not a dependency): https://github.com/lucasrosati/greenlight

Optional tool versions are informational except security gates. Ratchetry should not require a new release merely because an optional tool changed.
