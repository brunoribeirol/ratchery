#!/usr/bin/env python3
"""Install and exercise one built release archive in an isolated environment."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_FILES = 4096
SAFE_ROOT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
ALLOWED_MODES = {0o644, 0o755}


class ReleaseSmokeError(RuntimeError):
    """Raised when an archive cannot be safely installed and exercised."""


def _safe_members(archive: tarfile.TarFile) -> tuple[str, list[tarfile.TarInfo]]:
    members: list[tarfile.TarInfo] = []
    roots: set[str] = set()
    names: set[str] = set()
    total_size = 0
    for member in archive:
        if len(members) >= MAX_FILES:
            raise ReleaseSmokeError("archive must contain between 1 and 4096 files")
        members.append(member)
        path = PurePosixPath(member.name)
        normalized = path.as_posix()
        if (
            not member.isfile()
            or member.size < 0
            or path.is_absolute()
            or len(path.parts) < 2
            or member.name != normalized
            or any(part in {"", ".", ".."} for part in path.parts)
            or any(
                "\\" in part
                or any(ord(character) < 32 or ord(character) == 127 for character in part)
                for part in path.parts
            )
        ):
            raise ReleaseSmokeError(
                "archive may contain only regular files below one safe top-level directory"
            )
        if normalized in names:
            raise ReleaseSmokeError(f"archive contains duplicate path: {normalized}")
        names.add(normalized)
        roots.add(path.parts[0])
        total_size += member.size
        if total_size > MAX_ARCHIVE_BYTES:
            raise ReleaseSmokeError("archive expands beyond the 128 MiB smoke-test limit")
        if member.mode not in ALLOWED_MODES:
            raise ReleaseSmokeError(
                f"archive contains unsupported mode {member.mode:o}: {normalized}"
            )
    if not members:
        raise ReleaseSmokeError("archive must contain between 1 and 4096 files")
    if len(roots) != 1:
        raise ReleaseSmokeError("archive must contain exactly one top-level directory")
    root = next(iter(roots))
    if not SAFE_ROOT.fullmatch(root):
        raise ReleaseSmokeError("archive top-level directory name is unsafe")
    return root, members


def safe_extract_archive(archive_path: Path, destination: Path) -> Path:
    """Extract a release without following archive links or accepting special files."""
    try:
        archive_stat = archive_path.lstat()
    except OSError as exc:
        raise ReleaseSmokeError(f"cannot inspect archive: {exc}") from exc
    if stat.S_ISLNK(archive_stat.st_mode) or not stat.S_ISREG(archive_stat.st_mode):
        raise ReleaseSmokeError("release archive must be a regular, non-symlink file")
    if archive_stat.st_size > MAX_ARCHIVE_BYTES:
        raise ReleaseSmokeError("release archive exceeds the 128 MiB smoke-test limit")

    descriptor = -1
    try:
        descriptor = os.open(
            archive_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        )
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (archive_stat.st_dev, archive_stat.st_ino)
            or opened.st_size != archive_stat.st_size
        ):
            raise ReleaseSmokeError("release archive changed while opening")
        with os.fdopen(descriptor, "rb") as archive_file:
            descriptor = -1
            with tarfile.open(fileobj=archive_file, mode="r:gz") as archive:
                root_name, members = _safe_members(archive)
                for member in members:
                    relative = PurePosixPath(member.name)
                    target = destination.joinpath(*relative.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = archive.extractfile(member)
                    if source is None:
                        raise ReleaseSmokeError(f"cannot read archive member: {member.name}")
                    with source, target.open("xb") as output:
                        shutil.copyfileobj(source, output)
                    if target.stat().st_size != member.size:
                        raise ReleaseSmokeError(
                            f"archive member size changed while extracting: {member.name}"
                        )
                    target.chmod(member.mode)
            after = os.fstat(archive_file.fileno())
            if (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
            ) != (
                opened.st_dev,
                opened.st_ino,
                opened.st_size,
                opened.st_mtime_ns,
            ):
                raise ReleaseSmokeError("release archive changed while reading")
    except (OSError, tarfile.TarError) as exc:
        raise ReleaseSmokeError(f"cannot extract release archive: {exc}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    return destination / root_name


def _run(
    command: list[str], *, cwd: Path, env: dict[str, str], label: str
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReleaseSmokeError(f"{label} could not run: {exc}") from exc
    if result.returncode != 0:
        diagnostic = (result.stderr or result.stdout).strip()
        if len(diagnostic) > 2000:
            diagnostic = diagnostic[-2000:]
        raise ReleaseSmokeError(
            f"{label} failed with exit {result.returncode}"
            + (f": {diagnostic}" if diagnostic else "")
        )
    return result


def smoke_release(archive_path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="ratchery-release-smoke-") as raw:
        base = Path(raw)
        archive = archive_path if archive_path.is_absolute() else Path.cwd() / archive_path
        package = safe_extract_archive(archive, base / "extract")
        home = base / "home"
        prefix = base / "prefix"
        vault = base / "vault"
        projects = base / "projects"
        temporary = base / "tmp"
        for directory in (home, vault, projects, temporary):
            directory.mkdir(parents=True)

        python_dir = str(Path(sys.executable).resolve().parent)
        environment = {
            "HOME": str(home),
            "PATH": os.pathsep.join((python_dir, "/usr/bin", "/bin")),
            "TMPDIR": str(temporary),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_STATE_HOME": str(home / ".local" / "state"),
            "LANG": "C",
            "LC_ALL": "C",
            "PYTHONUTF8": "1",
        }
        discovered_clients = [
            client
            for client in ("claude", "codex")
            if shutil.which(client, path=environment["PATH"])
        ]
        if discovered_clients:
            raise ReleaseSmokeError(
                "isolated PATH unexpectedly exposes agent clients: "
                + ", ".join(discovered_clients)
            )
        installer = package / "install.sh"
        if not installer.is_file() or installer.is_symlink():
            raise ReleaseSmokeError("archive does not contain a regular install.sh")
        _run(
            [
                "/bin/bash",
                str(installer),
                "--prefix",
                str(prefix),
                "--vault",
                str(vault),
                "--projects-root",
                str(projects),
                "--external-tools",
                "none",
                "--yes",
            ],
            cwd=package,
            env=environment,
            label="artifact installation",
        )

        command = prefix / "bin" / "ratchery"
        compatibility_command = prefix / "bin" / "agent-workspace"
        runtime = prefix / "share" / "ratchery"
        if not command.exists() or not compatibility_command.exists() or not runtime.is_dir():
            raise ReleaseSmokeError(
                "installer did not create the primary command, compatibility command, and runtime"
            )
        _run([str(command), "--help"], cwd=base, env=environment, label="installed CLI help")
        compatibility_version = _run(
            [str(compatibility_command), "--version"],
            cwd=base,
            env=environment,
            label="compatibility CLI version",
        )
        primary_version = _run(
            [str(command), "--version"],
            cwd=base,
            env=environment,
            label="primary CLI version",
        )
        if compatibility_version.stdout != primary_version.stdout:
            raise ReleaseSmokeError("compatibility command does not run the primary runtime")

        # Exercise the package-manager boundary from the installed artifact,
        # not from the source tree. A Formula installs the runtime first and
        # then asks the user to configure a separate HOME explicitly.
        setup_home = base / "package-manager-home"
        setup_vault = base / "package-manager-vault"
        setup_projects = base / "package-manager-projects"
        setup_home.mkdir()
        setup_vault.mkdir()
        setup_environment = dict(environment)
        setup_environment.update(
            {
                "HOME": str(setup_home),
                "XDG_CACHE_HOME": str(setup_home / ".cache"),
                "XDG_CONFIG_HOME": str(setup_home / ".config"),
                "XDG_STATE_HOME": str(setup_home / ".local" / "state"),
            }
        )
        _run(
            [
                str(command),
                "setup",
                "--vault",
                str(setup_vault),
                "--projects-root",
                str(setup_projects),
                "--project-layout",
                "categorized",
                "--external-tools",
                "none",
                "--yes",
            ],
            cwd=base,
            env=setup_environment,
            label="installed package-manager setup",
        )
        _run(
            [str(command), "doctor-global"],
            cwd=base,
            env=setup_environment,
            label="installed package-manager doctor",
        )

        project = projects / "smoke-project"
        project.mkdir()
        _run(["git", "init", "-q"], cwd=project, env=environment, label="fixture setup")
        _run(
            [str(command), "init", "--path", str(project)],
            cwd=project,
            env=environment,
            label="installed project initialization",
        )
        memory = _run(
            [str(command), "memory", "status", "--path", str(project), "--json"],
            cwd=project,
            env=environment,
            label="installed memory status",
        )
        try:
            memory_report = json.loads(memory.stdout)
        except json.JSONDecodeError as exc:
            raise ReleaseSmokeError("installed memory status emitted invalid JSON") from exc
        if (
            not isinstance(memory_report, dict)
            or memory_report.get("backend") != "curated-vault"
            or memory_report.get("pending_handoff") is not False
            or memory_report.get("errors") != []
        ):
            raise ReleaseSmokeError("installed memory status emitted an invalid report")
        _run(
            [
                str(command),
                "tier-set",
                "--path",
                str(project),
                "--users",
                "internal",
                "--no-pii",
                "--no-payments",
                "--no-life-safety",
                "--no-regulated",
                "--data-sensitivity",
                "none",
                "--no-external-exposure",
                "--maturity",
                "prototype",
            ],
            cwd=project,
            env=environment,
            label="fixture risk review",
        )
        doctor = _run(
            [str(command), "doctor", "--path", str(project), "--json"],
            cwd=project,
            env=environment,
            label="installed project doctor",
        )
        try:
            report = json.loads(doctor.stdout)
        except json.JSONDecodeError as exc:
            raise ReleaseSmokeError("installed project doctor emitted invalid JSON") from exc
        if not isinstance(report, dict) or not isinstance(report.get("errors"), list):
            raise ReleaseSmokeError("installed project doctor emitted an invalid report")
        if report["errors"]:
            raise ReleaseSmokeError(
                f"installed project doctor reported {len(report['errors'])} error(s)"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Built <name>-<version>.tar.gz archive")
    args = parser.parse_args(argv)
    try:
        smoke_release(args.archive)
    except ReleaseSmokeError as exc:
        print(f"release smoke failed: {exc}", file=sys.stderr)
        return 1
    print(f"Release smoke passed: {args.archive.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
