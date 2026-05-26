#!/usr/bin/env python3
"""Minimal local-mode Lark CLI readiness and target setup helper."""
import argparse
import datetime
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from setup_state_guard import require_state_choice  # noqa: E402
from schedule_prompt import schedule_prompt_once  # noqa: E402

HOME = os.path.expanduser("~")
ROOT = os.environ.get("SLACK_DIGEST_HOME") or os.path.join(HOME, ".slack-daily-digest")
STATUS_PATH = os.path.join(ROOT, "local_platform.json")
CREDS_PATH = os.path.join(ROOT, "credentials.json")
INDEX_PATH = os.path.join(ROOT, "index.json")
SETUP_STATE_PATH = os.path.join(ROOT, "lark_cli_setup.json")
ROUTINE_PATH = os.path.join(ROOT, "routine.json")
INDEX_TITLE = "Slack Daily Digest · Index"

MESSAGE = (
    "Lark CLI is required for Codex / Claude Code local mode because Mira "
    "document skills are not available here.\n"
    "Please install and login to Lark CLI with your normal Feishu/Lark account."
)
SETUP_PENDING_MESSAGE = (
    "auth_pending: Open this URL, complete login, then rerun setup."
)

URL_RE = re.compile(r"https?://[^\s)>'\"]+")
AUTH_DOMAINS = ("docs", "drive", "im", "contact")
PENDING_TTL_SECONDS = 15 * 60


def lark_cli_auth_home():
    return os.environ.get("LARK_CLI_AUTH_HOME") or str(Path.home())


def lark_cli_path():
    configured = os.environ.get("LARK_CLI_PATH")
    if configured:
        return configured
    homebrew = "/opt/homebrew/bin/lark-cli"
    if os.path.exists(homebrew):
        return homebrew
    return shutil.which("lark-cli")


def lark_cli_env():
    env = os.environ.copy()
    auth_home = lark_cli_auth_home()
    env["HOME"] = auth_home
    if os.environ.get("LARK_CLI_AUTH_HOME"):
        env["XDG_CONFIG_HOME"] = os.path.join(auth_home, ".config")
        env["XDG_DATA_HOME"] = os.path.join(auth_home, ".local", "share")
        env["XDG_CACHE_HOME"] = os.path.join(auth_home, ".cache")
    return env


def run(cmd):
    env = lark_cli_env() if cmd and os.path.basename(cmd[0]) == "lark-cli" else None
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp, path)


def clear_pending():
    state = load_json(SETUP_STATE_PATH)
    if state.get("auth_pending"):
        state.pop("auth_pending", None)
        save_json(SETUP_STATE_PATH, state)


def remember_pending(kind, url, command):
    pending = {
        "kind": kind,
        "url": url,
        "command": command,
        "created_at": int(time.time()),
        "expires_at": int(time.time()) + PENDING_TTL_SECONDS,
    }
    state = load_json(SETUP_STATE_PATH)
    state["auth_pending"] = pending
    save_json(SETUP_STATE_PATH, state)
    return pending


def print_pending(pending):
    print("auth_pending")
    print("Auth URL:")
    print(pending["url"])
    print("Open this URL, complete login, then rerun setup.")


def existing_pending_valid():
    pending = load_json(SETUP_STATE_PATH).get("auth_pending") or {}
    if not pending.get("url"):
        return None
    if int(time.time()) >= int(pending.get("expires_at", 0)):
        return None
    return pending


def available_auth_commands():
    help_result = run([lark_cli_path(), "auth", "--help"])
    text = help_result.stdout + help_result.stderr
    return {
        "status": "status" in text,
        "login": "login" in text,
        "list": "list" in text,
    }


def scoped_auth_login_command():
    cli = lark_cli_path()
    help_result = run([cli, "auth", "login", "--help"])
    text = help_result.stdout + help_result.stderr
    if "--domain" in text and all(domain in text for domain in AUTH_DOMAINS):
        cmd = [cli, "auth", "login", "--domain", ",".join(AUTH_DOMAINS)]
        if "--no-wait" in text:
            cmd.append("--no-wait")
        return cmd
    if "--recommend" in text:
        cmd = [cli, "auth", "login", "--recommend"]
        if "--no-wait" in text:
            cmd.append("--no-wait")
        return cmd
    return None


