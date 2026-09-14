# Delta Spec: Reject untracked release files during manifest generation

Mode: **openspec-light** (T1).

## Why

`gen-manifest.py` enumerates only the Git index. A newly created release file
can therefore be absent from a locally generated and locally verified
`MANIFEST.json`, then become tracked in the same commit and fail CI. The
prepublication run reproduced this with four new documentation/test files.

## What changes

- Before generating, enumerate non-ignored untracked files through Git.
- Reject tracked release files whose working-tree content differs from the
  index, including partial staging and unstaged deletion.
- Ignore paths already excluded from release inventory, such as `.github/` and
  `MANIFEST.json` itself.
- Fail with an actionable message when any other untracked release candidate
  exists; require the maintainer to review and stage intended new files first.
- Continue building the manifest only from the Git index. Never silently add
  arbitrary working-tree files to a release.

## Affected contracts

- `python3 scripts/gen-manifest.py` becomes fail-closed when releasable files
  are untracked or not fully staged.
- The `MANIFEST.json` schema and archive format do not change.
- The publishing procedure stages intended new files before final generation.

## Out of scope

- Automatically staging files.
- Including ignored files, local state, `.github/`, or arbitrary untracked
  scratch data in an artifact.
- Changing runtime installation or archive verification.

## Tasks

- [x] Add untracked release-candidate detection to the generator.
- [x] Add a regression covering rejection before staging and inclusion after
  explicit staging.
- [x] Correct the manifest and publishing documentation.
- [x] Run focused and full release validation.

## Validation

- `python3 -m unittest tests.test_release_artifacts`
- `make test`
- `make release-smoke`
- `python3 scripts/verify-manifest.py`

Observed: 16 focused release-artifact tests and the full 316-test suite passed;
the manifest verified 279 files, 18 Action pins and 174 Markdown files passed,
and the release archive smoke test passed.

## Status

- [ ] Proposed
- [ ] In progress
- [x] Implemented
- [ ] Archived (link the merged commit)
