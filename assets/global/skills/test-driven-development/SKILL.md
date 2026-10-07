---
name: test-driven-development
description: Build a behavior change in small vertical red-green-refactor slices. Use when a feature, bug fix, or refactor has an observable test seam; avoid for documentation-only edits, generated files, disposable probes, or changes whose required harness cannot run.
---

# Test-driven development

Use TDD to shorten the feedback loop, not to maximize test count.

1. Identify the public behavior and the cheapest stable seam where it can be
   observed. Prefer a public API, command, file contract, or user-visible result
   over private implementation details.
2. Select one vertical slice. State the behavior, input, observable output, and
   why the selected test would fail before the change.
3. Add the smallest focused test and run it. Confirm that it fails for the
   intended missing behavior, not because of setup, syntax, or unrelated state.
4. Implement only enough production code to make that slice pass. Run the test
   again and inspect the exit status and relevant output.
5. Refactor only while the slice remains green. Remove duplication and improve
   names without widening scope or rewriting unrelated code.
6. Repeat one slice at a time, then run the affected broader suite. Report both
   fresh passing evidence and any checks that could not run.

Do not weaken an assertion merely to turn the test green. Do not replace a
behavioral test with a mock that bypasses the behavior. If a safe red phase is
impossible, explain why, name the alternative evidence, and keep the change
bounded.
