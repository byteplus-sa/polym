#!/usr/bin/env python3
"""Local routine runner with missed-run catch-up for Codex / Claude Code."""
import argparse
import datetime
import json
import os
import shlex
import stat
import subprocess
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schedule_config import normalize_timezone, persist_schedule  # noqa: E402
from status_renderer import render_status  # noqa: E402
from platform import detect_host_scheduler, has_host_scheduler, describe_host_scheduler  # noqa: E402

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

HOME = os.path.expanduser("~")
ROOT = os.environ.get("SLACK_DIGEST_HOME") or os.path.join(HOME, ".slack-daily-digest")
ROUTINE_JSON = os.path.join(ROOT, "routine.json")
STATE_JSON = os.path.join(ROOT, "routine_state.json")
INDEX_JSON = os.path.join(ROOT, "index.json")
LOG_PATH = os.path.join(ROOT, "routine.log")
LOCK_PATH = os.path.join(ROOT, "routine.lock")
RUNS_DIR = os.path.join(ROOT, "runs")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)

DEFAULT_ROUTINE = {
    "timezone": "Asia/Shanghai",
    "slots": ["08:00", "16:00"],
    "working_hours": {"start": "08:00", "end": "19:00"},
    "catchup_hours": 6,
    "check_interval_minutes": 10,
    "synthesis": {},
    "agent": {"type": "custom"},
}

CREDENTIAL_ERROR_MARKERS = (
    "invalid_auth",
    "token_revoked",
    "not_authed",
    "unauthorized",
    "token expired",
    "invalid token",
    "not logged in",
    "auth required",
)

MISSING_UNATTENDED_SYNTHESIS_ERROR = (
    "Scheduled runs need an unattended synthesis backend or explicit custom command. "
    "One-off E2E uses the current host agent handoff."
)

LOCAL_SCHEDULER_REMOVED_MSG = (
    "local_scheduler_removed: Local OS scheduler (launchd/systemd/cron) is no longer supported. "
    "Use Codex Routine or Claude Code Routine instead."
)


def log(message):
    os.makedirs(ROOT, exist_ok=True)
    stamp = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    with open(LOG_PATH, "a") as f:
        f.write(f"[{stamp}] {message}\n")


class Lock:
    def __enter__(self):
        try:
            self.fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise SystemExit(0)
        os.write(self.fd, str(os.getpid()).encode())
        return self

    def __exit__(self, exc_type, exc, tb):
        os.close(self.fd)
        try:
            os.unlink(LOCK_PATH)
        except FileNotFoundError:
            pass


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp, path)


def parse_hhmm(value):
    hour, minute = value.split(":")
    return int(hour), int(minute)


def as_minutes(value):
    hour, minute = parse_hhmm(value)
    return hour * 60 + minute


def inside_window(now, start, end):
    current = now.hour * 60 + now.minute
    start_m = as_minutes(start)
    end_m = as_minutes(end)
    if start_m <= end_m:
        return start_m <= current <= end_m
    return current >= start_m or current <= end_m


def tzinfo(name):
    if ZoneInfo is None:
        raise RuntimeError("Python zoneinfo is required for local routine scheduling")
    return ZoneInfo(name)


def scheduled_datetime(date_obj, slot, timezone):
    hour, minute = parse_hhmm(slot)
    return datetime.datetime(
        date_obj.year,
        date_obj.month,
        date_obj.day,
        hour,
        minute,
        tzinfo=tzinfo(timezone),
    )


def default_runner_command_template():
    return "python3 {skill_dir}/scripts/run_digest.py --date {date} --slot {slot}"


def render_command(config, date, slot):
    agent = config.get("agent", {})
    template = (
        config.get("runner_command_template")
        or agent.get("runner_command_template")
        or agent.get("command_template")  # backward compat: pre-v22 stored here
    )
    if not template:
        synthesis = config.get("synthesis", {})
        if synthesis.get("provider"):
            raise RuntimeError(MISSING_UNATTENDED_SYNTHESIS_ERROR)
        template = default_runner_command_template()
    return template.format(skill_dir=SKILL_DIR, date=date, slot=slot, timezone=config["timezone"])


def result_path(date, slot):
    return os.path.join(RUNS_DIR, date, f"result_{slot}.json")


