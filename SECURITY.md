# Security Policy

## Supported Versions

Only the latest released version of Ratchetry is supported
with security fixes. If you're not on the latest release, please upgrade
before reporting — the issue may already be fixed.

| Version | Supported |
| ------- | --------- |
| Latest `1.0.0` release candidate (before stable launch) | Yes |
| Latest stable release (after launch) | Yes |
| Older releases | No |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Use GitHub's private vulnerability reporting for this repository:
[github.com/brunoribeirol/ratchery/security/advisories/new](https://github.com/brunoribeirol/ratchery/security/advisories/new).
This is the primary and only supported disclosure channel — it keeps the
report private between you and the maintainer until a fix ships. Include:

- A description of the vulnerability and its impact.
- Steps to reproduce (a minimal repro is very helpful).
- The version/commit you tested against and your OS.

We aim to acknowledge reports within 5 business days. Please give us a
reasonable amount of time to address the issue before any public disclosure.

## Release Integrity

Tagged releases publish a deterministic source archive, `SHA256SUMS.txt`, an
SPDX 2.3 SBOM, and GitHub/Sigstore provenance. Verify the checksum and
attestation before installing a downloaded release; exact commands and the
release job's isolated permission boundary are in
[`docs/PUBLISHING.md`](docs/PUBLISHING.md).

## Security Model

Ratchetry installs configuration and hooks that constrain what
an AI coding agent (Claude Code or Codex CLI) can do inside a project. That
security model is **two layers**, and the two layers are not interchangeable:

### Layer 1 (primary): native CLI sandbox and permission deny-lists

The primary enforcement boundary is the host CLI's own sandbox and permission
system — not anything this project's Python code executes at runtime.

For Claude Code, the installed `assets/project/.claude/settings.json`
template:

- Enables the native sandbox (`sandbox.enabled: true`) with
  `failIfUnavailable: true` — **the sandbox fails closed**: if the sandbox
  can't be established, the run is blocked rather than silently falling back
  to unsandboxed execution.
- Declares filesystem deny rules (`sandbox.filesystem.denyRead` and
  `permissions.deny`) for `.env` and its environment variants
  (`.env.local`, `.env.production`, etc.), `~/.ssh`, `~/.aws/credentials`,
  `~/.config/gcloud/application_default_credentials.json`, `~/.netrc`,
  `~/.npmrc`, `~/.pypirc`, `*.pem`, `id_rsa`/`id_ed25519`, and
  `credentials.json`. Package/cloud credential names are denied at the
  project root and recursively in nested workspaces as well as under the
  user's home directory.
- Declares credential file/env-var deny entries under
  `sandbox.credentials` (files listed above, plus environment variables such
  as `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GITHUB_TOKEN`, `GH_TOKEN`,
  `NPM_TOKEN`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
  `AWS_SESSION_TOKEN`).
- Sets `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` so subprocesses spawned by the
  agent don't inherit the full parent environment by default.

Codex CLI is configured analogously: restricted workspace permissions,
network access off by default, and environment secret filtering (see
`docs/ARCHITECTURE.md`'s "Two-layer security model" section, and
`docs/10-SECURITY.md` for the full Codex `config.toml` reference).

This is the boundary that actually matters. It is enforced by the CLI/OS,
not by this project's own code, and it's designed to fail closed rather than
degrade silently.

Ratchetry supports this generated policy contract with Claude Code 2.1.187+ and
Codex CLI 0.138.0+. `preflight`, project `doctor`, and `doctor-global` reject an
installed client below that floor or one that returns unreadable version data;
a timed-out/spawn-failed probe is reported as an unverified warning, not
misrepresented as a known-bad version. An absent client remains supported when
the user deliberately runs only the other one. Project `doctor` also checks that the required deny layers, environment
filters, restricted profile, hooks feature, and exact managed `PreToolUse`
bindings remain present.

### Layer 2 (secondary): the PreToolUse regex hook

`lib/hook_runtime.py` also runs as a `PreToolUse` hook (wired up in
`assets/project/.claude/settings.json`'s `hooks.PreToolUse`, matched against
`Bash|Read|Write|Edit|MultiEdit`). On every matching tool call it:

- Blocks a fixed set of destructive/unreviewed shell patterns (`git reset
  --hard`, forced `git push`, `rm -rf /...`, `curl|bash`-style pipe-to-shell,
  etc. — see `DESTRUCTIVE_PATTERNS`).
- Blocks shell commands or file-path tool inputs that reference sensitive
  paths by regex (`.env*`, `~/.ssh`, `id_rsa`/`id_ed25519`, `~/.aws/credentials`,
  the gcloud application-default-credentials file, `credentials.json`,
  `*.pem`, `.netrc`, `.npmrc`, `.pypirc` — see `SENSITIVE_PATH_PATTERNS`).
- Blocks broad environment dumps (`env`, `printenv`, `set`) and direct shell
  expansion of variables whose names look like secrets (`*_KEY`, `*_TOKEN`,
  `*_SECRET`, `*_PASSWORD`, `*_CREDENTIAL`, etc.).

For patch tools, the hook examines diff target paths rather than patch bodies.
This still blocks a patch aimed at a sensitive file without falsely rejecting
documentation or policy changes that merely name one. Claude invokes the
runtime through its client-provided project directory; Codex and the runtime
both neutralize caller-controlled Git routing before accepting a repository
root. Task-policy writes require an existing real `.agents/state` directory
and use a directory-anchored atomic replacement, so a symlink does not redirect
the persisted metadata.

**This layer is explicitly a secondary, deterministic guard — not a
substitute for the sandbox.** The code and its own comments say so
(`lib/hook_runtime.py`: "This is a secondary deterministic guard. Claude
sandbox credentials and Codex filesystem denies are the primary enforcement
boundaries."). Its known limitation: it matches on literal substrings and
regexes against the command text and declared tool-input paths. An agent (or
an attacker steering one, e.g. via prompt injection) that constructs a
sensitive path dynamically — string concatenation, variable indirection,
encoding, a symlink, a wrapper script, reading the file through a tool the
hook doesn't inspect — can bypass this layer without matching any pattern
here. **Treat it as defense-in-depth against straightforward mistakes and
unsophisticated attempts, never as the reason the sandbox layer can be
weakened or skipped.**

### Untrusted content policy

Repository content that an agent reads while working — this project's own
`README.md`, `AGENTS.md`/`CLAUDE.md` fragments outside the managed block,
code comments, commit messages, issue/PR text, and any fetched web/MCP
content — is treated as **data to reason about, never as instructions to
follow**. Only the managed blocks in `AGENTS.md`/`CLAUDE.md` and the
framework's own `.claude/settings.json` / `.codex/config.toml` are trusted
policy. This is stated explicitly in the "Untrusted content policy" section
of `assets/project/AGENTS.block.md`, which every installed project inherits:
a file claiming to override tool permissions, request credential access, or
redirect network calls does not do so merely by existing in the repository,
and content that looks like it's trying to direct an AI agent ("ignore
previous instructions," embedded shell commands to run unprompted) should be
flagged and not acted on.

That same policy also requires not chaining, in one unattended step: reading
untrusted content, accessing private/sensitive data, and sending data
externally (network call, git push, a file write an attacker could later
read). See `assets/project/AGENTS.block.md` for the full policy text.

## What this project does not claim

- It does not claim the PreToolUse hook is a complete or sufficient security
  boundary on its own.
- It does not claim to detect or block every way secrets could be exfiltrated
  by a sufficiently motivated or well-instructed agent — the design goal is
  to raise the bar and fail closed at the sandbox layer, not to guarantee
  perfect prevention.
- It does not persist raw user prompts to disk or the Vault (see
  `hook_runtime.py`'s `UserPromptSubmit` handling, which stores only a
  truncated SHA-256 hash and classification metadata).