def print_manual_login_command():
    print("Automatic scoped Lark CLI user login is not available for this lark-cli build.")
    print("Run this in the same HOME/XDG environment, then rerun setup_lark_cli.py:")
    print(f"lark-cli auth login --domain {','.join(AUTH_DOMAINS)} --no-wait")


def available_config_commands():
    help_result = run([lark_cli_path(), "config", "--help"])
    text = help_result.stdout + help_result.stderr
    return {
        "init": "init" in text,
    }


def auth_payload(result):
    text = (result.stdout or "").strip()
    try:
        data = json.loads(text)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def is_real_user_auth(result):
    data = auth_payload(result)
    if not data:
        return False
    if data.get("identity") != "user":
        return False
    if not (data.get("userOpenId") or data.get("userName")):
        return False
    status = str(data.get("tokenStatus", "")).lower()
    return status not in ("missing", "invalid", "expired")


def is_auth_ready(result):
    text = result.stdout + result.stderr
    lowered = text.lower()
    if result.returncode != 0:
        return False
    if "not configured" in lowered or "not logged in" in lowered:
        return False
    if "only bot" in lowered or "\"identity\"" in lowered and "\"user\"" not in lowered:
        return False
    if "login" in lowered and "not" in lowered:
        return False
    return is_real_user_auth(result)


def needs_config(result):
    text = (result.stdout + result.stderr).lower()
    return "not configured" in text or "config init" in text


def needs_user_login(result):
    text = (result.stdout + result.stderr).lower()
    if "not logged in" in text or "only bot" in text:
        return True
    return result.returncode == 0 and not is_real_user_auth(result)


def required_credential_names():
    creds = load_json(CREDS_PATH)
    env_map = {
        "SLACK_USER_TOKEN": "slack_user_token",
        "LARK_APP_ID": "lark_app_id",
        "LARK_APP_SECRET": "lark_app_secret",
        "LARK_USER_EMAIL": "lark_user_email",
    }
    missing = []
    for env_name, key in env_map.items():
        if not (creds.get(key) or os.environ.get(env_name)):
            missing.append(env_name)
    return missing


def has_lark_target():
    creds = load_json(CREDS_PATH)
    index = load_json(INDEX_PATH)
    env_targets = ("LARK_CHAT_ID", "LARK_FOLDER_TOKEN", "LARK_DOC_TOKEN", "LARK_TARGET")
    cred_targets = ("lark_chat_id", "lark_folder_token", "lark_doc_token", "lark_target")
    if any(os.environ.get(name) for name in env_targets):
        return True
    if any(creds.get(name) for name in cred_targets):
        return True
    return bool(index.get("index_doc_url") or index.get("folder_token"))


def extract_doc_metadata(text):
    data = {}
    try:
        data = json.loads(text)
    except Exception:
        data = {}
    blob = json.dumps(data, ensure_ascii=False) if data else text
    url_match = re.search(r"https://[^\s\"')]+/(?:docx|docs|doc)/([A-Za-z0-9_-]+)", blob)
    token = None
    for key in ("document_id", "documentId", "doc_token", "docToken", "file_token", "fileToken", "token"):
        if isinstance(data, dict) and data.get(key):
            token = data[key]
            break
    if url_match:
        return {"index_doc_url": url_match.group(0), "index_doc_id": url_match.group(1)}
    if token:
        return {"index_doc_id": token}
    return {}


def save_index(metadata):
    index = load_json(INDEX_PATH)
    index.update({k: v for k, v in metadata.items() if v})
    index.setdefault("title", INDEX_TITLE)
    save_json(INDEX_PATH, index)
    return index


def save_credential_fields(fields):
    creds = load_json(CREDS_PATH)
    creds.update({k: v for k, v in fields.items() if v})
    save_json(CREDS_PATH, creds)


