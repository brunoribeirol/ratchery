#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${HOME}/.local"
VAULT=""
PROJECTS_ROOT="${HOME}/Projects"
PROJECT_LAYOUT="flat"
TOOLS="none"
MIGRATION="safe"
YES=0
DRY_RUN=0

usage() {
  cat <<'USAGE'
Usage: bash install.sh [options]

Required:
  --vault PATH                    Existing Obsidian vault

Paths:
  --projects-root PATH            Default parent for projects (default: ~/Projects)
  --prefix PATH                   Install prefix (default: ~/.local)

Behavior:
  --project-layout MODE           flat | categorized (default: flat)
  --vault-migration MODE          safe | preserve (default: safe)
  --external-tools POLICY         none | recommended (default: none)
  --dry-run                       Run preflight + show migration/install plan; write nothing
  --yes                           Skip interactive confirmation
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --vault) VAULT="${2:?missing path}"; shift 2 ;;
    --projects-root) PROJECTS_ROOT="${2:?missing path}"; shift 2 ;;
    --prefix) PREFIX="${2:?missing path}"; shift 2 ;;
    --project-layout) PROJECT_LAYOUT="${2:?missing mode}"; shift 2 ;;
    --vault-migration) MIGRATION="${2:?missing mode}"; shift 2 ;;
    --external-tools) TOOLS="${2:?missing policy}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --yes) YES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$VAULT" ]] || { echo "--vault is required" >&2; exit 2; }
[[ -d "$VAULT" ]] || { echo "Vault does not exist: $VAULT" >&2; exit 2; }
[[ "$TOOLS" == "none" || "$TOOLS" == "recommended" ]] || { echo "Invalid external-tools policy" >&2; exit 2; }
[[ "$PROJECT_LAYOUT" == "flat" || "$PROJECT_LAYOUT" == "categorized" ]] || { echo "Invalid project layout" >&2; exit 2; }
[[ "$MIGRATION" == "safe" || "$MIGRATION" == "preserve" ]] || { echo "Invalid vault migration mode" >&2; exit 2; }

# Reject drift and unsafe paths before executing the candidate runtime. The
# installer later stages this same verified inventory instead of copying a
# dirty checkout wholesale.
VERSION="$(python3 "$ROOT/scripts/verify-manifest.py" "$ROOT" --print-version)"

# Preflight is deliberately before any write. Missing Claude/Codex are warnings in
# the generic installer so the package can be prepared before the CLIs are installed.
python3 "$ROOT/lib/agent_workspace.py" preflight

SHARE="$PREFIX/share/ratchery"
LEGACY_SHARE="$PREFIX/share/agent-workspace"
BIN="$PREFIX/bin"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/ratchery"
PREVIOUS="none"
PREVIOUS_SHARE=""
if [[ -L "$SHARE" || -L "$LEGACY_SHARE" ]]; then
  echo "Refusing a symlinked runtime target or legacy runtime." >&2
  exit 1
fi
if [[ -f "$SHARE/MANIFEST.json" ]]; then
  [[ ! -L "$SHARE/MANIFEST.json" ]] || { echo "Refusing a symlinked runtime manifest." >&2; exit 1; }
  PREVIOUS_SHARE="$SHARE"
elif [[ -f "$LEGACY_SHARE/MANIFEST.json" ]]; then
  [[ ! -L "$LEGACY_SHARE/MANIFEST.json" ]] || { echo "Refusing a symlinked legacy runtime manifest." >&2; exit 1; }
  PREVIOUS_SHARE="$LEGACY_SHARE"
fi
if [[ -n "$PREVIOUS_SHARE" ]]; then
  PREVIOUS="$(python3 - "$PREVIOUS_SHARE/MANIFEST.json" <<'PY'
import json,sys
try: print(json.load(open(sys.argv[1])).get('version','unknown'))
except Exception: print('unknown')
PY
)"
fi

if [[ $DRY_RUN -eq 1 ]]; then
  python3 "$ROOT/lib/agent_workspace.py" vault-plan --vault "$VAULT" --migration "$MIGRATION"
  cat <<DRYRUN

Dry run only. No files were changed.
Current installed version: $PREVIOUS
Candidate version:         $VERSION
Runtime target:            $SHARE
Legacy runtime detected:   ${PREVIOUS_SHARE:-none}
Projects root:             $PROJECTS_ROOT
Project layout:            $PROJECT_LAYOUT
External tools policy:     $TOOLS

No third-party tool is auto-installed in Ratchetry. QMD <=2.6.3 is blocked by the
security gate; after you manually install a verified safe stable release, configure
it explicitly with: ratchery vault-qmd-setup ; then rerun with --apply.
DRYRUN
  exit 0
fi

if [[ $YES -ne 1 ]]; then
  cat <<CONFIRM
Install Ratchetry v$VERSION
  Previous:        $PREVIOUS
  Runtime:         $SHARE
  Command:         $BIN/ratchery
  Vault:           $VAULT
  Projects root:   $PROJECTS_ROOT
  Project layout:  $PROJECT_LAYOUT
  Vault migration: $MIGRATION
  External tools:  $TOOLS

The installer backs up the previous runtime before replacement and the Vault
migration creates external backups for recognized files before changing them.
User-owned project hooks/config entries are preserved by managed merge rules.
CONFIRM
  read -r -p "Continue? [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]] || exit 1
