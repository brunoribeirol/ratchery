"""Read-only upstream metadata watch for Ratchetry's curated technology radar.

Offline mode is the default. Online mode is explicit and can contact only the
GitHub repository metadata endpoint derived from strict github.com owner/repo
URLs already present in the shipped radar. It never writes the radar, installs
code, or sends repository content.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

import capability_system as cs


REPORT_SCHEMA_VERSION = "1.0.0"
MAX_RESPONSE_BYTES = 1_000_000
MIN_TIMEOUT_SECONDS = 1.0
MAX_TIMEOUT_SECONDS = 60.0
GITHUB_REPO_RE = re.compile(
    r"\Ahttps://github\.com/"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?)/"
    r"(?P<repo>[A-Za-z0-9._-]{1,100}?)(?:\.git)?/?\Z"
)
SPDX_LICENSES = {
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "GPL-2.0",
    "GPL-3.0",
    "ISC",
    "LGPL-2.1",
    "LGPL-3.0",
    "MIT",
    "MPL-2.0",
    "Unlicense",
}


class TechnologyWatchError(ValueError):
    """Raised when a watch input or bounded upstream response is invalid."""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevent an authorization header from following an upstream redirect."""

    def redirect_request(
        self,
        req: Any,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def _open_without_redirect(request: urllib.request.Request, *, timeout: float) -> Any:
    return urllib.request.build_opener(_NoRedirectHandler()).open(
        request,
        timeout=timeout,
    )


def github_coordinates(url: str) -> tuple[str, str] | None:
    """Return strict GitHub owner/repository coordinates or ``None``."""

    match = GITHUB_REPO_RE.fullmatch(url)
    if not match:
        return None
    return match.group("owner"), match.group("repo")


def github_api_url(owner: str, repo: str) -> str:
    """Build the only upstream endpoint online mode is allowed to contact."""

    if github_coordinates(f"https://github.com/{owner}/{repo}") != (owner, repo):
        raise TechnologyWatchError("Unsafe GitHub repository coordinates")
    return f"https://api.github.com/repos/{owner}/{repo}"


def _validated_timeout(timeout: float) -> float:
    if (
        not isinstance(timeout, (int, float))
        or isinstance(timeout, bool)
        or not math.isfinite(timeout)
        or not MIN_TIMEOUT_SECONDS <= timeout <= MAX_TIMEOUT_SECONDS
    ):
        raise TechnologyWatchError(
            f"Timeout must be between {MIN_TIMEOUT_SECONDS:g} and "
            f"{MAX_TIMEOUT_SECONDS:g} seconds"
        )
    return float(timeout)


def fetch_github_metadata(
    owner: str,
    repo: str,
    *,
    token: str | None = None,
    timeout: float = 10.0,
    opener: Callable[..., Any] = _open_without_redirect,
) -> dict[str, Any]:
    """Fetch a bounded public repository metadata object from GitHub."""

    endpoint = github_api_url(owner, repo)
    timeout = _validated_timeout(timeout)
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ratchery-technology-watch/1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(endpoint, headers=headers)
    try:
        with opener(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (OSError, urllib.error.URLError) as exc:
        reason = getattr(exc, "reason", None)
        raw_detail = str(reason) if reason else exc.__class__.__name__
        detail = " ".join(raw_detail.split())[:200]
        raise TechnologyWatchError(
            f"GitHub metadata request failed for {owner}/{repo}: {detail}"
        ) from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise TechnologyWatchError(
            f"GitHub metadata response is too large for {owner}/{repo}"
        )
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TechnologyWatchError(
            f"GitHub metadata response is invalid for {owner}/{repo}"
        ) from exc
    return _validate_metadata(value, owner=owner, repo=repo)


def _date_prefix(value: object) -> dt.date | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return dt.date.fromisoformat(value[:10])
    except ValueError:
        return None


def _license_id(metadata: dict[str, Any]) -> str | None:
    license_data = metadata.get("license")
    if not isinstance(license_data, dict):
        return None
    value = license_data.get("spdx_id")
    return value if isinstance(value, str) and value not in {"", "NOASSERTION"} else None


def _validate_metadata(
    metadata: object,
    *,
    owner: str,
    repo: str,
) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        raise TechnologyWatchError(
            f"GitHub metadata response is not an object for {owner}/{repo}"
        )
    if metadata.get("full_name") != f"{owner}/{repo}":
        raise TechnologyWatchError(
            f"GitHub metadata identity mismatch for {owner}/{repo}"
        )
    for field in ("archived", "disabled"):
        if field in metadata and not isinstance(metadata[field], bool):
            raise TechnologyWatchError(
                f"GitHub metadata field {field} is invalid for {owner}/{repo}"
            )
    for field in ("default_branch", "pushed_at"):
        if field in metadata and metadata[field] is not None and not isinstance(
            metadata[field], str
        ):
            raise TechnologyWatchError(
                f"GitHub metadata field {field} is invalid for {owner}/{repo}"
            )
    license_data = metadata.get("license")
    if license_data is not None and not isinstance(license_data, dict):
        raise TechnologyWatchError(
            f"GitHub metadata field license is invalid for {owner}/{repo}"
        )
    return metadata


def build_watch_report(
    root: Path,
    *,
    online: bool = False,
    token: str | None = None,
    today: dt.date | None = None,
    timeout: float = 10.0,
    fetcher: Callable[..., dict[str, Any]] = fetch_github_metadata,
) -> dict[str, Any]:
    """Build an advisory report without mutating source data."""

    today = today or dt.date.today()
    timeout = _validated_timeout(timeout)
    validation = cs.validate_radar(root, today)
    if not validation["ok"]:
        raise TechnologyWatchError("; ".join(validation["errors"]))

    results: list[dict[str, Any]] = []
    errors: list[str] = []
    for entry in cs.list_radar(root, today):
        result: dict[str, Any] = {
            "id": entry["id"],
            "name": entry["name"],
            "decision": entry["decision"],
            "stale": entry["stale"],
            "source_url": entry["url"],
            "review_needed": entry["stale"],
        }
        coordinates = github_coordinates(entry["url"])
        if coordinates is None:
            result.update(
                {
                    "watch": "manual",
                    "reason": "Source is not a strict GitHub repository URL.",
                }
            )
            results.append(result)
            continue

        owner, repo = coordinates
        result["endpoint"] = github_api_url(owner, repo)
        if not online:
            result["watch"] = "planned"
            results.append(result)
            continue

        try:
            metadata = fetcher(
                owner,
                repo,
                token=token,
                timeout=timeout,
            )
            metadata = _validate_metadata(metadata, owner=owner, repo=repo)
            pushed = _date_prefix(metadata.get("pushed_at"))
            reviewed = dt.date.fromisoformat(entry["last_reviewed"])
            observed_license = _license_id(metadata)
            expected_license = entry.get("license")
            license_mismatch = (
                expected_license in SPDX_LICENSES
                and observed_license is not None
                and observed_license != expected_license
            )
            changed = pushed is not None and pushed > reviewed
            archived = metadata.get("archived") is True
            disabled = metadata.get("disabled") is True
            result.update(
                {
                    "watch": "observed",
                    "archived": archived,
                    "disabled": disabled,
                    "default_branch": metadata.get("default_branch"),
                    "pushed_at": metadata.get("pushed_at"),
                    "upstream_changed_since_review": changed,
                    "observed_license": observed_license,
                    "license_mismatch": license_mismatch,
                    "review_needed": bool(
                        entry["stale"]
                        or changed
                        or archived
                        or disabled
                        or license_mismatch
                    ),
                }
            )
        except TechnologyWatchError as exc:
            message = str(exc)
            errors.append(message)
            result.update(
                {
                    "watch": "error",
                    "error": message,
                    "review_needed": True,
                }
            )
        results.append(result)

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "as_of": today.isoformat(),
        "mode": "online" if online else "offline",
        "network_access": "api.github.com only" if online else "none",
        "entries": results,
        "summary": {
            "total": len(results),
            "review_needed": sum(item["review_needed"] for item in results),
            "manual": sum(item["watch"] == "manual" for item in results),
            "errors": len(errors),
        },
        "errors": errors,
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render the bounded report for a terminal or GitHub Actions summary."""

    lines = [
        "# Ratchetry technology watch",
        "",
        f"- As of: {report['as_of']}",
        f"- Mode: {report['mode']}",
        f"- Network: {report['network_access']}",
        f"- Review needed: {report['summary']['review_needed']}/{report['summary']['total']}",
        "",
        "| Candidate | Decision | Watch | Review needed | Signal |",
        "| --- | --- | --- | --- | --- |",
    ]
    for entry in report["entries"]:
        signals = []
        if entry.get("stale"):
            signals.append("stale")
        if entry.get("upstream_changed_since_review"):
            signals.append("upstream changed")
        if entry.get("archived"):
            signals.append("archived")
        if entry.get("disabled"):
            signals.append("disabled")
        if entry.get("license_mismatch"):
            signals.append("license mismatch")
        if entry.get("error"):
            signals.append("query error")
        if entry.get("watch") == "manual":
            signals.append("manual source")
        lines.append(
            "| {id} | {decision} | {watch} | {needed} | {signals} |".format(
                id=entry["id"],
                decision=entry["decision"],
                watch=entry["watch"],
                needed="yes" if entry["review_needed"] else "no",
                signals=", ".join(signals) or "none",
            )
        )
    if report["errors"]:
        lines.extend(["", "## Query errors", ""])
        lines.extend(f"- {message}" for message in report["errors"])
    lines.extend(
        [
            "",
            "> Advisory only: no source was imported, enabled, installed, or modified.",
        ]
    )
    return "\n".join(lines) + "\n"