def configured_target(args):
    creds = load_json(CREDS_PATH)
    if args.lark_doc_token:
        return "doc", args.lark_doc_token
    if args.lark_folder_token:
        return "folder", args.lark_folder_token
    if args.lark_chat_id:
        return "chat", args.lark_chat_id
    for env_name, kind in (
        ("LARK_DOC_TOKEN", "doc"),
        ("LARK_FOLDER_TOKEN", "folder"),
        ("LARK_CHAT_ID", "chat"),
    ):
        if os.environ.get(env_name):
            return kind, os.environ[env_name]
    for key, kind in (
        ("lark_doc_token", "doc"),
        ("lark_folder_token", "folder"),
        ("lark_chat_id", "chat"),
    ):
        if creds.get(key):
            return kind, creds[key]
    index = load_json(INDEX_PATH)
    if index.get("index_doc_url") or index.get("index_doc_id"):
        return "index", index.get("index_doc_url") or index.get("index_doc_id")
    return None, None


def create_index_doc(folder_token=None):
    body = (
        "## Daily Digest List (newest on top)\n\n"
        "This document is auto-maintained by Slack Daily Digest.\n"
    )
    cmd = [
        lark_cli_path(), "docs", "+create",
        "--title", INDEX_TITLE,
        "--markdown", body,
    ]
    if folder_token:
        cmd += ["--folder-token", folder_token]
    result = run(cmd)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "unknown error"
        print("target_setup_failed: automatic index doc creation failed")
        print(detail)
        print("Provide LARK_FOLDER_TOKEN or LARK_DOC_TOKEN, then rerun setup.")
        return False
    metadata = extract_doc_metadata(result.stdout + result.stderr)
    if not metadata:
        print("target_setup_failed: created doc but could not parse doc token or URL")
        print("Provide LARK_DOC_TOKEN, then rerun setup.")
        return False
    if folder_token:
        metadata["folder_token"] = folder_token
    save_index(metadata)
    print(f"target_configured: index doc saved to {INDEX_PATH}")
    if metadata.get("index_doc_url"):
        print("Index URL:")
        print(metadata["index_doc_url"])
    return True


def resolve_lark_target(args):
    index = load_json(INDEX_PATH)
    if index.get("index_doc_url") or index.get("index_doc_id"):
        print("target_configured: reusing saved index doc")
        return True

    kind, value = configured_target(args)
    if kind == "doc":
        save_index({"index_doc_id": value})
        print("target_configured: using provided LARK_DOC_TOKEN")
        return True
    if kind == "folder":
        return create_index_doc(folder_token=value)
    if kind == "chat":
        save_credential_fields({"lark_chat_id": value})
        print("target_configured: using provided LARK_CHAT_ID for IM delivery")
        return True
    if args.auto_create_index:
        return create_index_doc()

    state = load_json(SETUP_STATE_PATH)
    if not state.get("target_prompted"):
        state["target_prompted"] = {
            "created_at": int(time.time()),
            "message": "folder_or_auto_index",
        }
        save_json(SETUP_STATE_PATH, state)
    print("missing_lark_target")
    print("No Lark target is configured yet. Would you like to:")
    print("A) provide a LARK_FOLDER_TOKEN so I can create the index doc there, or")
    print("B) let me create a default 'Slack Daily Digest · Index' doc automatically?")
    print("For A, rerun: python3 scripts/setup_lark_cli.py --lark-folder-token <token>")
    print("For B, rerun: python3 scripts/setup_lark_cli.py --auto-create-index")
    return False


def stream_login_flow(cmd):
    print(f"Starting Lark CLI setup: {' '.join(cmd)}", flush=True)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=lark_cli_env() if cmd and os.path.basename(cmd[0]) == "lark-cli" else None,
    )
    seen_url = None
    setup_pending = False
    captured = []

    while True:
        line = proc.stdout.readline() if proc.stdout else ""
        if not line:
            if proc.poll() is not None:
                break
            continue
        captured.append(line)
        match = URL_RE.search(line)
        if match and not seen_url:
            seen_url = match.group(0)
            pending = remember_pending("browser_login", seen_url, cmd)
            print_pending(pending)
            setup_pending = True
            break

    if proc.poll() is None:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    return proc.returncode, seen_url, setup_pending, "".join(captured)


