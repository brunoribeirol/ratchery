# Release Supply-Chain Specification

Status: implemented
Tier: T1
Owner: primary maintainer

## Problem

The tag workflow currently publishes `SHA256SUMS.txt` containing hashes of
individual checkout files, but it does not publish the archive whose bytes a
consumer needs to verify. It also publishes neither an SBOM nor a signed build
provenance statement. A successful workflow therefore proves that a tag was
packaged, but gives a downstream user no single Ratchetry artifact to download,
hash, inspect, and verify.

## Contract

For every `vX.Y.Z` tag whose version matches the repository metadata, the
release workflow must:

1. verify `MANIFEST.json` against the tagged tree;
2. build a deterministic source archive from exactly the manifest inventory;
3. generate a JSON SPDX 2.3 SBOM describing the archive and every contained
   file, with no invented runtime dependencies;
4. publish SHA-256 checksums for the archive, SBOM, and manifest;
5. create GitHub/Sigstore build-provenance and SBOM attestations for the source
   archive; and
6. attach all four artifacts to the GitHub Release.

The archive must be byte-identical when rebuilt from the same tree and source
epoch. It must not contain `.git`, GitHub workflow credentials, untracked
files, local state excluded by the manifest, absolute paths, symlinks, or path
traversal entries.

`install.sh` must apply the same inventory boundary: validate the manifest,
derive the displayed version from it, and stage only verified entries. A dirty
checkout must never leak `.git`, ignored state, or unrelated untracked files
into the installed runtime.

## Design

- `scripts/build-release.py` is stdlib-only and reads the authoritative
  `MANIFEST.json` rather than walking the filesystem.
- Archive ownership, timestamps, modes, and member order are normalized.
  Executable bits come from the Git index, not the local checkout umask.
- `SOURCE_DATE_EPOCH` may override the timestamp. Otherwise the tagged Git
  commit timestamp is used, which keeps rebuilds deterministic.
- The SPDX document is a separate release artifact. It uses the archive
  checksum plus SHA-1/SHA-256 checksums for each source file; SHA-1 is present
  only because SPDX 2.3's package verification-code algorithm requires it.
- GitHub's first-party `actions/attest` creates one SLSA provenance
  attestation and one SPDX SBOM attestation. The action remains commit-SHA
  pinned. Repository code executes only in the read-only build job; a
  no-checkout/no-shell attestation job holds OIDC privileges, and a third job
  holds only the `contents: write` permission needed to publish the Release.

## Failure behavior

The build fails before publication when:

- the tag, library version, or manifest version disagree;
- manifest paths are duplicated, absolute, escaping, symlinked, missing, or
  not regular files;
- file size/hash differs from the manifest;
- a manifest entry is not tracked by Git or has an unsupported Git mode; or
- the requested repository identifier or output package name is unsafe.

## Tests

- Build twice into distinct temporary directories and compare every output
  byte.
- Inspect archive members, metadata, modes, prefix, and inventory.
- Recompute the published checksums and SPDX package verification code.
- Exercise rejection of path traversal, symlinks, hash drift, and version
  mismatch in isolated Git fixtures.
- Run the complete repository suite, Ruff, manifest verification, workflow
  pin audit, and `git diff --check`.

## Tasks

- [x] Implement deterministic archive/SBOM/checksum generation.
- [x] Add focused release-artifact tests and wire them into local/CI suites.
- [x] Add pinned provenance and SBOM attestations to `release.yml`.
- [x] Document release creation and downstream verification.
- [x] Add the public-repository settings checklist that cannot live in Git.
- [x] Stage installation from the verified manifest inventory only.
- [x] Regenerate and verify `MANIFEST.json`.