def classify_error(text):
    lowered = text.lower()
    if any(marker in lowered for marker in CREDENTIAL_ERROR_MARKERS):
        return "credential_error"
    return "transient_error"


def run_agent(config, date, slot):
    command = render_command(config, date, slot)
    env = os.environ.copy()
    env["SLACK_DIGEST_PLATFORM"] = "local_agent"
    env["SLACK_DIGEST_DATE"] = date
    env["SLACK_DIGEST_SLOT"] = slot
    env["SLACK_DIGEST_TIMEZONE"] = config["timezone"]
    log(f"running date={date} slot={slot} command={command}")
    result = subprocess.run(
        shlex.split(command),
        cwd=SKILL_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60 * 60,
    )
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    path = result_path(date, slot)
    if os.path.exists(path):
        try:
            with open(path) as f:
                payload = json.load(f)
            if payload.get("ok") is True:
                return True, payload.get("doc_url"), None
            return False, None, payload.get("error") or output.strip()
        except Exception:
            pass
    if result.returncode == 0:
        return True, None, None
    return False, None, output.strip() or f"agent command exited {result.returncode}"


def load_config():
    config = load_json(ROUTINE_JSON, json.loads(json.dumps(DEFAULT_ROUTINE)))
    if not os.path.exists(ROUTINE_JSON) and os.path.exists(INDEX_JSON):
        index = load_json(INDEX_JSON, {})
        schedule = index.get("schedule") or []
        slots = []
        timezone = config["timezone"]
        for item in schedule:
            slots.append(f"{int(item['hour']):02d}:{int(item['minute']):02d}")
            timezone = item.get("timezone") or ("Asia/Shanghai" if item.get("tz") == "+08:00" else timezone)
        if slots:
            config["slots"] = slots
            config["timezone"] = timezone
    return config


def due_slots(config, state, now):
    today = now.date()
    for slot in config["slots"]:
        key = f"{today.isoformat()}#{slot}"
        record = state.setdefault("runs", {}).get(key, {})
        if record.get("status") == "success":
            continue
        if record.get("status") == "credential_error":
            log(f"skip credential_error key={key}")
            continue
        scheduled = scheduled_datetime(today, slot, config["timezone"])
        if now < scheduled:
            continue
        if not inside_window(
            now,
            config["working_hours"]["start"],
            config["working_hours"]["end"],
        ):
            log(f"skip outside working hours key={key}")
            continue
        age_hours = (now - scheduled).total_seconds() / 3600
        if age_hours > float(config.get("catchup_hours", 6)):
            record.update({
                "status": "skipped_missed_window",
                "scheduled_at": scheduled.isoformat(),
                "last_error": "catch-up window expired",
            })
            state["runs"][key] = record
            log(f"mark skipped_missed_window key={key}")
            continue
        yield key, today.isoformat(), slot, scheduled


def run_due(slot=None, timezone_override=None):
    with Lock():
        config = load_config()
        if timezone_override:
            config["timezone"] = timezone_override
        # When a specific slot is given, restrict to only that slot.
        if slot:
            config = dict(config)
            config["slots"] = [slot]
        state = load_json(STATE_JSON, {"runs": {}})
        now = datetime.datetime.now(tzinfo(config["timezone"]))
        ran_any = False

        for key, date, slot, scheduled in due_slots(config, state, now):
            ran_any = True
            record = state.setdefault("runs", {}).get(key, {})
            attempts = int(record.get("attempts", 0)) + 1
            record.update({
                "status": "running",
                "attempts": attempts,
                "scheduled_at": scheduled.isoformat(),
                "started_at": now.isoformat(),
            })
            state["runs"][key] = record
            save_json(STATE_JSON, state)

            setup_status = None
            try:
                ok, doc_url, error = run_agent(config, date, slot)
            except RuntimeError as exc:
                if str(exc) != MISSING_UNATTENDED_SYNTHESIS_ERROR:
                    raise
                ok, doc_url, error = False, None, str(exc)
                setup_status = "blocked_missing_unattended_synthesis"
            finished = datetime.datetime.now(tzinfo(config["timezone"]))
            if ok:
                record.update({
                    "status": "success",
                    "finished_at": finished.isoformat(),
                    "doc_url": doc_url,
                    "last_error": None,
                })
                log(f"success key={key} doc_url={doc_url or ''}")
            else:
                status = setup_status or classify_error(error or "")
                record.update({
                    "status": status,
                    "finished_at": finished.isoformat(),
                    "last_error": error,
                })
                if status == "credential_error":
                    log(f"credential_error key={key}: {error}")
                elif setup_status:
                    log(f"{status} key={key}: {error}")
                else:
                    log(f"transient_error key={key}: {error}")
            state["runs"][key] = record
            save_json(STATE_JSON, state)

        if not ran_any:
            save_json(STATE_JSON, state)
            log("no due slots")


