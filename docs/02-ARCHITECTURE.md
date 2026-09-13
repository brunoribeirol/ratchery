# Architecture

```text
Global runtime/config
  ~/.local/share/ratchery
  ~/.config/ratchery
  ~/.agents/skills
  ~/.claude/skills -> canonical skills

Repository
  AGENTS.md / CLAUDE.md
  .agents/runtime + state + conditional skills
  .claude/rules + agents + settings
  .codex/config + hooks + agents
  docs/

Obsidian
  project Homes, session summaries, decisions, reusable bugs, commands, references
```

Ownership rule: Ratchetry modifies only explicit managed blocks/owned hook groups/managed skill directories. Human content outside those surfaces is preserved.
