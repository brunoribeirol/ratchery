# Sources and adaptation note

This is a Ratchetry-native workflow, not a vendored third-party Skill. It adapts
the general reproduce/minimize/hypothesize/instrument/fix discipline reviewed
from these MIT-licensed projects on 2026-10-06:

- <https://github.com/mattpocock/skills/tree/main/skills/diagnosing-bugs>
- <https://github.com/obra/superpowers/tree/main/skills/systematic-debugging>

Ratchetry's version adds explicit secret redaction, bounded instrumentation,
authorization before mutation, and its existing durable bug-note threshold.
