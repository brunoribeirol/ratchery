#!/usr/bin/env bash
set -euo pipefail

PKG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# mktemp -d can fail (denied write, full disk, read-only TMPDIR...). If it
# does, `$(mktemp -d)` is an empty string, and `cd ""` is a bash no-op that
# returns success and leaves PWD unchanged -- `set -e` never sees a failure.
# TMP would then silently become the caller's cwd (this repo, when run from
# its root), and the EXIT trap below would `rm -rf` it. Fail loudly instead.
RAW_TMP="$(mktemp -d)" || { echo "run-tests.sh: mktemp -d failed" >&2; exit 1; }
[[ -n "$RAW_TMP" && -d "$RAW_TMP" ]] || { echo "run-tests.sh: mktemp -d returned no usable directory" >&2; exit 1; }
# Resolve to the real (non-symlinked) path: on macOS, mktemp -d returns a
# path under /var, which is itself a symlink to /private/var. Subprocess
# $PWD/cwd values report the resolved path, so comparing against the
# unresolved $TMP would spuriously fail every "ran from $HOME" assertion.
TMP="$(cd "$RAW_TMP" && pwd -P)"
# Extra guard: never let the trap rm -rf anything outside the real system
# temp directory, no matter how TMP was computed above.
case "$TMP" in
  /tmp/*|/private/tmp/*|/var/folders/*|/private/var/folders/*) ;;
  *) echo "run-tests.sh: refusing to use suspicious TMP='$TMP' (expected a system temp dir)" >&2; exit 1 ;;
esac
trap 'rm -rf "$TMP"' EXIT

export HOME="$TMP/home"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_STATE_HOME="$HOME/.local/state"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
mkdir -p "$HOME"

VAULT="$TMP/vault"
PROJECTS="$TMP/Projects"
mkdir -p "$VAULT"/{projects,session-logs,decisions,bugs-solved,commands,references,graphify,templates,tcc,academic,career,Clippings,.obsidian}

# Legacy Vault fixture.
cat > "$VAULT/README.md" <<'MD'
# Vault Agent Memory Kit v1.0
MD
cat > "$VAULT/install.sh" <<'SH2'
#!/usr/bin/env bash
BACKUP=".vault-agent-kit-backups"
echo "Vault agent memory kit installed"
SH2
chmod +x "$VAULT/install.sh"
cat > "$VAULT/AGENTS.md" <<'MD'
# Vault Operating Contract
Detailed multi-step workflows belong in Skills.
MD
cat > "$VAULT/CLAUDE.md" <<'MD'
@AGENTS.md
# Claude Code Vault Adapter
MD
cat > "$VAULT/VAULT-INDEX.md" <<'MD'
# Vault Index
<!-- vault-agent-kit:active-projects:start -->
<!-- vault-agent-kit:active-projects:end -->
<!-- vault-agent-kit:section:start -->
<!-- vault-agent-kit:section:end -->
MD
cat > "$VAULT/templates/README.md" <<'MD'
# Vault templates
project-note.md
MD
cat > "$VAULT/templates/project-home.md" <<'MD'
<!-- vault-agent-kit:current-state:start -->
MD
cat > "$VAULT/templates/project-note.md" <<'MD'
[[{{project_home_link}}]]
MD
cat > "$VAULT/templates/session-log.md" <<'MD'
# {{session_title}}
## Unresolved risks
MD
cat > "$VAULT/templates/bug.md" <<'MD'
# Bug: {{title}}
## Reusable lesson
MD
cat > "$VAULT/templates/decision.md" <<'MD'
# Decision: {{title}}
## Review trigger
MD
cat > "$VAULT/templates/command.md" <<'MD'
# Command: {{title}}
## Variations
MD
cat > "$VAULT/templates/reference.md" <<'MD'
# {{title}}
## Reliability and limitations
MD
: > "$VAULT/related-note.md"
: > "$VAULT/.DS_Store"
cat > "$VAULT/tcc/invalid.md" <<'MD'
---
title: Session: invalid example
status: active
---

# Example
MD
cat > "$VAULT/projects/existing.md" <<'MD'
# Existing project content
MD

# Dry run must be read-only.
before_hash="$(find "$VAULT" -type f -print0 | sort -z | xargs -0 shasum | shasum | awk '{print $1}')"
bash "$PKG/install.sh" \
  --prefix "$HOME/.local" \
  --vault "$VAULT" \
  --projects-root "$PROJECTS" \
  --project-layout categorized \
  --vault-migration safe \
  --external-tools none \
  --dry-run >/dev/null
after_hash="$(find "$VAULT" -type f -print0 | sort -z | xargs -0 shasum | shasum | awk '{print $1}')"
[[ "$before_hash" == "$after_hash" ]]

# A legacy runtime path controlled through a symlink must never be trusted as
# an upgrade source. Prove the installer rejects it before constructing the
# valid legacy fixture used by the migration test below.
mkdir -p "$HOME/.local/share" "$TMP/untrusted-runtime"
ln -s "$TMP/untrusted-runtime" "$HOME/.local/share/agent-workspace"
if bash "$PKG/install.sh" \
  --prefix "$HOME/.local" \
  --vault "$VAULT" \
  --projects-root "$PROJECTS" \
  --project-layout categorized \
  --vault-migration safe \
  --external-tools none \
  --dry-run >"$TMP/symlinked-legacy-runtime" 2>&1; then
  echo "installer accepted a symlinked legacy runtime" >&2
  exit 1
fi
grep -q 'Refusing a symlinked runtime target or legacy runtime' "$TMP/symlinked-legacy-runtime"
rm "$HOME/.local/share/agent-workspace"

# Simulate the last private-development install. The Ratchetry installer must
# back it up, preserve its files, migrate config into the new namespace, and
# point both command names at one new runtime.
mkdir -p "$HOME/.local/share/agent-workspace/bin" "$HOME/.config/agent-workspace"
printf '{"version":"1.0.1"}\n' > "$HOME/.local/share/agent-workspace/MANIFEST.json"
cat > "$HOME/.local/share/agent-workspace/bin/agent-workspace" <<'SH'
#!/usr/bin/env bash
printf '%s\n' 1.0.1
SH
chmod +x "$HOME/.local/share/agent-workspace/bin/agent-workspace"
printf '{"version":"1.0.1","vault_path":"%s","projects_root":"%s","project_layout":"categorized","external_tools":"none"}\n' \
  "$VAULT" "$PROJECTS" > "$HOME/.config/agent-workspace/config.json"

# Clean branded install over the recognized legacy state.
bash "$PKG/install.sh" \
  --prefix "$HOME/.local" \
  --vault "$VAULT" \
  --projects-root "$PROJECTS" \
  --project-layout categorized \
  --vault-migration safe \
  --external-tools none \
  --yes >/dev/null
INSTALLED_RUNTIME="$HOME/.local/share/ratchery"
[[ ! -e "$INSTALLED_RUNTIME/.git" ]]
[[ ! -e "$INSTALLED_RUNTIME/.github" ]]
python3 "$INSTALLED_RUNTIME/scripts/verify-manifest.py" "$INSTALLED_RUNTIME" >/dev/null

EXPECTED_VERSION="$(python3 "$PKG/scripts/verify-manifest.py" "$PKG" --print-version)"
[[ "$(ratchery --version)" == "$EXPECTED_VERSION" ]]
[[ "$(agent-workspace --version)" == "$EXPECTED_VERSION" ]]
[[ -f "$HOME/.config/ratchery/config.json" ]]
[[ -f "$HOME/.config/agent-workspace/config.json" ]]
[[ -d "$HOME/.local/share/agent-workspace" ]]
legacy_backup_manifest="$(find "$XDG_STATE_HOME/ratchery/runtime-backups" -name manifest.json | head -1)"
[[ -n "$legacy_backup_manifest" ]]
grep -q 'agent-workspace' "$legacy_backup_manifest"
[[ -f "$PROJECTS/README.md" ]]
for category in personal academic learning work experiments archived; do [[ -f "$PROJECTS/$category/README.md" ]]; done
[[ ! -e "$VAULT/README.md" && ! -e "$VAULT/install.sh" && ! -e "$VAULT/related-note.md" && ! -e "$VAULT/.DS_Store" ]]
[[ -f "$VAULT/AGENTS.md" && -f "$VAULT/CLAUDE.md" && -f "$VAULT/VAULT-INDEX.md" ]]
[[ "$(grep -c 'agent-workspace:v8:start' "$VAULT/AGENTS.md")" -eq 1 ]]
[[ "$(grep -c 'agent-workspace:v8:start' "$VAULT/CLAUDE.md")" -eq 1 ]]
[[ "$(grep -c 'agent-workspace:v8:index:start' "$VAULT/VAULT-INDEX.md")" -eq 1 ]]
[[ -f "$VAULT/projects/existing.md" ]]

# Narrow YAML repair.
ratchery vault-fix-yaml | grep -q '1 file(s)'
ratchery vault-fix-yaml --apply >/dev/null
grep -q '^title: "Session: invalid example"$' "$VAULT/tcc/invalid.md"
ratchery vault-doctor >/dev/null

# Create a project and validate the current scaffold.
ratchery new tiny --category personal >/dev/null
P="$PROJECTS/personal/tiny"
ratchery tier-set --path "$P" >/dev/null
[[ -d "$P/.git" ]]
[[ -f "$P/AGENTS.md" && -f "$P/CLAUDE.md" ]]
[[ -f "$P/.codex/config.toml" && -f "$P/.codex/hooks.json" && -f "$P/.claude/settings.json" ]]
[[ -f "$P/.agents/state/project-id" && -f "$P/.agents/state/ownership.json" ]]
[[ -f "$VAULT/projects/tiny/Home.md" ]]
grep -q '^permissionMode: plan$' "$P/.claude/agents/explorer.md"
grep -q '^permissionMode: plan$' "$P/.claude/agents/reviewer.md"
grep -q '^permissionMode: plan$' "$P/.claude/agents/security-reviewer.md"
! grep -q '^permissionMode: plan$' "$P/.claude/agents/test-runner.md"

grep -q 'agent-workspace:v8:commands:start' "$P/docs/COMMANDS.md"
cat >> "$P/docs/COMMANDS.md" <<'MD'

## Human note
DO-NOT-DELETE-ME
MD
ratchery refresh --path "$P" >/dev/null
grep -q 'DO-NOT-DELETE-ME' "$P/docs/COMMANDS.md"
[[ "$(grep -c 'agent-workspace:v8:commands:start' "$P/docs/COMMANDS.md")" -eq 1 ]]

# JSON/TOML semantics, sandbox, scrub, timeout. TOML semantic validation
# (tomllib) is stdlib-only from Python 3.11+ -- same documented floor as
# lib/agent_workspace.py's own guard (see docs/INSTALLATION.md), so this whole
# block is 3.11+-only rather than picking apart which assertions need it.
if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
python3 - <<PY
import json,tomllib
from pathlib import Path
p=Path("$P")
claude=json.loads((p/'.claude/settings.json').read_text())
hooks=json.loads((p/'.codex/hooks.json').read_text())
cfg=tomllib.loads((p/'.codex/config.toml').read_text())
assert claude['sandbox']['enabled'] is True
assert claude['sandbox']['failIfUnavailable'] is True
assert claude['sandbox']['allowUnsandboxedCommands'] is False
assert claude['env']['CLAUDE_CODE_SUBPROCESS_ENV_SCRUB']=='1'
assert claude['permissions']['disableBypassPermissionsMode']=='disable'
assert 'mcp__context7__query-docs' in claude['permissions']['ask']
assert 'SessionEnd' not in hooks.get('hooks', {})
assert 'SessionEnd' not in claude.get('hooks', {})
assert cfg['shell_environment_policy']['ignore_default_excludes'] is False
assert '**/.env.*' not in cfg['permissions']['project-edit']['filesystem'][':workspace_roots']
PY
fi

