# Hooks and Automation

Only two lifecycle surfaces are installed by default:

- `UserPromptSubmit`: stores risk/classification metadata plus a prompt hash, never prompt text.
- `PreToolUse`: deterministic defense-in-depth for credentials and destructive commands.

There is **no default SessionEnd hook**. Close-time hooks are a weak persistence boundary because the original working directory may be moved/deleted and clients can change lifecycle behavior. Important durable state is written explicitly through `workspace-save`.

Ratchetry hook groups are identified by the runtime command marker. Refresh removes/replaces only those groups and preserves user groups. Configuration writes are backed up and atomic.
