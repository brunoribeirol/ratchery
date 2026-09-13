#!/usr/bin/env python3
"""Tests for deterministic release archives, checksums, and SPDX metadata."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build-release.py"
GENERATOR = ROOT / "scripts" / "gen-manifest.py"
VERIFIER = ROOT / "scripts" / "verify-manifest.py"
SMOKE = ROOT / "scripts" / "smoke-test-release.py"
EPOCH = 1_700_000_000

sys.path.insert(0, str(BUILDER.parent))
BUILDER_SPEC = importlib.util.spec_from_file_location(
    "ratchery_build_release_test_module", BUILDER
)
assert BUILDER_SPEC is not None and BUILDER_SPEC.loader is not None
BUILDER_MODULE = importlib.util.module_from_spec(BUILDER_SPEC)
sys.modules[BUILDER_SPEC.name] = BUILDER_MODULE
BUILDER_SPEC.loader.exec_module(BUILDER_MODULE)

SMOKE_SPEC = importlib.util.spec_from_file_location(
    "ratchery_release_smoke_test_module", SMOKE
)
assert SMOKE_SPEC is not None and SMOKE_SPEC.loader is not None
SMOKE_MODULE = importlib.util.module_from_spec(SMOKE_SPEC)
sys.modules[SMOKE_SPEC.name] = SMOKE_MODULE
SMOKE_SPEC.loader.exec_module(SMOKE_MODULE)


class ReleaseFixture:
    def __init__(self, base: Path) -> None:
        self.root = base / "repository"
        self.root.mkdir()
        self.write("lib/agent_workspace.py", 'VERSION = "1.2.3"\n')
        self.write("README.md", "# Fixture\n")
        self.write("LICENSE", "MIT fixture\n")
        self.write("bin/fixture", "#!/usr/bin/env python3\nprint('ok')\n", 0o755)
        self.regenerate_manifest()
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Release Fixture")
        self.git("add", ".")

    def write(self, rel: str, content: str, mode: int = 0o644) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        path.chmod(mode)

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            capture_output=True,
        )

    def regenerate_manifest(self, extra: list[dict[str, object]] | None = None) -> None:
        entries = []
        for rel in ["LICENSE", "README.md", "bin/fixture", "lib/agent_workspace.py"]:
            data = (self.root / rel).read_bytes()
            entries.append(
                {
                    "path": rel,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "size_bytes": len(data),
                }
            )
        entries.extend(extra or [])
        manifest = {
            "name": "ratchery-fixture",
            "version": "1.2.3",
            "channel": "stable",
            "generated_at": "2023-11-14T22:13:20+00:00",
            "file_count_excluding_manifest": len(entries),
            "total_bytes_excluding_manifest": sum(
                int(entry["size_bytes"]) for entry in entries
            ),
            "files": entries,
        }
        (self.root / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")

    def build(
        self, output: Path, *, environment: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--root",
                str(self.root),
                "--output-dir",
                str(output),
                "--source-date-epoch",
                str(EPOCH),
                "--repository",
                "example/ratchery-fixture",
            ],
            text=True,
            capture_output=True,
            env=environment,
        )

    def verify(
        self, *args: str, environment: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VERIFIER), str(self.root), *args],
            text=True,
            capture_output=True,
            env=environment,
        )


class TestReleaseArtifacts(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.fixture = ReleaseFixture(self.base)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_two_builds_are_byte_identical_and_archive_is_normalized(self) -> None:
        first = self.base / "first"
        second = self.base / "second"
        result_a = self.fixture.build(first)
        result_b = self.fixture.build(second)
        self.assertEqual(result_a.returncode, 0, result_a.stderr)
        self.assertEqual(result_b.returncode, 0, result_b.stderr)
        self.assertEqual(
            {path.name: path.read_bytes() for path in first.iterdir()},
            {path.name: path.read_bytes() for path in second.iterdir()},
        )

        archive_path = first / "ratchery-fixture-1.2.3.tar.gz"
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
        expected = {
            "ratchery-fixture-1.2.3/LICENSE",
            "ratchery-fixture-1.2.3/MANIFEST.json",
            "ratchery-fixture-1.2.3/README.md",
            "ratchery-fixture-1.2.3/bin/fixture",
            "ratchery-fixture-1.2.3/lib/agent_workspace.py",
        }
        self.assertEqual({member.name for member in members}, expected)
        self.assertTrue(all(member.isfile() for member in members))
        self.assertTrue(all(member.mtime == EPOCH for member in members))
        self.assertTrue(all(member.uid == member.gid == 0 for member in members))
        modes = {member.name: member.mode for member in members}
        self.assertEqual(modes["ratchery-fixture-1.2.3/bin/fixture"], 0o755)
        self.assertEqual(modes["ratchery-fixture-1.2.3/README.md"], 0o644)

    def test_installer_stage_contains_only_verified_manifest_files(self) -> None:
        self.fixture.write("untracked-secret.txt", "must not be installed\n")
        destination = self.base / "stage"

        result = self.fixture.verify("--stage", str(destination))

        self.assertEqual(result.returncode, 0, result.stderr)
        installed = {
            path.relative_to(destination).as_posix()
            for path in destination.rglob("*")
            if path.is_file()
        }
        self.assertEqual(
            installed,
            {
                "LICENSE",
                "MANIFEST.json",
                "README.md",
                "bin/fixture",
                "lib/agent_workspace.py",
            },
        )
        self.assertFalse((destination / ".git").exists())
        self.assertFalse((destination / "untracked-secret.txt").exists())

    def test_rejects_tracked_file_missing_from_manifest(self) -> None:
        self.fixture.write("docs/new-public-doc.md", "must be shipped\n")
        self.fixture.git("add", "docs/new-public-doc.md")

        verify_result = self.fixture.verify()
        self.assertNotEqual(verify_result.returncode, 0)
        self.assertIn("missing from manifest: docs/new-public-doc.md", verify_result.stderr)

        build_result = self.fixture.build(self.base / "incomplete-output")
        self.assertNotEqual(build_result.returncode, 0)
        self.assertIn("missing from manifest: docs/new-public-doc.md", build_result.stderr)

    def test_checksums_and_spdx_describe_the_published_archive(self) -> None:
        output = self.base / "dist"
        result = self.fixture.build(output)
        self.assertEqual(result.returncode, 0, result.stderr)

        expected_checksums = {}
        for line in (output / "SHA256SUMS.txt").read_text().splitlines():
            digest, filename = line.split("  ", 1)
            expected_checksums[filename] = digest
        self.assertEqual(
            set(expected_checksums),
            {
                "MANIFEST.json",
                "ratchery-fixture-1.2.3.spdx.json",
                "ratchery-fixture-1.2.3.tar.gz",
            },
        )
        for filename, digest in expected_checksums.items():
            self.assertEqual(hashlib.sha256((output / filename).read_bytes()).hexdigest(), digest)

        archive = output / "ratchery-fixture-1.2.3.tar.gz"
        sbom = json.loads((output / "ratchery-fixture-1.2.3.spdx.json").read_text())
        self.assertEqual(sbom["spdxVersion"], "SPDX-2.3")
        self.assertEqual(len(sbom["packages"]), 1)
        package = sbom["packages"][0]
        self.assertEqual(package["licenseDeclared"], "MIT")
        self.assertEqual(
            package["checksums"],
            [{"algorithm": "SHA256", "checksumValue": hashlib.sha256(archive.read_bytes()).hexdigest()}],
        )
        self.assertEqual(len(sbom["files"]), 5)
        sha1_values = []
        for rel in [
            "LICENSE",
            "MANIFEST.json",
            "README.md",
            "bin/fixture",
            "lib/agent_workspace.py",
        ]:
            sha1_values.append(hashlib.sha1((self.fixture.root / rel).read_bytes()).hexdigest())
        expected_code = hashlib.sha1("".join(sorted(sha1_values)).encode()).hexdigest()
        self.assertEqual(
            package["packageVerificationCode"]["packageVerificationCodeValue"],
            expected_code,
        )

    def test_rejects_path_traversal_and_symlinks(self) -> None:
        escaped = self.base / "escape"
        escaped.write_text("outside\n")
        data = escaped.read_bytes()
        unsafe = {
            "path": "../escape",
            "sha256": hashlib.sha256(data).hexdigest(),
            "size_bytes": len(data),
        }
        self.fixture.regenerate_manifest([unsafe])
        verify_result = self.fixture.verify()
        self.assertNotEqual(verify_result.returncode, 0)
        self.assertIn("unsafe manifest path", verify_result.stderr)
        result = self.fixture.build(self.base / "unsafe-output")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe manifest path", result.stderr)

        self.fixture.regenerate_manifest()
        link = self.fixture.root / "linked-readme"
        link.symlink_to("README.md")
        link_data = link.read_bytes()
        linked = {
            "path": "linked-readme",
            "sha256": hashlib.sha256(link_data).hexdigest(),
            "size_bytes": len(link_data),
        }
        self.fixture.regenerate_manifest([linked])
        self.fixture.git("add", "MANIFEST.json", "linked-readme")
        verify_result = self.fixture.verify()
        self.assertNotEqual(verify_result.returncode, 0)
        self.assertIn("symlink", verify_result.stderr)
        result = self.fixture.build(self.base / "link-output")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr)

    def test_rejects_content_and_version_drift(self) -> None:
        self.fixture.write("README.md", "changed after manifest\n")
        result = self.fixture.build(self.base / "drift-output")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("content mismatch", result.stderr)

        self.fixture.write("README.md", "# Fixture\n")
        self.fixture.regenerate_manifest()
        manifest_path = self.fixture.root / "MANIFEST.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["version"] = "9.9.9"
        manifest_path.write_text(json.dumps(manifest) + "\n")
        result = self.fixture.build(self.base / "version-output")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match runtime VERSION", result.stderr)

    def test_release_tools_ignore_git_environment_redirection(self) -> None:
        attacker = self.base / "attacker"
        attacker.mkdir()
        subprocess.run(["git", "-C", str(attacker), "init", "-q"], check=True)
        (attacker / "TRAP").write_text("wrong inventory\n")
        subprocess.run(["git", "-C", str(attacker), "add", "TRAP"], check=True)
        self.fixture.write("docs/unlisted.md", "must be detected\n")
        self.fixture.git("add", "docs/unlisted.md")
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_DIR": str(attacker / ".git"),
                "GIT_WORK_TREE": str(attacker),
                "GIT_INDEX_FILE": str(attacker / ".git/index"),
            }
        )

        verify_result = self.fixture.verify(environment=environment)
        build_result = self.fixture.build(
            self.base / "redirected-output", environment=environment
        )

        self.assertNotEqual(verify_result.returncode, 0)
        self.assertIn("missing from manifest: docs/unlisted.md", verify_result.stderr)
        self.assertNotEqual(build_result.returncode, 0)
        self.assertIn("missing from manifest: docs/unlisted.md", build_result.stderr)

    def test_rejects_nonempty_output_directory(self) -> None:
        output = self.base / "nonempty-output"
        output.mkdir()
        (output / "unexpected.txt").write_text("do not publish\n")

        result = self.fixture.build(output)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("output directory must be empty", result.stderr)
        self.assertEqual((output / "unexpected.txt").read_text(), "do not publish\n")

    def test_rejects_output_directory_symlink_and_symlinked_parent(self) -> None:
        outside = self.base / "outside-output"
        outside.mkdir()
        direct = self.base / "direct-link"
        parent = self.base / "parent-link"
        direct.symlink_to(outside, target_is_directory=True)
        parent.symlink_to(outside, target_is_directory=True)

        direct_result = self.fixture.build(direct)
        nested_result = self.fixture.build(parent / "nested")

        self.assertNotEqual(direct_result.returncode, 0)
        self.assertNotEqual(nested_result.returncode, 0)
        self.assertIn("must not traverse a symlink", direct_result.stderr)
        self.assertIn("must not traverse a symlink", nested_result.stderr)
        self.assertEqual(list(outside.iterdir()), [])

    def test_manifest_output_uses_the_already_validated_byte_snapshot(self) -> None:
        manifest_path = self.fixture.root / "MANIFEST.json"
        validated_manifest = manifest_path.read_bytes()
        original_load = BUILDER_MODULE.load_sources

        def mutate_after_validation(root: Path):
            result = original_load(root)
            manifest_path.write_text('{"attacker": "changed-after-validation"}\n')
            return result

        output = self.base / "snapshot-output"
        with mock.patch.object(
            BUILDER_MODULE, "load_sources", side_effect=mutate_after_validation
        ):
            BUILDER_MODULE.build_release(
                self.fixture.root, output, EPOCH, "example/ratchery-fixture"
            )

        self.assertEqual((output / "MANIFEST.json").read_bytes(), validated_manifest)
        with tarfile.open(output / "ratchery-fixture-1.2.3.tar.gz", "r:gz") as archive:
            archived = archive.extractfile(
                "ratchery-fixture-1.2.3/MANIFEST.json"
            )
            assert archived is not None
            self.assertEqual(archived.read(), validated_manifest)

    def test_generator_ignores_git_environment_redirection(self) -> None:
        victim = self.base / "generator-victim"
        (victim / "lib").mkdir(parents=True)
        (victim / "scripts").mkdir()
        (victim / "README.md").write_text("# Victim\n")
        (victim / "lib/agent_workspace.py").write_text('VERSION = "1.2.3"\n')
        shutil.copy2(GENERATOR, victim / "scripts/gen-manifest.py")
        shutil.copy2(ROOT / "scripts/git_environment.py", victim / "scripts/git_environment.py")
        subprocess.run(["git", "-C", str(victim), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(victim), "add", "."], check=True)

        attacker = self.base / "generator-attacker"
        attacker.mkdir()
        subprocess.run(["git", "-C", str(attacker), "init", "-q"], check=True)
        (attacker / "TRAP").write_text("wrong inventory\n")
        subprocess.run(["git", "-C", str(attacker), "add", "TRAP"], check=True)
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_DIR": str(attacker / ".git"),
                "GIT_WORK_TREE": str(attacker),
                "GIT_INDEX_FILE": str(attacker / ".git/index"),
            }
        )

        result = subprocess.run(
            [sys.executable, str(victim / "scripts/gen-manifest.py")],
            cwd=victim,
            env=environment,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        paths = {item["path"] for item in json.loads((victim / "MANIFEST.json").read_text())["files"]}
        self.assertIn("README.md", paths)
        self.assertIn("lib/agent_workspace.py", paths)
        self.assertNotIn("TRAP", paths)


class TestManifestGeneratorCli(unittest.TestCase):
    def test_help_does_not_modify_manifest(self) -> None:
        manifest_path = ROOT / "MANIFEST.json"
        before = manifest_path.read_bytes()

        result = subprocess.run(
            [sys.executable, str(GENERATOR), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)
        self.assertEqual(manifest_path.read_bytes(), before)


class TestReleaseSmokeSafety(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _archive_with(self, member: tarfile.TarInfo, data: bytes = b"fixture\n") -> Path:
        archive_path = self.base / "fixture.tar.gz"
        member.size = len(data)
        member.mode = 0o644
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.addfile(member, io.BytesIO(data))
        return archive_path

    def test_safe_extractor_rejects_traversal_and_links(self) -> None:
        traversal = self._archive_with(tarfile.TarInfo("package/../../escape"))
        with self.assertRaisesRegex(SMOKE_MODULE.ReleaseSmokeError, "regular files"):
            SMOKE_MODULE.safe_extract_archive(traversal, self.base / "traversal-output")

        archive_link = self.base / "archive-link-member.tar.gz"
        link_member = tarfile.TarInfo("package/link")
        link_member.type = tarfile.SYMTYPE
        link_member.linkname = "../../escape"
        link_member.mode = 0o777
        with tarfile.open(archive_link, "w:gz") as archive:
            archive.addfile(link_member)
        with self.assertRaisesRegex(SMOKE_MODULE.ReleaseSmokeError, "regular files"):
            SMOKE_MODULE.safe_extract_archive(
                archive_link, self.base / "archive-link-output"
            )

        link_path = self.base / "link.tar.gz"
        link_path.symlink_to(traversal)
        with self.assertRaisesRegex(SMOKE_MODULE.ReleaseSmokeError, "non-symlink"):
            SMOKE_MODULE.safe_extract_archive(link_path, self.base / "link-output")

    def test_safe_extractor_rejects_ambiguous_and_replaced_archive_paths(self) -> None:
        ambiguous = self._archive_with(tarfile.TarInfo("package/./README.md"))
        with self.assertRaisesRegex(SMOKE_MODULE.ReleaseSmokeError, "regular files"):
            SMOKE_MODULE.safe_extract_archive(ambiguous, self.base / "ambiguous-output")

        original = self._archive_with(tarfile.TarInfo("package/original.txt"))
        replacement = self.base / "replacement.tar.gz"
        shutil.copy2(original, replacement)
        real_open = SMOKE_MODULE.os.open

        def replace_before_open(path: Path, flags: int) -> int:
            original.unlink()
            replacement.rename(original)
            return real_open(path, flags)

        with mock.patch.object(SMOKE_MODULE.os, "open", side_effect=replace_before_open):
            with self.assertRaisesRegex(
                SMOKE_MODULE.ReleaseSmokeError, "changed while opening"
            ):
                SMOKE_MODULE.safe_extract_archive(original, self.base / "replaced-output")

    def test_safe_extractor_writes_only_the_single_regular_root(self) -> None:
        archive_path = self._archive_with(tarfile.TarInfo("package/README.md"))
        extracted = SMOKE_MODULE.safe_extract_archive(
            archive_path, self.base / "valid-output"
        )
        self.assertEqual(extracted.name, "package")
        self.assertEqual((extracted / "README.md").read_text(), "fixture\n")


if __name__ == "__main__":
    unittest.main()
