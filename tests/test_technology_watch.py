#!/usr/bin/env python3
"""Contracts for the read-only curated technology watcher."""

from __future__ import annotations

import datetime as dt
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

import technology_watch as tw  # noqa: E402


class FakeResponse:
    def __init__(self, value: object) -> None:
        self.payload = json.dumps(value).encode()

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, _limit: int) -> bytes:
        return self.payload


class TechnologyWatchTests(unittest.TestCase):
    def test_github_coordinates_are_strict_and_allow_list_the_host(self) -> None:
        self.assertEqual(
            tw.github_coordinates("https://github.com/openai/plugins"),
            ("openai", "plugins"),
        )
        for unsafe in (
            "http://github.com/openai/plugins",
            "https://evil.example/openai/plugins",
            "https://github.com/openai/plugins/issues",
            "https://github.com/openai/plugins?x=1",
            "https://github.com/openai/plugins@evil.example",
        ):
            with self.subTest(unsafe=unsafe):
                self.assertIsNone(tw.github_coordinates(unsafe))

    def test_offline_report_never_calls_the_fetcher(self) -> None:
        fetcher = mock.Mock(side_effect=AssertionError("network was attempted"))
        report = tw.build_watch_report(
            ROOT,
            online=False,
            today=dt.date(2026, 10, 6),
            fetcher=fetcher,
        )
        self.assertEqual(report["network_access"], "none")
        self.assertFalse(fetcher.called)
        self.assertTrue(
            any(item["watch"] == "planned" for item in report["entries"])
        )
        self.assertTrue(
            any(item["watch"] == "manual" for item in report["entries"])
        )

    def test_online_report_flags_change_archive_and_license_mismatch(self) -> None:
        def fetcher(owner: str, repo: str, **_kwargs: object) -> dict[str, object]:
            return {
                "full_name": f"{owner}/{repo}",
                "default_branch": "main",
                "pushed_at": "2026-10-07T10:00:00Z",
                "archived": owner == "openai",
                "disabled": False,
                "license": {"spdx_id": "Apache-2.0"},
            }

        report = tw.build_watch_report(
            ROOT,
            online=True,
            today=dt.date(2026, 10, 8),
            fetcher=fetcher,
        )
        observed = [item for item in report["entries"] if item["watch"] == "observed"]
        self.assertTrue(observed)
        self.assertTrue(all(item["upstream_changed_since_review"] for item in observed))
        self.assertTrue(any(item["archived"] for item in observed))
        self.assertTrue(any(item["review_needed"] for item in observed))

    def test_fetcher_bounds_endpoint_and_does_not_render_token(self) -> None:
        captured: dict[str, object] = {}

        def opener(request: object, *, timeout: float) -> FakeResponse:
            captured["url"] = request.full_url  # type: ignore[attr-defined]
            captured["headers"] = dict(request.header_items())  # type: ignore[attr-defined]
            captured["timeout"] = timeout
            return FakeResponse(
                {
                    "full_name": "openai/plugins",
                    "default_branch": "main",
                    "pushed_at": "2026-10-06T00:00:00Z",
                    "archived": False,
                    "disabled": False,
                    "license": {"spdx_id": "MIT"},
                }
            )

        metadata = tw.fetch_github_metadata(
            "openai", "plugins", token="secret-value", timeout=3.0, opener=opener
        )
        self.assertEqual(captured["url"], "https://api.github.com/repos/openai/plugins")
        self.assertEqual(captured["timeout"], 3.0)
        self.assertEqual(metadata["default_branch"], "main")
        rendered = json.dumps(metadata) + tw.render_markdown(
            {
                "as_of": "2026-10-06",
                "mode": "online",
                "network_access": "api.github.com only",
                "summary": {"review_needed": 0, "total": 0},
                "entries": [],
                "errors": [],
            }
        )
        self.assertNotIn("secret-value", rendered)
        self.assertEqual(
            captured["headers"]["Authorization"],  # type: ignore[index]
            "Bearer secret-value",
        )

    def test_default_fetcher_disables_redirects(self) -> None:
        with mock.patch.object(tw.urllib.request, "build_opener") as build_opener:
            response = FakeResponse(
                {"full_name": "openai/plugins", "default_branch": "main"}
            )
            build_opener.return_value.open.return_value = response

            tw.fetch_github_metadata("openai", "plugins")

        handler = build_opener.call_args.args[0]
        self.assertIsInstance(handler, tw.urllib.request.HTTPRedirectHandler)
        self.assertIsNone(
            handler.redirect_request(
                mock.Mock(),
                mock.Mock(),
                302,
                "Found",
                {},
                "https://evil.example/redirect",
            )
        )

    def test_timeout_and_response_identity_fail_closed(self) -> None:
        for timeout in (0.0, 61.0, float("nan"), float("inf")):
            with self.subTest(timeout=timeout):
                with self.assertRaises(tw.TechnologyWatchError):
                    tw.fetch_github_metadata("openai", "plugins", timeout=timeout)

        def wrong_repo(_request: object, *, timeout: float) -> FakeResponse:
            self.assertEqual(timeout, 3.0)
            return FakeResponse({"full_name": "attacker/other"})

        with self.assertRaisesRegex(
            tw.TechnologyWatchError,
            "identity mismatch",
        ):
            tw.fetch_github_metadata(
                "openai",
                "plugins",
                timeout=3.0,
                opener=wrong_repo,
            )

        def malformed_fetcher(
            owner: str,
            repo: str,
            **_kwargs: object,
        ) -> dict[str, object]:
            return {"full_name": f"{owner}/{repo}", "archived": "false"}

        report = tw.build_watch_report(
            ROOT,
            online=True,
            fetcher=malformed_fetcher,
        )
        self.assertGreater(report["summary"]["errors"], 0)
        self.assertTrue(
            all(
                "field archived is invalid" in message
                for message in report["errors"]
            )
        )

    def test_workflow_is_daily_read_only_and_pinned(self) -> None:
        text = (ROOT / ".github/workflows/technology-watch.yml").read_text()
        self.assertIn('cron: "17 11 * * *"', text)
        self.assertIn("permissions: {}", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("issues: write", text)
        self.assertNotIn("pull-requests: write", text)
        self.assertNotIn("pull_request_target", text)
        self.assertRegex(text, r"actions/checkout@[0-9a-f]{40}")
        self.assertIn("agent_workspace.py radar watch --online", text)


if __name__ == "__main__":
    unittest.main()
