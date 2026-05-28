#!/usr/bin/env python3
"""Lark document client abstraction for Mira and local-agent runs."""
import json
import os
import re
import shutil
import subprocess
import importlib.util
from pathlib import Path

from lark_helpers import doc_create, doc_edit_inplace, doc_read  # noqa: E402

_platform_spec = importlib.util.spec_from_file_location(
    "slack_digest_platform",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "platform.py"),
)
_platform = importlib.util.module_from_spec(_platform_spec)
_platform_spec.loader.exec_module(_platform)
is_mira = _platform.is_mira


class LarkCliNotReady(RuntimeError):
    pass


class LarkDocClient:
    def create_doc(self, title, markdown_path):
        raise NotImplementedError

    def read_doc(self, doc_url, output_format="markdown"):
        raise NotImplementedError

    def edit_doc(self, doc_url, edits_path):
        raise NotImplementedError

    def move_doc(self, doc_url, folder_token):
        raise NotImplementedError


def _extract_doc_url(text):
    match = re.search(r"https://[^\s\"')]+/(?:docx|docs|doc)/[A-Za-z0-9_-]+", text)
    if match:
        return match.group(0)
    try:
        data = json.loads(text)
    except Exception:
        return text.strip()
    for key in ("url", "doc_url", "document_url"):
        if isinstance(data, dict) and data.get(key):
            return data[key]
    blob = json.dumps(data, ensure_ascii=False)
    match = re.search(r"https://[^\s\"')]+/(?:docx|docs|doc)/[A-Za-z0-9_-]+", blob)
    return match.group(0) if match else text.strip()


def _extract_file_token(doc_url):
    match = re.search(r"/(?:docx|docs|doc)/([A-Za-z0-9_-]+)", doc_url)
    if match:
        return match.group(1)
    return doc_url.rstrip("/").split("/")[-1]


class MiraLarkDocClient(LarkDocClient):
    def __init__(self, skill_path=None):
        self.skill_path = skill_path or os.environ.get(
            "LARK_DOCS_SKILL_PATH",
            "/data/plugins/market/lark-docs-skill/skills/lark-docs-skill",
        )

    def create_doc(self, title, markdown_path):
        result = doc_create(title, markdown_path, self.skill_path)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Mira Lark doc create failed")
        return _extract_doc_url(result.stdout)

    def read_doc(self, doc_url, output_format="markdown"):
        fmt = "markdown" if output_format == "markdown" else output_format
        result = doc_read(doc_url, self.skill_path, fmt=fmt)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Mira Lark doc read failed")
        return result.stdout

    def edit_doc(self, doc_url, edits_path):
        result = doc_edit_inplace(doc_url, edits_path, self.skill_path)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Mira Lark doc edit failed")

    def move_doc(self, doc_url, folder_token):
        drive_path = os.environ.get(
            "LARK_DRIVE_WIKI_SKILL_PATH",
            "/data/plugins/market/lark-drive-wiki-skill/skills/lark-drive-wiki-skill",
        )
        cmd = ["python3.11", "-m", "lark_drive_wiki", "move", doc_url, folder_token]
        result = subprocess.run(cmd, cwd=drive_path, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Mira Lark doc move failed")


def _default_lark_cli():
    configured = os.environ.get("LARK_CLI_PATH")
    if configured:
        return configured
    homebrew = "/opt/homebrew/bin/lark-cli"
    if os.path.exists(homebrew):
        return homebrew
    return "lark-cli"


class LocalLarkCliDocClient(LarkDocClient):
    def __init__(self, cli=None):
        self.cli = cli or _default_lark_cli()
        self._ensure_ready()

    def _run(self, args, cwd=None):
        result = subprocess.run([self.cli] + args, capture_output=True, text=True, env=_lark_cli_env(), cwd=cwd)
        if result.returncode != 0:
            msg = (result.stderr or result.stdout).strip()
            if _looks_like_auth_error(msg):
                raise LarkCliNotReady(_setup_message())
            raise RuntimeError(msg or f"lark-cli {' '.join(args)} failed")
        return result.stdout

    def _ensure_ready(self):
        if not shutil.which(self.cli):
            raise LarkCliNotReady(_setup_message())
        status = subprocess.run(
            [self.cli, "auth", "status"],
            capture_output=True,
            text=True,
            env=_lark_cli_env(),
        )
        text = status.stdout + status.stderr
        if status.returncode != 0 or _looks_like_auth_error(text) or not _has_real_user_auth(status.stdout):
            raise LarkCliNotReady(_setup_message())

    def create_doc(self, title, markdown_path):
        markdown_content = Path(markdown_path).read_text(encoding="utf-8")
        stdout = self._run([
            "docs", "+create",
            "--title", title,
            "--markdown", markdown_content,
        ])
        return _extract_doc_url(stdout)

    def read_doc(self, doc_url, output_format="markdown"):
        # lark-cli currently returns JSON/pretty/table formats; callers that need
        # markdown can parse the JSON payload or use the returned pretty content.
        fmt = "json" if output_format == "markdown" else output_format
        return self._run(["docs", "+fetch", "--doc", doc_url, "--format", fmt])

    def edit_doc(self, doc_url, edits_path):
        with open(edits_path) as f:
            raw = f.read()
        try:
            edits = json.loads(raw)
        except json.JSONDecodeError:
            self._run([
                "docs", "+update",
                "--doc", doc_url,
                "--mode", "overwrite",
                "--markdown", raw,
            ])
            return

        if isinstance(edits, dict):
            edits = [edits]
        for edit in edits:
            cmd = [
                "docs", "+update",
                "--doc", doc_url,
                "--mode", edit.get("mode", "append"),
            ]
            if edit.get("selection_with_ellipsis"):
                cmd += ["--selection-with-ellipsis", edit["selection_with_ellipsis"]]
            if edit.get("selection_by_title"):
                cmd += ["--selection-by-title", edit["selection_by_title"]]
            if edit.get("markdown") is not None:
                cmd += ["--markdown", edit["markdown"]]
            self._run(cmd)

    def move_doc(self, doc_url, folder_token):
        self._run([
            "drive", "+move",
            "--file-token", _extract_file_token(doc_url),
            "--folder-token", folder_token,
            "--type", "docx",
        ])


def _looks_like_auth_error(text):
    lowered = text.lower()
    needles = (
        "not logged in",
        "unauthorized",
        "authorization",
        "auth required",
        "login",
        "token expired",
        "invalid token",
    )
    return any(needle in lowered for needle in needles)


def _lark_cli_env():
    env = os.environ.copy()
    auth_home = os.environ.get("LARK_CLI_AUTH_HOME") or str(Path.home())
    env["HOME"] = auth_home
    if os.environ.get("LARK_CLI_AUTH_HOME"):
        env["XDG_CONFIG_HOME"] = os.path.join(auth_home, ".config")
        env["XDG_DATA_HOME"] = os.path.join(auth_home, ".local", "share")
        env["XDG_CACHE_HOME"] = os.path.join(auth_home, ".cache")
    return env


def _has_real_user_auth(text):
    try:
        data = json.loads(text)
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    if data.get("identity") != "user":
        return False
    if not (data.get("userOpenId") or data.get("userName")):
        return False
    return str(data.get("tokenStatus", "")).lower() not in ("missing", "invalid", "expired")


def _setup_message():
    return (
        "Lark CLI is required for Codex / Claude Code local mode because Mira "
        "document skills are not available here. Please install and login to "
        "Lark CLI with your normal Feishu/Lark account, then run setup again."
    )


def get_lark_doc_client():
    if is_mira():
        return MiraLarkDocClient()
    return LocalLarkCliDocClient()
