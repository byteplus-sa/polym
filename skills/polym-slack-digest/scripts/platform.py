#!/usr/bin/env python3
"""Execution platform detection for Slack Daily Digest."""
import os

MIRA = "mira"
LOCAL_AGENT = "local_agent"
VALID_PLATFORMS = {MIRA, LOCAL_AGENT}

# Host scheduler backend identifiers
HOST_SCHEDULER_CLAUDE_CODE = "claude_code"
HOST_SCHEDULER_CODEX = "codex"
GENERIC_LOCAL = "generic_local"  # no host routine — local OS scheduler only


def detect_platform():
    override = os.environ.get("SLACK_DIGEST_PLATFORM", "").strip().lower()
    if override:
        if override not in VALID_PLATFORMS:
            raise ValueError(
                "SLACK_DIGEST_PLATFORM must be 'mira' or 'local_agent', "
                f"got {override!r}"
            )
        return override

    mira_env = (
        "MIRA_WORKSPACE_ID",
        "MIRA_TASK_ID",
        "MIRA_SKILL_ID",
        "MIRA_RUNTIME",
    )
    if any(os.environ.get(name) for name in mira_env):
        return MIRA

    mira_paths = (
        "/data/plugins/market/lark-docs-skill/skills/lark-docs-skill",
        "/data/plugins/market/lark-drive-wiki-skill/skills/lark-drive-wiki-skill",
    )
    if any(os.path.exists(path) for path in mira_paths):
        return MIRA

    return LOCAL_AGENT


def is_mira():
    return detect_platform() == MIRA


def is_local_agent():
    return detect_platform() == LOCAL_AGENT


def detect_host_scheduler():
    """Return the host scheduler type available in this environment, or None.

    Priority:
      1. SLACK_DIGEST_HOST_SCHEDULER env var (explicit override; set to 'none' to disable)
      2. Codex sandbox markers
      3. Claude Code markers (~/.claude directory present)
      4. None → no host scheduler, use local OS scheduler
    """
    override = os.environ.get("SLACK_DIGEST_HOST_SCHEDULER", "").strip().lower()
    if override:
        if override == "none":
            return None
        if override in (HOST_SCHEDULER_CLAUDE_CODE, HOST_SCHEDULER_CODEX):
            return override
        # Unknown value — treat as unavailable
        return None

    # Codex sandbox
    if os.environ.get("CODEX_SANDBOX_ENABLED") or os.environ.get("CODEX_RUNTIME"):
        return HOST_SCHEDULER_CODEX

    # Claude Code: ~/.claude directory is created by Claude Code CLI installation
    claude_dir = os.path.join(os.path.expanduser("~"), ".claude")
    if os.path.isdir(claude_dir):
        return HOST_SCHEDULER_CLAUDE_CODE

    return None


def has_host_scheduler():
    """Return True if a host routine scheduler is available."""
    return detect_host_scheduler() is not None


def describe_host_scheduler():
    """Return a description dict for the detected host scheduler environment.

    Keys:
      host               — identifier: "codex", "claude_code", or None
      label              — human-readable environment name
      routine_api        — MCP tool / SDK call to create a routine, or None
      create_method      — agent instruction keyword used in SKILL.md
      durability         — "durable_ui" if routines persist and appear in host UI, else None
      session_persistent — True if routines survive session restart
      ui_visible         — True if routines appear in the host UI
      notes              — list of important behavioral notes for the agent
    """
    host = detect_host_scheduler()

    if host == HOST_SCHEDULER_CODEX:
        return {
            "host": HOST_SCHEDULER_CODEX,
            "label": "Codex workspace",
            "routine_api": "mcp__scheduled-tasks__create_scheduled_task",
            "create_method": "mcp_scheduled_tasks",
            "durability": "durable_ui",
            "session_persistent": True,
            "ui_visible": True,
            "notes": [
                "Use mcp__scheduled-tasks__create_scheduled_task with a daily cron expression "
                "(e.g. '0 10 * * *' for 10:00). Create one task per digest slot.",
                "Scheduled tasks are durable: they persist across session restarts, "
                "run in the background, and are visible/manageable in the Codex routines UI.",
                "After creation record IDs: "
                "python3 scripts/local_routine.py set-backend --backend host_routine "
                "--durability durable_ui "
                "--routine-ids <id1>,<id2> --retry-ids <r1>,<r2> [--catchup-ids <c1>]",
            ],
        }

    if host == HOST_SCHEDULER_CLAUDE_CODE:
        return {
            "host": HOST_SCHEDULER_CLAUDE_CODE,
            "label": "Claude Code workspace",
            "routine_api": "mcp__scheduled-tasks__create_scheduled_task",
            "create_method": "mcp_scheduled_tasks",
            "durability": "durable_ui",
            "session_persistent": True,
            "ui_visible": True,
            "notes": [
                "Use mcp__scheduled-tasks__create_scheduled_task with a daily cron expression "
                "(e.g. '0 10 * * *' for 10:00). Create one task per digest slot.",
                "Scheduled tasks are durable: they persist across session restarts, "
                "run in the background, and are visible/manageable in the Claude Code "
                "Scheduled/Routines UI.",
                "Do NOT use CronCreate — CronCreate jobs are session-only and auto-expire "
                "after 7 days; they are not allowed for production scheduled runs.",
                "If mcp__scheduled-tasks__create_scheduled_task is unavailable, stop with "
                "host_durable_ui_routine_unavailable — do not fall back to CronCreate, "
                "session-only jobs, launchd, cron, or systemd.",
                "After creation record IDs: "
                "python3 scripts/local_routine.py set-backend --backend host_routine "
                "--durability durable_ui "
                "--routine-ids <id1>,<id2> --retry-ids <r1>,<r2> [--catchup-ids <c1>]",
            ],
        }

    # Host unknown — no supported scheduler detected
    return {
        "host": None,
        "label": "Unknown host",
        "routine_api": None,
        "create_method": None,
        "durability": None,
        "session_persistent": False,
        "ui_visible": False,
        "notes": [],
    }