fi

mkdir -p "$BIN" "$PROJECTS_ROOT" "$STATE/runtime-backups"
if [[ -n "$PREVIOUS_SHARE" && -d "$PREVIOUS_SHARE" ]]; then
  STAMP="$(date +%Y%m%d-%H%M%S)-$$"
  RUNTIME_BACKUP="$STATE/runtime-backups/${STAMP}-v${PREVIOUS}"
  mkdir -p "$RUNTIME_BACKUP"
  cp -R "$PREVIOUS_SHARE" "$RUNTIME_BACKUP/runtime"
  printf '{"from_version":"%s","to_version":"%s","source":"%s"}\n' "$PREVIOUS" "$VERSION" "$PREVIOUS_SHARE" > "$RUNTIME_BACKUP/manifest.json"
  echo "Previous runtime backup: $RUNTIME_BACKUP"
fi

# Stage the candidate next to the target and atomically rename it into place.
STAGE="$PREFIX/share/.ratchery-${VERSION}-$$"
rm -rf "$STAGE"
mkdir -p "$STAGE"
python3 "$ROOT/scripts/verify-manifest.py" "$ROOT" --stage "$STAGE"
rm -rf "$SHARE.previous"
if [[ -d "$SHARE" ]]; then mv "$SHARE" "$SHARE.previous"; fi
if ! mv "$STAGE" "$SHARE"; then
  [[ -d "$SHARE.previous" ]] && mv "$SHARE.previous" "$SHARE"
  exit 1
fi
rm -rf "$SHARE.previous"

ln -sfn "$SHARE/bin/ratchery" "$BIN/ratchery"
ln -sfn "$SHARE/bin/ratchery" "$BIN/agent-workspace"
chmod +x "$BIN/ratchery" "$BIN/agent-workspace" "$SHARE/bin/ratchery" "$SHARE/bin/agent-workspace" "$SHARE/install.sh" "$SHARE/tests/run-tests.sh"

# From here on, $SHARE is the new runtime -- if any of these steps fail, roll
# it back to the version we just backed up above rather than leaving a
# half-configured install (new binaries in place, old/no global config) with
# no automatic recovery.
rollback_runtime() {
  if [[ -n "${RUNTIME_BACKUP:-}" && -d "$RUNTIME_BACKUP/runtime" && "$PREVIOUS_SHARE" == "$SHARE" ]]; then
    echo "Post-install step failed -- rolling back runtime to the pre-install backup ($RUNTIME_BACKUP)." >&2
    rm -rf "$SHARE"
    cp -R "$RUNTIME_BACKUP/runtime" "$SHARE"
    ln -sfn "$SHARE/bin/ratchery" "$BIN/ratchery"
    ln -sfn "$SHARE/bin/ratchery" "$BIN/agent-workspace"
  elif [[ -n "${RUNTIME_BACKUP:-}" && -d "$RUNTIME_BACKUP/runtime" && "$PREVIOUS_SHARE" == "$LEGACY_SHARE" ]]; then
    echo "Post-install step failed -- restoring the legacy command ($RUNTIME_BACKUP)." >&2
    rm -rf "$SHARE"
    rm -f "$BIN/ratchery"
    ln -sfn "$LEGACY_SHARE/bin/agent-workspace" "$BIN/agent-workspace"
  else
    echo "Post-install step failed. No prior runtime backup exists (this was a first install), so nothing to roll back -- the new runtime at $SHARE is still in place, but global config may be incomplete. Re-run install.sh to retry." >&2
  fi
}
trap rollback_runtime ERR

python3 "$SHARE/lib/agent_workspace.py" global-config \
  --vault "$VAULT" \
  --projects-root "$PROJECTS_ROOT" \
  --project-layout "$PROJECT_LAYOUT" \
  --external-tools "$TOOLS"

python3 "$SHARE/lib/agent_workspace.py" install-global
python3 "$SHARE/lib/agent_workspace.py" vault-install --migration "$MIGRATION"
trap - ERR

if [[ "$TOOLS" == "recommended" ]]; then
  # Third-party tools stay explicit. This command prints guidance only.
  python3 "$SHARE/lib/agent_workspace.py" tools-install-recommended
fi

if ! python3 "$SHARE/lib/agent_workspace.py" doctor-global; then
  echo "Post-install doctor found Vault/content issues. The runtime is installed; review the errors, use vault-fix-yaml if appropriate, then rerun doctor-global." >&2
fi

cat <<DONE

Ratchetry v$VERSION installed successfully.

Command:
  $BIN/ratchery

Compatibility command:
  $BIN/agent-workspace

Useful first commands:
  ratchery doctor-global --deep
  ratchery tools-status
  ratchery tools-recommend
  ratchery vault-qmd-setup        # plan only; optional

Create a categorized project:
  ratchery new my-project --category personal

Initialize an existing repository:
  cd /path/to/repository && ratchery init && ratchery doctor --deep

Documentation:
  $SHARE/docs/00-START-HERE.md
DONE

if [[ ":$PATH:" != *":$BIN:"* ]]; then
  echo "Add to your shell profile: export PATH=\"$BIN:\$PATH\""
fi
