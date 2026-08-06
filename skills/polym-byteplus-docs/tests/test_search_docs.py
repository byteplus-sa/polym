#!/usr/bin/env python3
"""Offline regression tests for the polym-byteplus-docs search helper."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_DIR / "scripts" / "search_docs.py"
INDEX_PATH = SKILL_DIR / "llms.txt"

SPEC = importlib.util.spec_from_file_location("polym_byteplus_search_docs", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load search helper from {SCRIPT_PATH}")
SEARCH_DOCS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SEARCH_DOCS
SPEC.loader.exec_module(SEARCH_DOCS)


def run_helper(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("BYTEPLUS_LLMS_TXT", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


class IndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sections, cls.entries = SEARCH_DOCS.load_entries(INDEX_PATH)

    def test_index_inventory_is_complete_and_unique(self) -> None:
        urls = [entry.url for entry in self.entries]
        self.assertEqual(106, len(self.sections))
        self.assertEqual(106, len(set(self.sections)))
        self.assertEqual(21_184, len(self.entries))
        self.assertEqual(21_184, len(set(urls)))
        self.assertFalse(
            any(entry.section == "Uncategorized" for entry in self.entries)
        )

    def test_bundled_index_is_found_outside_the_repository(self) -> None:
        original_cwd = Path.cwd()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)
                self.assertEqual(INDEX_PATH.resolve(), SEARCH_DOCS.find_index(None))
        finally:
            os.chdir(original_cwd)


class SearchRegressionTests(unittest.TestCase):
    def assert_query_contains(self, expected_url: str, *args: str) -> None:
        result = run_helper(*args)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(expected_url, result.stdout)

    def test_modelark_context_caching_sources(self) -> None:
        args = ("context caching", "--library", "ModelArk", "--limit", "12")
        self.assert_query_contains(
            "https://docs.byteplus.com/en/docs/ModelArk/1398933", *args
        )
        self.assert_query_contains(
            "https://docs.byteplus.com/en/docs/ModelArk/1396491", *args
        )

    def test_vod_server_side_upload_and_server_sdk_sources(self) -> None:
        self.assert_query_contains(
            "https://docs.byteplus.com/en/docs/byteplus-vod/docs-server-side-uploads",
            "server-side uploads",
            "--library",
            "Video on Demand",
            "--limit",
            "8",
        )
        self.assert_query_contains(
            "https://docs.byteplus.com/en/docs/byteplus-vod/docs-server-sdk-overview",
            "server SDK",
            "--library",
            "Video on Demand",
            "--limit",
            "8",
        )

    def test_iam_custom_policy_sources(self) -> None:
        args = ("custom policy", "--library", "IAM", "--limit", "12")
        self.assert_query_contains(
            "https://docs.byteplus.com/en/docs/IAM/creating-a-user-custom-policy",
            *args,
        )
        self.assert_query_contains(
            "https://docs.byteplus.com/en/docs/IAM/what-is-the-policy-syntax",
            *args,
        )

    def test_json_output_has_stable_fields(self) -> None:
        result = run_helper(
            "context caching",
            "--library",
            "ModelArk",
            "--limit",
            "3",
            "--json",
        )
        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(3, len(payload))
        self.assertEqual(
            {"score", "section", "title", "url"},
            set(payload[0]),
        )

    def test_empty_query_fails_with_guidance(self) -> None:
        result = run_helper()
        self.assertEqual(2, result.returncode)
        self.assertIn("Provide a query or use --list-libraries", result.stderr)

    def test_invalid_limit_fails_with_guidance(self) -> None:
        result = run_helper("ModelArk", "--limit", "0")
        self.assertEqual(2, result.returncode)
        self.assertIn("--limit must be positive", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
