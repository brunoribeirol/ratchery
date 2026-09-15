# Security

## Threat model
Protect local credentials, prevent accidental destructive operations, minimize network/supply-chain exposure, and avoid leaking user prompts into durable memory.

## Cost-observability privacy

`ratchery usage` invokes ccusage with an argv list, never shell text, and
runs it from the user's home directory so an inspected repository cannot inject
a local ccusage configuration. Benchmark capture and `budget check` force JSON
and offline mode, validates source/date/session selectors, and immediately reduces the report to
aggregate totals. Stored snapshots exclude raw rows, session IDs, prompts,
responses, paths, project labels, and source code. User-supplied provenance
labels reject whitespace/path separators and must not contain secrets. Snapshots
live under the user's absolute XDG state directory, outside the repository and
agent context; relative XDG state values are ignored, and a resolved path inside
the repository is rejected. The
project namespace combines its durable UUID with a canonical-path fingerprint,
so copying a public project ID cannot select another checkout's evidence.

This is a data-minimization boundary, not an anonymity claim: aggregate dates,
date windows, project-label fingerprints, token counts, and estimated costs can
still be sensitive business information. Do not commit or paste snapshots
publicly. Offline mode avoids
pricing refresh access; it does not make an unreviewed ccusage binary trustworthy.
`budget check` persists nothing and redacts the project selector from its
result. Its values remain ccusage estimates after usage has occurred; it is not
a provider billing boundary or pre-spend control. `--enforce` only maps a local
threshold observation to exit 3 for an explicitly configured caller.

The recorded clean commit is capture-time provenance, not proof that historical
usage was generated at that commit; keep the experiment checkout unchanged
through capture and treat date-window labels as self-attested protocol data.

## Provider-neutral memory boundary

The built-in handoff is explicit-only: no SessionEnd hook, watcher, daemon,
network request, MCP server, or model call creates or reads it automatically.
One pending `Handoff.json` lives outside the repository in the exact Vault
project selected by the repository's durable UUID and outside QMD's Markdown
index. Duplicate UUID claims fail closed.

Input arrives only through explicitly confirmed stdin, is capped at 64 KiB,
has an exact schema and bounded lists/fields, and cannot supply project or Git
provenance. Absolute/traversing paths, duplicate JSON keys, multiline/control
data, wrong node types (including FIFOs), symlinks, concurrent mutations, and
common credential forms are rejected without echoing a matched value. Vault and
backup components are opened through anchored directory descriptors. A second
write requires `--replace`; replacement and `clear --apply` first create private
XDG-state backups while holding a per-project POSIX lock across the complete
read/backup/revalidate/mutate boundary. Git provenance explicitly disables
repository-configured fsmonitor commands. A synced/restored handoff is not read
if it grants group or other permissions. This credential tripwire is defense
in depth, not a DLP guarantee, so
every handoff still requires human/agent review and must exclude prompts,
responses, raw output, secrets, and sensitive customer data.

`memory backends/status/doctor/plan` do not execute optional binaries. Merely
finding `ai-memory` on `PATH` never reports it enabled. See `MEMORY.md` for the
data contract and the deliberately separate experimental-backend policy.

## Optional scanners and MCP security

No third-party scanner is part of the always-on runtime. Use Gitleaks at an
explicit commit/release boundary, then select Trivy, Semgrep, Checkov,
OSV-Scanner, Syft, or Grype by project risk and artifact type. More scanners can
mean duplicated findings, extra databases/network, false positives, and larger
agent output. Redact suspected secret values before any report enters an agent
response, issue, CI log, or Vault note.

For MCP-heavy setups, native sandboxing, least privilege, static definitions,
and explicit opt-in remain primary. Agent Scan or a container gateway may add
defense in depth, but only after reviewing current data flow, external service or
token requirements, command execution, filesystem/network access, and tool
definition pinning. Ratchetry does not auto-install or auto-run either.

Ratchetry-managed MCP definitions remain explicit opt-ins. Serena is pinned to
an immutable full commit, its web dashboard is disabled, and only the three
symbol-retrieval tools are exposed. Context7 exposes only library resolution and
documentation query. Codex profiles require prompt approval and bound startup,
tool runtime, and output size; Claude places the same managed tools in
`permissions.ask`. These limits reduce the reachable surface and context cost;
they do not establish that upstream code or returned content is trustworthy.

## Claude
- permissions deny sensitive reads;
- bypass-permissions mode disabled;
- sandbox on and fail-closed;
- unsandboxed fallback disabled;
- filesystem/credential denies;
- subprocess credential environment scrub;
- PreToolUse blocks credential paths, broad environment dumps, likely secret expansion, destructive Git/filesystem commands, and remote script pipes.

The primary deny lists cover both home-directory credentials and project-local
package/cloud credential files at the repository root or in nested workspaces.
The Claude hook uses its client-provided project directory as an exec-form
argument, so repository discovery does not require interpolating a shell
command.

## Codex
- project-edit filesystem scope;
- sensitive files denied;
- project network disabled by default;
- secret environment filtering;
- same deterministic PreToolUse guard.

The Codex hook discovers the checkout with Git in a minimal environment so
caller-controlled `GIT_*` routing cannot redirect it. The runtime independently
scrubs the same Git controls, verifies that the discovered root contains the
reported working directory, and writes task-policy state through a verified
directory descriptor. A missing, symlinked, or replaced `.agents/state`
directory makes persistence fail visibly without writing through the link.

All project-mutating commands reject symlinks and non-directory/non-file nodes
on the managed parent/file surface before reading or writing configuration.
Project configuration backups live outside the repository, use private
directory/file modes, and record only a project-relative source path. MCP
enable/disable validates both client representations before mutation and rolls
back every project file if a replacement fails.

Ratchetry supports the generated policy contract with Claude Code 2.1.187+ and
Codex CLI 0.138.0+ when those clients are installed. `preflight`, project
`doctor`, and `doctor-global` enforce that version floor. Project `doctor`
verifies the full shipped deny/filter contract and the exact managed
PreToolUse binding before the deep probe tests the runtime behavior.

Codex applies repository-local `.codex/config.toml` only after the user has
reviewed and trusted the repository. Ratchetry validates the file but never
self-authorizes that user-level trust decision. The scheduled/manual
`client-canary.yml` preparation job has read-only repository access; its four
client jobs have no GitHub token scope or checkout. They install each public
package before downloading only the generated fixture, then parse it with
minimum/current supported clients without model inference. Claude's official
package is the sole exception to the no-lifecycle-script rule because its
documented native binary is installed by that step. Codex's hosted check proves
the permission-profile CLI and strictly parsed config schema, not `bwrap`
execution: nested network namespaces are unavailable on GitHub-hosted runners. This is
compatibility evidence, not an end-to-end proof of sandbox containment or MCP
safety.

The canary does not run `claude doctor`: that diagnostic may wait for terminal
input or connectivity in older clients and is not a deterministic config
parser. Claude version and pending-MCP parsing run as separate commands with
closed stdin and a 30-second timeout, so an upstream hang fails quickly and
identifies the exact contract step.

`doctor --deep` simulates `cat .env` and requires denial. Never weaken controls simply to silence a tool warning.

Example/template environment files such as `.env.example`, `.env.sample`, and `.env.template` remain readable for setup/documentation. Common real `.env` variants are denied explicitly, and the deterministic hook catches arbitrary secret-like `.env.*` variants except those example/template names.