# Hook security + privacy.
printf '{"hook_event_name":"UserPromptSubmit","cwd":"%s","prompt":"fix typo with sk-super-secret"}\n' "$P" | python3 "$P/.agents/runtime/agent_workspace.py" > "$TMP/trivial"
[[ ! -s "$TMP/trivial" ]]
! grep -R -q 'sk-super-secret' "$P/.agents/state"
python3 - <<PY
import json
from pathlib import Path
p=Path("$P/.agents/state/task-policy.json")
d=json.loads(p.read_text())
assert 'prompt' not in d and len(d['prompt_hash'])==24
PY
printf '{"hook_event_name":"PreToolUse","cwd":"%s","tool_name":"Bash","tool_input":{"command":"cat .env"}}\n' "$P" | python3 "$P/.agents/runtime/agent_workspace.py" | grep -q deny
printf '{"hook_event_name":"PreToolUse","cwd":"%s","tool_name":"Bash","tool_input":{"command":"printenv"}}\n' "$P" | python3 "$P/.agents/runtime/agent_workspace.py" | grep -q deny
printf '{"hook_event_name":"PreToolUse","cwd":"%s","tool_name":"Bash","tool_input":{"command":"git reset --hard"}}\n' "$P" | python3 "$P/.agents/runtime/agent_workspace.py" | grep -q deny
printf '{"hook_event_name":"PreToolUse","cwd":"%s","tool_name":"Bash","tool_input":{"command":"cat README.md"}}\n' "$P" | python3 "$P/.agents/runtime/agent_workspace.py" > "$TMP/safe"
[[ ! -s "$TMP/safe" ]]
printf '{"hook_event_name":"PreToolUse","cwd":"%s","tool_name":"Bash","tool_input":{"command":"cat .env.example"}}\n' "$P" | python3 "$P/.agents/runtime/agent_workspace.py" > "$TMP/env-example-safe"
[[ ! -s "$TMP/env-example-safe" ]]
# Regression: `set -eu` is a common, safe shell-hardening idiom and must not
# be flagged as an environment dump; a bare `set` still must be (found via
# independent Codex cross-review, 2026-08-30).
printf '{"hook_event_name":"PreToolUse","cwd":"%s","tool_name":"Bash","tool_input":{"command":"set -euo pipefail"}}\n' "$P" | python3 "$P/.agents/runtime/agent_workspace.py" > "$TMP/set-flags-safe"
[[ ! -s "$TMP/set-flags-safe" ]]
printf '{"hook_event_name":"PreToolUse","cwd":"%s","tool_name":"Bash","tool_input":{"command":"set"}}\n' "$P" | python3 "$P/.agents/runtime/agent_workspace.py" | grep -q deny