def parse_slots(raw):
    slots = []
    for item in raw.split(","):
        item = item.strip()
        parse_hhmm(item)
        slots.append(item)
    return slots


def parse_working_hours(raw):
    start, end = raw.split("-", 1)
    parse_hhmm(start.strip())
    parse_hhmm(end.strip())
    return {"start": start.strip(), "end": end.strip()}


def write_launch_agent(config):
    raise SystemExit(LOCAL_SCHEDULER_REMOVED_MSG)


def write_systemd_timer(config):
    raise SystemExit(LOCAL_SCHEDULER_REMOVED_MSG)


def _is_tmp_root():
    real = os.path.realpath(ROOT)
    return real.startswith("/private/tmp/") or real.startswith("/tmp/")


def validate_for_scheduler():
    """Check all prerequisites before creating any scheduler. Returns list of error strings."""
    errors = []
    creds_path = os.path.join(ROOT, "credentials.json")
    if not os.path.exists(creds_path):
        errors.append("credentials.json missing — run save_credentials.py first")
    if not os.path.exists(INDEX_JSON):
        errors.append("index.json missing — Lark target not configured (run setup_lark_cli.py first)")

    config = load_json(ROUTINE_JSON, {})
    agent = config.get("agent", {})
    template = (
        config.get("runner_command_template")
        or agent.get("runner_command_template")
        or agent.get("command_template")
    )
    if not template:
        errors.append(
            "runner_command_template not set — run "
            "'python3 scripts/local_routine.py generate-runner' first"
        )
    else:
        # Must not be the plain default (which stops at AGENT_HANDOFF)
        default = default_runner_command_template()
        if template.strip() == default.strip():
            errors.append(
                "runner_command_template is plain run_digest.py — "
                "this stops at AGENT_HANDOFF and cannot run unattended"
            )
    return errors


def _catchup_schedule(slots, working_hours):
    """Return (hour, minute) for a suggested catch-up routine.

    Places it 30 minutes after the last slot, capped at end of working hours.
    Returns None if there is only one slot or catch-up would land outside working hours.
    """
    if not slots:
        return None
    last_slot = max(slots, key=lambda s: int(s.split(":")[0]) * 60 + int(s.split(":")[1]))
    lh, lm = int(last_slot.split(":")[0]), int(last_slot.split(":")[1])
    total = lh * 60 + lm + 30
    ch, cm = divmod(total, 60)
    end = working_hours.get("end", "19:00")
    eh, em = int(end.split(":")[0]), int(end.split(":")[1])
    end_total = eh * 60 + em
    if ch * 60 + cm > end_total:
        # Put it at end of working hours as last resort
        ch, cm = eh, em
    return ch, cm