def run_setup_command(cmd, kind):
    if "--no-wait" in cmd:
        result = run(cmd)
        output = result.stdout + result.stderr
        match = URL_RE.search(output)
        if match:
            pending = remember_pending(kind, match.group(0), cmd)
            print_pending(pending)
            return True
        print("Lark CLI setup did not print a login URL.")
        if output.strip():
            print(output.strip())
        print("Manual command:")
        print(" ".join(cmd))
        if result.returncode != 0:
            print(f"Lark CLI setup command exited with code {result.returncode}.")
        return False

    code, seen_url, setup_pending, output = stream_login_flow(cmd)
    if not seen_url:
        print("Lark CLI setup did not print a login URL.")
        if output.strip():
            print(output.strip())
        print("Manual command:")
        print(" ".join(cmd))
    if code not in (0, None) and not setup_pending:
        print(f"Lark CLI setup command exited with code {code}.")
    return setup_pending


def run_login_setup(status, commands):
    print(f"Lark CLI auth is not available from LARK_CLI_AUTH_HOME: {lark_cli_auth_home()}")
    config_commands = available_config_commands()
    if needs_config(status):
        if not config_commands.get("init"):
            print(MESSAGE)
            print("This lark-cli build does not expose a supported config command.")
            print("Manual command:")
            print("lark-cli config init --new --lang en")
            return False
        setup_pending = run_setup_command([lark_cli_path(), "config", "init", "--new", "--lang", "en"],
                                          "config_init")
        if setup_pending:
            return False
        status = run([lark_cli_path(), "auth", "status"])
        if is_auth_ready(status):
            return status

    if commands.get("login") and needs_user_login(status):
        cmd = scoped_auth_login_command()
        if not cmd:
            print_manual_login_command()
            return False
        setup_pending = run_setup_command(cmd, "user_auth")
        if setup_pending:
            return False
    elif not commands.get("login"):
        print(MESSAGE)
        print("This lark-cli build does not expose a supported login command.")
        print("Manual command:")
        print(f"lark-cli auth login --domain {','.join(AUTH_DOMAINS)} --no-wait")
        return False
    else:
        setup_pending = False

    status_after = run([lark_cli_path(), "auth", "status"])
    if is_auth_ready(status_after):
        return status_after

    if setup_pending:
        print("Lark CLI auth is pending browser login completion.")
        print(SETUP_PENDING_MESSAGE)
    else:
        print(MESSAGE)
        print("Lark CLI auth is still missing after setup.")
    text = (status_after.stderr or status_after.stdout).strip()
    if text:
        print(text)
    return False


def write_status(cli_path, auth_stdout):
    os.makedirs(ROOT, exist_ok=True)
    payload = {
        "platform": "local_agent",
        "lark_cli_path": cli_path,
        "lark_cli_ready": True,
        "checked_at": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "auth_status": auth_stdout.strip(),
    }
    tmp = STATUS_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp, STATUS_PATH)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto-create-index", action="store_true",
                        help="create the default Slack Daily Digest index doc with Lark CLI user auth")
    parser.add_argument("--lark-folder-token",
                        help="folder token where the default index doc should be created")
    parser.add_argument("--lark-doc-token",
                        help="existing index document token to save")
    parser.add_argument("--lark-chat-id",
                        help="optional IM delivery chat id")
    args = parser.parse_args()

    if not require_state_choice():
        return 2

    cli_path = lark_cli_path()
    if not cli_path:
        print(MESSAGE)
        print("Install command depends on your environment; after install, run: lark-cli auth login")
        return 1

    commands = available_auth_commands()
    if not commands.get("status"):
        print(MESSAGE)
        print("This lark-cli build does not expose `auth status`; update lark-cli, then run setup again.")
        return 1

    status = run([cli_path, "auth", "status"])
    if is_auth_ready(status):
        print("Lark CLI auth valid using LARK_CLI_AUTH_HOME.")
        clear_pending()
    else:
        pending = existing_pending_valid()
        if pending:
            print_pending(pending)
            return 1
        status = run_login_setup(status, commands)
        if not status:
            return 1
        clear_pending()

    doctor = run([cli_path, "doctor", "--offline"])
    if doctor.returncode != 0:
        print(MESSAGE)
        print((doctor.stderr or doctor.stdout).strip())
        return 1

    missing = required_credential_names()
    if missing:
        print("missing_credentials: " + ", ".join(missing))
        return 2

    if not resolve_lark_target(args):
        return 2

    write_status(cli_path, status.stdout)
    print(f"OK: Lark CLI is ready for local mode. Status saved to {STATUS_PATH}")
    schedule_prompt_once()
    return 0


if __name__ == "__main__":
    sys.exit(main())