# SessionEnd is deliberately not a persistence API. Even a stale/custom hook
# that invokes the runtime must not recreate the removed automatic Vault writer.
mkdir -p "$TMP/session-end-disabled-vault"
printf '{"hook_event_name":"SessionEnd","cwd":"%s","reason":"test"}\n' "$P" \
  | AGENT_WORKSPACE_VAULT="$TMP/session-end-disabled-vault" \
    python3 "$P/.agents/runtime/agent_workspace.py"
! find "$TMP/session-end-disabled-vault" -type f | grep -q .

# Regression: malformed stdin JSON is a known, accepted fail-open failure
# mode -- this hook is a secondary deterministic guard, not the enforcement
# boundary (that's the sandbox config, Layer 1). Confirm it exits cleanly
# and blocks/denies nothing rather than crashing or hanging.
printf 'not valid json{{{' | python3 "$P/.agents/runtime/agent_workspace.py" > "$TMP/malformed-json"
[[ ! -s "$TMP/malformed-json" ]]
printf '' | python3 "$P/.agents/runtime/agent_workspace.py" > "$TMP/empty-stdin"
[[ ! -s "$TMP/empty-stdin" ]]

ratchery doctor --path "$P" --deep >/dev/null

# The active catalog is a doctor invariant and cannot be disabled through the
# convenience command while tier/capability policy still selects it.
if ratchery agents disable reviewer --path "$P" > "$TMP/disable-active" 2>&1; then
  echo "agents disable unexpectedly removed an active baseline agent" >&2
  exit 1