def setup_scheduler(args):
    """Validate setup and emit a machine-readable scheduler_setup_request for the host agent.

    Creates one durable host UI routine per digest slot (main) plus one retry routine per slot
    (+15 min) and an optional end-of-day catch-up.

    Only durable Codex and Claude Code host routines are supported.
    Local OS scheduler (launchd/systemd/cron) is not supported and will not be used.
    Session-only (non-durable) routines are not allowed for production runs.
    """
    # Stable-path check: refuse /tmp for durable routines
    if _is_tmp_root():
        raise SystemExit(
            "stable_path_required: SLACK_DIGEST_HOME is under /tmp — "
            "state will be lost on reboot. Set SLACK_DIGEST_HOME to a stable path "
            "(e.g. ~/.slack-daily-digest) before creating host routines."
        )

    # Host detection: must be codex or claude_code
    host_scheduler = detect_host_scheduler()
    if not host_scheduler:
        raise SystemExit(
            "host_unknown: cannot detect host scheduler. "
            "This skill requires a Codex workspace or Claude Code session. "
            "Do not fall back to launchd, cron, or systemd."
        )

    # Durability check: stop if host does not support durable UI routines
    host_desc = describe_host_scheduler()
    if not host_desc.get("session_persistent"):
        raise SystemExit(
            "session_only_routine_not_allowed: the detected host does not support "
            "durable routines. Production runs require routines that persist across "
            "session restarts and are visible in the host UI. "
            "Do not create session-only, auto-expiring, or hidden routines."
        )

    errors = validate_for_scheduler()
    if errors:
        for e in errors:
            print(f"validation_failed: {e}", file=sys.stderr)
        raise SystemExit("scheduler_setup_blocked: fix the above before creating a scheduler")

    config = load_json(ROUTINE_JSON, {})
    agent_cfg = config.get("agent", {})
    template = (
        config.get("runner_command_template")
        or agent_cfg.get("runner_command_template")
        or agent_cfg.get("command_template")
    )
    slots = config.get("slots", ["11:00"])
    timezone = config.get("timezone", "Asia/Shanghai")
    working_hours = config.get("working_hours", {"start": "08:00", "end": "19:00"})
    catchup_hours = config.get("catchup_hours", 6)
    env = {"SLACK_DIGEST_HOME": ROOT, "SLACK_DIGEST_PLATFORM": "local_agent"}

    # --- Per-slot main routines + retry routines (+15 min each) ---
    per_slot_routines = []
    retry_routines = []
    for slot in slots:
        sh, sm = int(slot.split(":")[0]), int(slot.split(":")[1])
        safe = slot.replace(":", "")
        slot_cmd = (
            f"python3 {os.path.join(SCRIPT_DIR, 'local_routine.py')} "
            f"run-due --slot {slot} --timezone {timezone}"
        )

        per_slot_routines.append({
            "slot": slot,
            "name": f"slack-digest-{safe}",
            "description": f"Slack Daily Digest {slot} {timezone}",
            "command": slot_cmd,
            "env": env,
            "cron": f"{sm} {sh} * * *",
            "schedule": {"type": "daily", "hour": sh, "minute": sm, "timezone": timezone},
        })

        # Retry at slot + 15 minutes
        retry_total = sh * 60 + sm + 15
        rh, rm = divmod(retry_total, 60)
        retry_routines.append({
            "slot": slot,
            "name": f"slack-digest-{safe}-retry",
            "description": f"Slack Daily Digest {slot} retry {timezone}",
            "command": slot_cmd,
            "env": env,
            "cron": f"{rm} {rh} * * *",
            "schedule": {"type": "daily", "hour": rh, "minute": rm, "timezone": timezone},
            "note": (
                f"Retries slot {slot} if the main routine failed or was missed. "
                "Skips silently if already succeeded."
            ),
        })

    # --- Optional end-of-day catch-up routine ---
    cu = _catchup_schedule(slots, working_hours)
    optional_catchup = None
    if cu:
        ch, cm = cu
        catchup_cmd = (
            f"python3 {os.path.join(SCRIPT_DIR, 'local_routine.py')} "
            f"run-due --timezone {timezone}"
        )
        optional_catchup = {
            "name": "slack-digest-catchup",
            "description": f"Slack Daily Digest catch-up {timezone}",
            "command": catchup_cmd,
            "env": env,
            "cron": f"{cm} {ch} * * *",
            "schedule": {"type": "daily", "hour": ch, "minute": cm, "timezone": timezone},
            "note": (
                "Checks all slots for the day. Retries missed/failed slots. "
                "Skips slots that already succeeded. Safe to always create."
            ),
        }

    request = {
        "status": "scheduler_setup_request",
        "host_scheduler": host_scheduler,
        "scheduler_durability": "durable_ui",
        "host_instructions": host_desc,
        "state": ROOT,
        "schedule": {
            "slots": slots,
            "timezone": timezone,
            "working_hours": working_hours,
            "catchup_hours": catchup_hours,
        },
        "runner_command_template": template,
        # One main durable routine per slot
        "host_routines": per_slot_routines,
        # One durable retry routine per slot at +15 minutes
        "retry_routines": retry_routines,
        # Optional durable end-of-day catch-up (ask user)
        "optional_catchup_routine": optional_catchup,
        # Enforcement: no local scheduler, no session-only routines
        "local_scheduler_used": False,
        "session_only_routine_used": False,
    }
    print(json.dumps(request, indent=2, sort_keys=True))
    return request


