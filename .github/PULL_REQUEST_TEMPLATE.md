## Summary

<!-- What does this change do, and why? -->

## Checklist

- [ ] Tests run and passing locally:
  - [ ] `bash tests/run-tests.sh`
  - [ ] `python3 -m unittest discover -s tests -p 'test_*.py'`
- [ ] Docs updated if this change affects setup, usage, or architecture
      (`README.md`, `CHANGELOG.md`, `docs/`, or the relevant asset's own
      docs).
- [ ] No new dependency added without prior discussion in an issue (this
      project is Python-stdlib-only).
- [ ] **Security-relevant change flagged below**, if applicable (see next
      section). If this doesn't touch `lib/hook_runtime.py`, sandbox/
      permission configuration, or anything affecting what an agent can
      read/execute, leave the section below as "N/A."

## Security-relevant change

<!--
If this PR touches lib/hook_runtime.py, assets/**/settings.json or
config.toml permission/sandbox blocks, credential handling, or the
untrusted-content policy, describe the change and its security impact here.
Otherwise write "N/A".
-->

## Related issues

<!-- Closes #... -->
