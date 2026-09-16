#!/usr/bin/env python3
"""Static least-privilege contract for the release workflow."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/release.yml"


class TestReleaseWorkflowContract(unittest.TestCase):
    def setUp(self) -> None:
        if not WORKFLOW.exists():
            self.skipTest("CI-only workflow is intentionally absent from release archives")
        text = WORKFLOW.read_text()
        self.build = text.split("  build:\n", 1)[1].split("  attest:\n", 1)[0]
        remainder = text.split("  attest:\n", 1)[1]
        self.attest = remainder.split("  publish:\n", 1)[0]
        self.publish = remainder.split("  publish:\n", 1)[1]

    def test_tag_code_runs_with_read_only_permissions(self) -> None:
        self.assertIn("permissions:\n      contents: read", self.build)
        self.assertNotIn("id-token: write", self.build)
        self.assertNotIn("attestations: write", self.build)
        self.assertNotIn("actions/attest@", self.build)

    def test_attestation_job_has_no_checkout_or_repository_commands(self) -> None:
        self.assertIn("id-token: write", self.attest)
        self.assertIn("attestations: write", self.attest)
        self.assertIn("actions/attest@", self.attest)
        self.assertNotIn("actions/checkout@", self.attest)
        self.assertNotIn("\n      - run:", self.attest)
        self.assertNotIn("\n        run:", self.attest)

    def test_only_the_four_expected_outputs_are_transferred_and_published(self) -> None:
        self.assertNotIn("dist/*", self.build)
        self.assertNotIn("dist/*", self.publish)
        for expected in (
            "dist/SHA256SUMS.txt",
            "dist/MANIFEST.json",
            "needs.build.outputs.archive",
            "needs.build.outputs.sbom",
        ):
            self.assertIn(expected, self.publish if expected.startswith("needs") else self.build)

    def test_exact_built_archive_is_smoked_before_upload(self) -> None:
        build_step = "run: python3 scripts/build-release.py --output-dir dist"
        smoke_step = (
            'run: python3 scripts/smoke-test-release.py '
            '"${{ steps.metadata.outputs.archive }}"'
        )
        upload_step = "uses: actions/upload-artifact@"
        self.assertIn(smoke_step, self.build)
        self.assertLess(self.build.index(build_step), self.build.index(smoke_step))
        self.assertLess(self.build.index(smoke_step), self.build.index(upload_step))

    def test_prerelease_channel_is_validated_and_applied(self) -> None:
        self.assertIn('expected_channel = "prerelease" if "-" in version else "stable"', self.build)
        self.assertIn("channel: ${{ steps.metadata.outputs.channel }}", self.build)
        self.assertIn('if [[ "$RELEASE_CHANNEL" == "prerelease" ]]', self.publish)
        self.assertIn("release_flags+=(--prerelease)", self.publish)

    def test_publish_job_names_repository_without_checkout(self) -> None:
        self.assertNotIn("actions/checkout@", self.publish)
        self.assertIn('gh release create "$GITHUB_REF_NAME"', self.publish)
        self.assertIn('--repo "$GITHUB_REPOSITORY"', self.publish)


if __name__ == "__main__":
    unittest.main()