fi
grep -q "Refusing to disable active agent 'reviewer'" "$TMP/disable-active"
[[ -f "$P/.claude/agents/reviewer.md" ]]
[[ -f "$P/.codex/agents/reviewer.toml" ]]

# Explicit on-demand agents remain reversible on both clients.
ratchery agents enable cost-optimizer --path "$P" >/dev/null
[[ -f "$P/.claude/agents/cost-optimizer.md" ]]
[[ -f "$P/.codex/agents/cost_optimizer.toml" ]]
ratchery agents-status --path "$P" | grep -q '\[enabled\] cost-optimizer'
ratchery agents disable cost-optimizer --path "$P" >/dev/null
[[ ! -e "$P/.claude/agents/cost-optimizer.md" ]]
[[ ! -e "$P/.codex/agents/cost_optimizer.toml" ]]

# Regression: doctor must validate Codex config.toml semantics, not just that
# it parses (found via independent Codex cross-review, 2026-08-30). Swapping
# the hardened profile for an unrestricted built-in preset must be caught.
# TOML semantic validation is Python 3.11+-only (tomllib; same documented
# floor as lib/agent_workspace.py -- see docs/INSTALLATION.md), so below that
# doctor can only warn it couldn't check, not report the specific tampered
# value -- nothing to assert there.
cp "$P/.codex/config.toml" "$TMP/config.toml.bak"
sed -i.orig 's/default_permissions = "project-edit"/default_permissions = ":danger-full-access"/' "$P/.codex/config.toml"
tampered_output="$(ratchery doctor --path "$P" --deep 2>&1 || true)"
if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  grep -q "default_permissions is ':danger-full-access'" <<<"$tampered_output"
fi
cp "$TMP/config.toml.bak" "$P/.codex/config.toml"
rm -f "$P/.codex/config.toml.orig"
ratchery doctor --path "$P" --deep >/dev/null

