#!/usr/bin/env python3
"""Shared schedule normalization and persistence helpers."""
import json
import os
import stat


UTC_ALIASES = {"utc", "gmt", "gmt+0", "gmt+00:00", "+00:00", "z"}


def normalize_timezone(value):
    raw = (value or "Asia/Shanghai").strip()
    if raw.lower() in UTC_ALIASES:
        return "Etc/UTC"
    return raw


def timezone_offset_label(timezone):
    if timezone in ("Etc/UTC", "UTC"):
        return "+00:00"
    if timezone == "Asia/Shanghai":
        return "+08:00"
    return timezone


def parse_slots(raw):
    slots = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        hour, minute = item.split(":")
        slots.append(f"{int(hour):02d}:{int(minute):02d}")
    return slots


def parse_working_hours(raw):
    start, end = raw.split("-", 1)
    return {"start": start.strip(), "end": end.strip()}


def schedule_entries(slots, timezone):
    tz = timezone_offset_label(timezone)
    return [
        {
            "hour": int(slot.split(":")[0]),
            "minute": int(slot.split(":")[1]),
            "timezone": timezone,
            "tz": tz,
            "window_hours": 19 if int(slot.split(":")[0]) < 14 else 5,
        }
        for slot in slots
    ]


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp, path)


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def persist_schedule(root, slots, timezone, working_hours=None, runner_command_template=None):
    timezone = normalize_timezone(timezone)
    index_path = os.path.join(root, "index.json")
    routine_path = os.path.join(root, "routine.json")
    index = load_json(index_path)
    index["schedule"] = schedule_entries(slots, timezone)
    index["timezone"] = timezone
    if working_hours:
        index["working_hours"] = working_hours
    save_json(index_path, index)

    routine = load_json(routine_path)
    routine.setdefault("catchup_hours", 6)
    routine.setdefault("check_interval_minutes", 10)
    routine.setdefault("synthesis", {})
    routine.setdefault("agent", {"type": "custom"})
    # migrate: remove deprecated agent.command_template if present
    routine.get("agent", {}).pop("command_template", None)
    routine["slots"] = slots
    routine["timezone"] = timezone
    if working_hours:
        routine["working_hours"] = working_hours
    if runner_command_template is not None:
        routine["runner_command_template"] = runner_command_template
    save_json(routine_path, routine)
    return index, routine