def set_backend(args):
    """Record the scheduler backend, durability, host, and all routine IDs created."""
    config = load_json(ROUTINE_JSON, {})
    config["scheduler_backend"] = args.backend
    config["scheduler_host"] = detect_host_scheduler()
    config["scheduler_durability"] = getattr(args, "durability", None) or "durable_ui"

    ids_raw = getattr(args, "routine_ids", None)
    if ids_raw:
        config["scheduler_routine_ids"] = [i.strip() for i in ids_raw.split(",") if i.strip()]

    retry_raw = getattr(args, "retry_ids", None)
    if retry_raw:
        config["retry_routine_ids"] = [i.strip() for i in retry_raw.split(",") if i.strip()]

    catchup_raw = getattr(args, "catchup_ids", None)
    if catchup_raw:
        config["catchup_routine_ids"] = [i.strip() for i in catchup_raw.split(",") if i.strip()]

    save_json(ROUTINE_JSON, config)

    cfg = load_config()
    summary = {
        "host": config.get("scheduler_host"),
        "scheduler_backend": "durable host UI routine",
        "scheduler_durability": config.get("scheduler_durability"),
        "main_routine_ids": config.get("scheduler_routine_ids", []),
        "retry_routine_ids": config.get("retry_routine_ids", []),
        "catchup_routine_ids": config.get("catchup_routine_ids", []),
        "slots": cfg.get("slots", []),
        "timezone": cfg.get("timezone"),
        "slack_digest_home": ROOT,
        "local_scheduler_used": False,
        "session_only_routine_used": False,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


def install(args):
    raise SystemExit(LOCAL_SCHEDULER_REMOVED_MSG)


def configure(args, quiet=False):
    config = load_config()
    if args.slots:
        config["slots"] = parse_slots(args.slots)
    if args.timezone:
        config["timezone"] = normalize_timezone(args.timezone)
    if args.working_hours:
        config["working_hours"] = parse_working_hours(args.working_hours)
    if args.catchup_hours is not None:
        config["catchup_hours"] = args.catchup_hours
    if args.command_template:
        config.setdefault("synthesis", {})["provider"] = "custom"
        config["runner_command_template"] = args.command_template
        # remove deprecated key so it doesn't shadow the canonical one
        config.get("agent", {}).pop("command_template", None)

    persist_schedule(
        ROOT,
        config["slots"],
        config["timezone"],
        config.get("working_hours"),
        runner_command_template=config.get("runner_command_template"),
    )
    config = load_json(ROUTINE_JSON, config)
    if not quiet:
        render_status(
            "schedule config saved; scheduler not installed",
            runs=", ".join(config.get("slots", [])),
            timezone=config.get("timezone"),
            state=ROOT,
        )
    return config


# is_temp_home / scheduler_mode / launch_environment were removed with local OS scheduler support.


def status():
    config = load_json(ROUTINE_JSON, {})
    state = load_json(STATE_JSON, {"runs": {}})
    print(json.dumps({
        "routine_config": ROUTINE_JSON,
        "routine_state": STATE_JSON,
        "log": LOG_PATH,
        "config": config,
        "recent_runs": state.get("runs", {}),
    }, indent=2, sort_keys=True))


def uninstall():
    raise SystemExit(LOCAL_SCHEDULER_REMOVED_MSG)


def generate_runner(args):
    """Copy the canonical unattended-runner-template.sh to a local executable."""
    template_path = os.path.join(SKILL_DIR, "references", "unattended-runner-template.sh")
    if not os.path.exists(template_path):
        raise RuntimeError(f"Runner template not found: {template_path}")

    out_path = getattr(args, "output", None) or os.path.expanduser("~/.local/bin/slack-digest-runner.sh")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    import shutil
    shutil.copy2(template_path, out_path)
    os.chmod(out_path, 0o755)

    # Build the command_template that routine.json will store
    command_template = f"{out_path} {{skill_dir}} {{date}} {{slot}}"

    # Persist into routine.json so run-due picks it up
    config = load_json(ROUTINE_JSON, {})
    config["runner_command_template"] = command_template
    config.get("agent", {}).pop("command_template", None)
    save_json(ROUTINE_JSON, config)

    print(f"OK: runner written to {out_path}")
    print(f"runner_command_template: {command_template}")
    return out_path, command_template


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    # install — removed; kept for clear error messaging
    install_parser = sub.add_parser("install",
        help="[REMOVED] local OS scheduler is no longer supported")
    install_parser.add_argument("--slots")
    install_parser.add_argument("--timezone", default=None)
    install_parser.add_argument("--working-hours")
    install_parser.add_argument("--catchup-hours", type=float)
    install_parser.add_argument("--command-template")
    install_parser.add_argument("--mode", choices=["auto", "isolated", "production"], default="auto")
    install_parser.add_argument("--confirm-production", action="store_true")
    install_parser.add_argument("--confirm-local-os", action="store_true")

    configure_parser = sub.add_parser("configure")
    configure_parser.add_argument("--slots", help="comma-separated HH:MM list, e.g. 08:00,16:00")
    configure_parser.add_argument("--timezone", default=None)
    configure_parser.add_argument("--working-hours", help="HH:MM-HH:MM, e.g. 08:00-19:00")
    configure_parser.add_argument("--catchup-hours", type=float)
    configure_parser.add_argument("--command-template", help="explicit custom synthesis command template")

    # setup-scheduler: includes all args that configure() may consume (Part 1 bug fix)
    ss_parser = sub.add_parser("setup-scheduler",
        help="validate setup and emit scheduler_setup_request JSON for the host agent")
    ss_parser.add_argument("--slots", help="comma-separated HH:MM list, e.g. 11:00,16:00")
    ss_parser.add_argument("--timezone", default=None)
    ss_parser.add_argument("--working-hours", help="HH:MM-HH:MM, e.g. 08:00-19:00")
    ss_parser.add_argument("--catchup-hours", type=float,
                           help="override catchup window before emitting request")
    ss_parser.add_argument("--command-template",
                           help="override runner_command_template before emitting request")

    sb_parser = sub.add_parser("set-backend",
        help="record which scheduler backend and routine IDs were successfully created")
    sb_parser.add_argument("--backend", required=True,
                           choices=["host_routine"],
                           help="scheduler backend that was created (only host_routine supported)")
    sb_parser.add_argument("--durability", default="durable_ui",
                           choices=["durable_ui"],
                           help="scheduler durability level (must be durable_ui)")
    sb_parser.add_argument("--routine-ids", default=None,
                           help="comma-separated main routine IDs")
    sb_parser.add_argument("--retry-ids", default=None,
                           help="comma-separated retry routine IDs (+15 min)")
    sb_parser.add_argument("--catchup-ids", default=None,
                           help="comma-separated catch-up routine IDs (end-of-day)")

    gr_parser = sub.add_parser("generate-runner",
        help="install unattended-runner-template.sh to ~/.local/bin and update routine.json")
    gr_parser.add_argument("--output", default=None,
                           help="destination path (default: ~/.local/bin/slack-digest-runner.sh)")

    run_due_parser = sub.add_parser("run-due",
        help="check and run any due (or specified) digest slots")
    run_due_parser.add_argument("--slot", default=None,
                                help="restrict to a single slot (HH:MM); defaults to all due slots")
    run_due_parser.add_argument("--timezone", default=None,
                                help="timezone override (default: from routine.json)")

    sub.add_parser("status")

    uninstall_parser = sub.add_parser("uninstall",
        help="[REMOVED] local OS scheduler is no longer supported")

    args = parser.parse_args()
    try:
        if args.command == "install":
            install(args)
        elif args.command == "configure":
            configure(args)
        elif args.command == "setup-scheduler":
            # Allow optional slot/tz/wh/catchup/template overrides before emitting the request
            if any([
                getattr(args, "slots", None),
                getattr(args, "timezone", None),
                getattr(args, "working_hours", None),
                getattr(args, "catchup_hours", None) is not None,
                getattr(args, "command_template", None),
            ]):
                configure(args, quiet=True)
            setup_scheduler(args)
        elif args.command == "set-backend":
            set_backend(args)
        elif args.command == "generate-runner":
            generate_runner(args)
        elif args.command == "run-due":
            run_due(
                slot=getattr(args, "slot", None),
                timezone_override=getattr(args, "timezone", None),
            )
        elif args.command == "status":
            status()
        elif args.command == "uninstall":
            uninstall()
    except Exception as exc:
        log(f"ERROR: {exc}")
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
