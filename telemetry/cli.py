"""Polymath telemetry CLI entry point.

Subcommands:
  sync         parse local cc + codex data and upload yesterday's daily row
  install      register the daily 14:00 launchd job (macOS)
  uninstall    remove the launchd job
  status       inspect launchd / state file
  auth-check   verify lark-cli has every scope polymath needs
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from . import __version__
from . import state as state_mod
from . import identity
from . import aggregator
from . import scheduler
from . import auth as auth_mod
from .parsers import claude_code, codex
from . import uploader


def cmd_sync(args: argparse.Namespace) -> int:
    if args.reset_state:
        if state_mod.STATE_FILE.exists():
            state_mod.STATE_FILE.unlink()
            print(f"removed {state_mod.STATE_FILE}", file=sys.stderr)

    # Registration is the installer's job — `install.sh` and `polymath telemetry
    # install` both call into scheduler.install(). `sync` purely syncs.

    state = state_mod.load()

    records = []
    if "claude-code" in args.agents:
        records.extend(claude_code.parse_all(state))
    if "codex" in args.agents:
        records.extend(codex.parse_all(state))

    rows = aggregator.aggregate(records)

    # Only push completed days. Today's row is partial — let tomorrow's 14:00
    # run pick it up cleanly once the day has rolled over.
    today_iso = date.today().isoformat()
    if args.include_today:
        eligible = rows
    else:
        eligible = [r for r in rows if r.date < today_iso]
    dropped = len(rows) - len(eligible)

    sa = identity.resolve_sa_name()
    mid = identity.machine_id()
    payload = [
        row.to_record(sa=sa, cli_version=f"polymath/{__version__}", machine_id=mid)
        for row in eligible
    ]

    msg = f"parsed {len(records)} records → {len(rows)} daily rows for SA={sa}"
    if dropped:
        msg += f" (dropped {dropped} for today={today_iso}; will push tomorrow)"
    print(msg, file=sys.stderr)
    if args.verbose:
        for row in rows:
            skill_summary = (
                ", ".join(f"{n}:{c}" for n, c in row.skill_invocations.most_common(3))
                or "(none)"
            )
            print(
                f"  {row.date} {row.agent:12} "
                f"total={row.total_tokens:>10,} "
                f"sessions={row.session_count} "
                f"skills=[{skill_summary}]",
                file=sys.stderr,
            )

    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        result = uploader.upload(payload)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    state_mod.save(state)
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    info = scheduler.install(hour=args.hour, minute=args.minute)
    print(json.dumps(info, indent=2, ensure_ascii=False))
    print(
        f"\n✅ launchd job registered. Will run daily at {args.hour:02d}:{args.minute:02d}.",
        file=sys.stderr,
    )
    print(f"   Logs: {info['logs']}/sync.{{out,err}}", file=sys.stderr)
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    info = scheduler.uninstall()
    print(json.dumps(info, indent=2, ensure_ascii=False))
    return 0


def cmd_auth_check(args: argparse.Namespace) -> int:
    status, missing, data = auth_mod.check()
    info = {
        "status": status,
        "user": data.get("userName"),
        "missing_scopes": sorted(missing) if missing else [],
        "required_count": len(auth_mod.REQUIRED_SCOPES),
    }
    print(json.dumps(info, indent=2, ensure_ascii=False))
    if status == "ok":
        return 0
    print(
        f"\n❌ lark-cli auth status: {status}. "
        "Run `lark-cli auth login` to re-grant the missing scopes.",
        file=sys.stderr,
    )
    return 1


def cmd_status(args: argparse.Namespace) -> int:
    info = scheduler.status()
    info["state_file"] = str(state_mod.STATE_FILE)
    info["state_file_exists"] = state_mod.STATE_FILE.exists()
    print(json.dumps(info, indent=2, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="polymath-telemetry")
    sub = p.add_subparsers(dest="cmd", required=True)

    sync = sub.add_parser("sync", help="parse local agent data and upload daily aggregates")
    sync.add_argument(
        "--agents",
        nargs="+",
        choices=["claude-code", "codex"],
        default=["claude-code", "codex"],
        help="which agents to parse (default: both)",
    )
    sync.add_argument("--dry-run", action="store_true", help="print payload, do not upload")
    sync.add_argument("--reset-state", action="store_true", help="force a full re-scan")
    sync.add_argument(
        "--include-today",
        action="store_true",
        help="also push today's partial data (default: only push completed days)",
    )
    sync.add_argument("-v", "--verbose", action="store_true")
    sync.set_defaults(func=cmd_sync)

    install = sub.add_parser(
        "install",
        help="register a daily launchd job (macOS); default 14:00 local pushes the previous day",
    )
    install.add_argument("--hour", type=int, default=14, help="local hour to run (0-23, default 14)")
    install.add_argument("--minute", type=int, default=0, help="local minute (0-59, default 0)")
    install.set_defaults(func=cmd_install)

    uninstall = sub.add_parser("uninstall", help="remove the launchd job")
    uninstall.set_defaults(func=cmd_uninstall)

    status = sub.add_parser("status", help="show whether the auto-schedule is loaded")
    status.set_defaults(func=cmd_status)

    auth_check = sub.add_parser(
        "auth-check",
        help="verify lark-cli is logged in with every scope polymath needs",
    )
    auth_check.set_defaults(func=cmd_auth_check)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