# Regression: an explicit `mcp enable` opt-in must survive `refresh`, not be
# silently wiped by the external_tools=none cleanup on the next run (found
# via independent Codex cross-review, 2026-08-30).
ratchery mcp enable context7 --path "$P" >/dev/null
grep -q '"context7"' "$P/.mcp.json"
grep -q 'agent-workspace:mcp:context7:start' "$P/.codex/config.toml"
grep -q 'default_tools_approval_mode = "prompt"' "$P/.codex/config.toml"
grep -q 'output_token_limit = 6000' "$P/.codex/config.toml"
grep -q '"context7"' "$P/.agents/state/mcp-enabled.json"
ratchery refresh --path "$P" >/dev/null
grep -q '"context7"' "$P/.mcp.json"
grep -q 'agent-workspace:mcp:context7:start' "$P/.codex/config.toml"
ratchery mcp disable context7 --path "$P" >/dev/null
[[ ! -f "$P/.mcp.json" ]] || ! grep -q '"context7"' "$P/.mcp.json"
! grep -q 'agent-workspace:mcp:context7:start' "$P/.codex/config.toml"

# Preserve user hook arrays across refresh.
python3 - <<PY
import json
from pathlib import Path
p=Path("$P/.claude/settings.json")
d=json.loads(p.read_text())
d.setdefault('hooks',{}).setdefault('PreToolUse',[]).append({'matcher':'Bash','hooks':[{'type':'command','command':'echo USER-HOOK'}]})
p.write_text(json.dumps(d,indent=2)+'\n')
p=Path("$P/.codex/hooks.json")
d=json.loads(p.read_text())
d.setdefault('hooks',{}).setdefault('PreToolUse',[]).append({'matcher':'Bash','hooks':[{'type':'command','command':'echo CODEX-USER-HOOK','timeout':1}]})
p.write_text(json.dumps(d,indent=2)+'\n')
PY
ratchery refresh --path "$P" >/dev/null
grep -q 'USER-HOOK' "$P/.claude/settings.json"
grep -q 'CODEX-USER-HOOK' "$P/.codex/hooks.json"

# Refresh removes only legacy Ratchetry-owned SessionEnd groups and preserves user SessionEnd groups.
python3 - <<PY2
import json
from pathlib import Path
p=Path("$P")
for rel in ['.claude/settings.json','.codex/hooks.json']:
    f=p/rel; d=json.loads(f.read_text())
    d.setdefault('hooks',{}).setdefault('SessionEnd',[]).append({'hooks':[{'type':'command','command':'python3 "\$(git rev-parse --show-toplevel)/.agents/runtime/agent_workspace.py"','timeout':3}]})
    d['hooks']['SessionEnd'].append({'hooks':[{'type':'command','command':'echo USER-SESSION-END','timeout':1}]})
    f.write_text(json.dumps(d,indent=2)+'\n')
PY2
ratchery refresh --path "$P" >/dev/null
grep -q 'USER-SESSION-END' "$P/.claude/settings.json"
grep -q 'USER-SESSION-END' "$P/.codex/hooks.json"
python3 - <<PY2
import json
from pathlib import Path
for rel in ['.claude/settings.json','.codex/hooks.json']:
 d=json.loads((Path("$P")/rel).read_text())
 groups=d.get('hooks',{}).get('SessionEnd',[])
 assert len(groups)==1
 assert 'USER-SESSION-END' in json.dumps(groups)
 assert 'agent_workspace.py' not in json.dumps(groups)
PY2

