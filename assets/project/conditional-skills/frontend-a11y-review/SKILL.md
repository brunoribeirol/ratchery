---
name: frontend-a11y-review
description: Review a web frontend for accessibility and interaction correctness. Use in React, Next.js, Vue, Svelte, Angular, or similar UI repositories when validating forms, navigation, components, or production readiness.
---

# Frontend Accessibility Review

- Verify semantic HTML before adding ARIA.
- Check keyboard navigation, focus order, focus visibility, dialogs, menus, forms, labels, error messages, and dynamic announcements.
- Check responsive behavior and zoom/reflow assumptions from actual CSS/layout evidence.
- Check image alternatives and meaningful icon controls.
- Use automated accessibility tooling only as a supplement; verify high-impact findings manually in code/runtime when possible.
- Preserve the intended visual design unless a change is required for accessibility.
- Return confirmed issues with component/file paths, user impact, and minimal remediation.