# Conditional skills should appear and disappear with capabilities.
cat > "$P/package.json" <<'JSON'
{"dependencies":{"react":"latest"},"scripts":{"build":"vite build","test":"vitest"}}
JSON
ratchery refresh --path "$P" >/dev/null
[[ -f "$P/.agents/skills/frontend-a11y-review/SKILL.md" ]]
rm "$P/package.json"
ratchery refresh --path "$P" >/dev/null
[[ ! -e "$P/.agents/skills/frontend-a11y-review" ]]

# Vault index is reconciled, preserves human content, and lists recent activity.
# Session logs live per-project (projects/<slug>/session-logs/), not in one
# shared bucket -- see docs/decision-matrix.md.
echo 'HUMAN-VAULT-NOTE' >> "$VAULT/VAULT-INDEX.md"
[[ -d "$VAULT/projects/tiny/session-logs" ]]
printf '# Session One\n' > "$VAULT/projects/tiny/session-logs/2026-01-01.md"
printf '# Decision One\n' > "$VAULT/decisions/decision-one.md"
printf '# Bug One\n' > "$VAULT/bugs-solved/bug-one.md"
ratchery vault-refresh >/dev/null
grep -q 'HUMAN-VAULT-NOTE' "$VAULT/VAULT-INDEX.md"
grep -q 'Recent sessions' "$VAULT/VAULT-INDEX.md"
grep -q 'Session One' "$VAULT/VAULT-INDEX.md"
grep -q 'Decision One' "$VAULT/VAULT-INDEX.md"
grep -q 'Bug One' "$VAULT/VAULT-INDEX.md"
[[ "$(grep -c 'agent-workspace:v8:index:start' "$VAULT/VAULT-INDEX.md")" -eq 1 ]]

# Legacy global session-logs/ bucket never leaks onto the dashboard, and the
# migration command (dry-run by default) correctly matches a legacy log to
# its project by frontmatter and moves it only with --apply.
mkdir -p "$VAULT/session-logs"
printf -- '---\nproject: "tiny"\n---\n\n# Legacy Session\n' > "$VAULT/session-logs/legacy.md"
ratchery vault-refresh >/dev/null
! grep -q 'Legacy Session' "$VAULT/VAULT-INDEX.md"
ratchery vault-migrate-session-logs | grep -q 'Would move: session-logs/legacy.md'
[[ -f "$VAULT/session-logs/legacy.md" ]]
ratchery vault-migrate-session-logs --apply | grep -q 'Moved: session-logs/legacy.md'
[[ ! -f "$VAULT/session-logs/legacy.md" ]]
[[ -f "$VAULT/projects/tiny/session-logs/legacy.md" ]]
ratchery vault-refresh >/dev/null
grep -q 'Legacy Session' "$VAULT/VAULT-INDEX.md"

# Stable project-id and moved repository metadata.
PID="$(cat "$P/.agents/state/project-id")"
MOVED="$PROJECTS/personal/tiny-moved"
mv "$P" "$MOVED"
ratchery refresh --path "$MOVED" >/dev/null
[[ "$(cat "$MOVED/.agents/state/project-id")" == "$PID" ]]
grep -q "$MOVED" "$VAULT/projects/tiny/Home.md"

# Collision-safe Vault slug for another repository with same basename.
mkdir -p "$PROJECTS/experiments/tiny"
git -C "$PROJECTS/experiments/tiny" init -q
ratchery init --path "$PROJECTS/experiments/tiny" >/dev/null
SECOND_ID="$(cat "$PROJECTS/experiments/tiny/.agents/state/project-id")"
[[ "$SECOND_ID" != "$PID" ]]
SECOND_SHORT="${SECOND_ID%%-*}"
[[ -f "$VAULT/projects/tiny-$SECOND_SHORT/Home.md" ]]

# QMD operations are explicit. With no QMD binary, search falls back locally.
{ ratchery vault-qmd-setup 2>&1 || true; } | grep -q 'QMD is not installed'
ratchery vault-search 'Existing project' >/dev/null

# QMD <=2.6.3 is blocked.
cat > "$HOME/.local/bin/qmd" <<'QMDOLD'
#!/usr/bin/env bash
if [[ "${1:-}" == "--version" ]]; then echo 'qmd 2.6.3'; exit 0; fi
echo "SHOULD-NOT-RUN $*" >> "${QMD_TEST_LOG:?}"
exit 0
QMDOLD
chmod +x "$HOME/.local/bin/qmd"
export QMD_TEST_LOG="$TMP/qmd.log"
{ ratchery vault-qmd-setup 2>&1 || true; } | grep -q 'integration disabled'
! grep -q 'SHOULD-NOT-RUN' "$QMD_TEST_LOG" 2>/dev/null || false
ratchery vault-search 'Existing project' >/dev/null
rm -f "$QMD_TEST_LOG"

# A safe-version fake QMD is isolated in a dedicated named index and remains read-only until --apply.
cat > "$HOME/.local/bin/qmd" <<'QMD'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "--version" ]]; then echo 'qmd 2.6.4'; exit 0; fi
printf '%s|cwd=%s\n' "$*" "$PWD" >> "${QMD_TEST_LOG:?}"
case "$*" in
  *"collection list"*) exit 0 ;;
  *"context list"*) exit 0 ;;
  *" status") echo 'fake qmd status'; exit 0 ;;
  *" doctor") echo 'fake qmd doctor'; exit 0 ;;
  *) exit 0 ;;
esac
QMD
chmod +x "$HOME/.local/bin/qmd"
export QMD_TEST_LOG="$TMP/qmd.log"
ratchery vault-qmd-setup > "$TMP/qmd-plan"
grep -q -- '--index ratchery-vault collection add' "$TMP/qmd-plan"
grep -q -- '--index ratchery-vault context add' "$TMP/qmd-plan"
grep -q -- '--index ratchery-vault embed -c vault' "$TMP/qmd-plan"
! grep -q 'collection add' "$QMD_TEST_LOG"
ratchery vault-qmd-status >/dev/null
grep -q "cwd=$HOME" "$QMD_TEST_LOG"
rm -f "$HOME/.local/bin/qmd"
unset QMD_TEST_LOG

# Deep global doctor delegates to native codex doctor when supported.
cat > "$HOME/.local/bin/codex" <<'CODEX'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "--version" ]]; then echo 'codex-cli 0.149.0'; exit 0; fi
if [[ "${1:-}" == "doctor" ]]; then echo 'fake codex doctor ok'; echo doctor >> "${CODEX_DOCTOR_LOG:?}"; exit 0; fi
exit 0
CODEX
chmod +x "$HOME/.local/bin/codex"
export CODEX_DOCTOR_LOG="$TMP/codex-doctor.log"
ratchery doctor-global --deep >/dev/null
grep -q doctor "$CODEX_DOCTOR_LOG"
rm -f "$HOME/.local/bin/codex"
unset CODEX_DOCTOR_LOG

# Reinstall/update must be idempotent and create a runtime backup.
bash "$PKG/install.sh" \
  --prefix "$HOME/.local" \
  --vault "$VAULT" \
  --projects-root "$PROJECTS" \
  --project-layout categorized \
  --vault-migration safe \
  --external-tools none \
  --yes >/dev/null
[[ "$(grep -c 'agent-workspace:v8:start' "$VAULT/AGENTS.md")" -eq 1 ]]
[[ "$(grep -c 'agent-workspace:v8:index:start' "$VAULT/VAULT-INDEX.md")" -eq 1 ]]
find "$XDG_STATE_HOME/ratchery/runtime-backups" -name manifest.json | grep -q .
find "$XDG_STATE_HOME/ratchery/backups" -name manifest.json | grep -q .

# Source/package sanity.
python3 -m py_compile "$PKG/lib/agent_workspace.py" "$PKG/lib/hook_runtime.py"
bash -n "$PKG/install.sh" "$PKG/bin/ratchery" "$PKG/bin/agent-workspace" "$PKG/tests/run-tests.sh"
python3 - <<PY
import json
try:
    import tomllib  # stdlib only from Python 3.11+, same guard as lib/agent_workspace.py
except ImportError:
    tomllib = None
from pathlib import Path
b=Path("$PKG")
json.loads((b/'assets/project/.claude/settings.json').read_text())
json.loads((b/'assets/project/.codex/hooks.json').read_text())
if tomllib:
    tomllib.loads((b/'assets/project/.codex/config.base.toml').read_text())
json.loads((b/'tools.lock.json').read_text())
json.loads((b/'MANIFEST.json').read_text())
PY

# Full MANIFEST.json integrity check (existence, size, sha256, totals) lives
# in scripts/verify-manifest.py so it can also run standalone (make verify,
# CI step) without duplicating the logic here.
python3 "$PKG/scripts/verify-manifest.py" "$PKG"

echo 'All Ratchetry tests passed.'
