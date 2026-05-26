#!/usr/bin/env python3
"""Daily run orchestrator."""
import argparse, datetime, hashlib, json, os, re, subprocess, sys, time, calendar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schedule_prompt import schedule_prompt_once  # noqa: E402
from local_digest_publish import write_result, PublishError  # noqa: E402
from digest_publish import publish_final_digest, strip_fence_file  # noqa: E402
from platform import is_mira  # noqa: E402
from status_renderer import render_status  # noqa: E402
from schedule_config import normalize_timezone  # noqa: E402

HOME = os.path.expanduser("~")
ROOT = os.environ.get("SLACK_DIGEST_HOME") or os.path.join(HOME, ".slack-daily-digest")
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPTS)
TEMPLATE_PATH = os.path.join(SKILL_DIR, "references", "digest-template.md")
ROUTINE_PATH = os.path.join(ROOT, "routine.json")
RUNTIME_PATH = os.path.join(ROOT, "runtime.json")

REQUIRED_SECTIONS = (
    "## 🎯 Executive Summary",
    "## 📌 Highlights",
    "## ✅ TODO Backlog",
    "## 📈 Business Pipeline",
    "## ⚠️ Risk Signals",
    "## 🗂️ By Channel",
    "## 📝 Statistics",
)
FORBIDDEN_TEXT = ("Review the full messages below", "placeholder, to be filled")


def ensure_dirs(date):
    run_dir = os.path.join(ROOT, "runs", date)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path) as f:
        return json.load(f)


def save_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def rel_runtime(path):
    return os.path.relpath(path, ROOT)


def rel_skill(path):
    return os.path.relpath(path, SKILL_DIR)


def final_md_filename(slot, custom_window_hours=None):
    """Return the final markdown filename.

    Custom --window-hours runs get a _<N>h suffix to avoid colliding with
    routine slot files that use a different (default) window.
    """
    slot_key = slot.replace(":", "")
    if custom_window_hours is not None:
        return f"final_{slot_key}_{custom_window_hours}h.md"
    return f"final_{slot_key}.md"


def meta_path(markdown_path):
    """Sidecar path for final markdown freshness metadata."""
    return markdown_path[:-3] + ".meta.json"


def digest_sha256(digest_path):
    h = hashlib.sha256()
    with open(digest_path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def write_final_meta(markdown_path, digest_path, window_hours, date, slot):
    sha = digest_sha256(digest_path) if os.path.exists(digest_path) else None
    save_json(meta_path(markdown_path), {
        "source_digest_path": rel_runtime(digest_path),
        "source_digest_sha256": sha,
        "window_hours": window_hours,
        "date": date,
        "slot": slot,
        "generated_at": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    })
    return sha


def check_final_freshness(markdown_path, digest_path, window_hours, date, slot):
    """Return (is_fresh, info_dict).

    A final markdown is fresh only when:
      - the sidecar meta exists
      - source_digest_sha256 matches the current digest file
      - window_hours, date, and slot all match
    Any mismatch → stale; caller must delete the markdown and re-synthesize.
    """
    if not os.path.exists(markdown_path):
        return False, {"stale_final_detected": False, "final_markdown_reused": False}

    mp = meta_path(markdown_path)
    meta = load_json(mp)
    if not meta:
        return False, {
            "stale_final_detected": True, "final_markdown_reused": False,
            "stale_reason": "no_meta",
        }

    current_sha = digest_sha256(digest_path) if os.path.exists(digest_path) else None
    if meta.get("source_digest_sha256") != current_sha:
        return False, {
            "stale_final_detected": True, "final_markdown_reused": False,
            "stale_reason": "sha256_mismatch",
            "source_digest_sha256": current_sha,
        }
    if meta.get("window_hours") != window_hours:
        return False, {
            "stale_final_detected": True, "final_markdown_reused": False,
            "stale_reason": "window_hours_mismatch",
            "source_digest_sha256": current_sha,
        }
    if meta.get("date") != date or meta.get("slot") != slot:
        return False, {
            "stale_final_detected": True, "final_markdown_reused": False,
            "stale_reason": "date_slot_mismatch",
            "source_digest_sha256": current_sha,
        }

    return True, {
        "stale_final_detected": False, "final_markdown_reused": True,
        "source_digest_sha256": current_sha,
    }


def remember_runtime_root():
    save_json(RUNTIME_PATH, {
        "runtime_root": ROOT,
        "skill_root": SKILL_DIR,
        "updated_at": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    })


def validate_final_markdown(path, slot=None):
    if not os.path.exists(path):
        raise RuntimeError("agent_synthesis_required")
    if os.path.getsize(path) == 0:
        raise RuntimeError("agent_synthesis_required: final markdown is empty")
    with open(path) as f:
        body = f.read()
    missing = [section for section in REQUIRED_SECTIONS if section not in body]
    if missing:
        raise RuntimeError("agent_synthesis_failed: missing template sections " + ", ".join(missing))
    # For non-16:00 slots, the trailing "16:00 Update (placeholder, to be filled)" section
    # is intentionally included by the template — strip it before the forbidden-phrase check.
    check_body = body
    if slot != "16:00":
        check_body = re.sub(r"\n##[^\n]*16:00 Update.*", "", body, flags=re.DOTALL)
    if any(phrase in check_body for phrase in FORBIDDEN_TEXT):
        raise RuntimeError("agent_synthesis_failed: output still contains placeholder text")


def write_host_handoff(date, slot, run_dir, digest_path, history_path, markdown_path,
                       oldest, latest, timezone, window_hours, custom_window_hours=None):
    slot_key = slot.replace(":", "")
    sha = digest_sha256(digest_path) if os.path.exists(digest_path) else None
    publish_cmd = (
        f"python3 scripts/run_digest.py --publish-existing --date {date} --slot {slot}"
        + (f" --window-hours {custom_window_hours}" if custom_window_hours is not None else "")
    )
    handoff = {
        "status": "agent_synthesis_required",
        "runtime_root": ROOT,
        "skill_root": SKILL_DIR,
        "date": date,
        "slot": slot,
        "timezone": timezone,
        "oldest": oldest,
        "latest": latest,
        "window_hours": window_hours,
        "source_digest_sha256": sha,
        "digest_json": rel_runtime(digest_path),
        "history_json": rel_runtime(history_path),
        "template_path": rel_skill(TEMPLATE_PATH),
        "final_markdown": rel_runtime(markdown_path),
        "instruction": (
            "Current host agent must read digest_json, history_json, and template_path; "
            "write final_markdown following Daily Digest Synthesis Template v4; then run publish_command."
        ),
        "publish_command": publish_cmd,
    }
    handoff_path = os.path.join(run_dir, f"handoff_{slot_key}.json")
    save_json(handoff_path, handoff)
    return handoff_path, handoff


def publish_final(date, slot, markdown_path, digest_path=None, window_hours=None,
                  freshness_info=None):
    """Validate and publish a synthesized digest through the unified publish pipeline.

    Uses publish_final_digest() from digest_publish.py which handles:
      Bug 1 — strip outer markdown fence before publishing
      Bug 2 — index updated newest-on-top with de-duplication
      Bug 3 — IM card notification sent after publish
    """
    validate_final_markdown(markdown_path, slot=slot)
    # Write / refresh freshness sidecar so the next run can verify this file.
    sha = None
    if digest_path and os.path.exists(digest_path):
        sha = write_final_meta(markdown_path, digest_path, window_hours, date, slot)
    tz = configured_timezone()
    try:
        result = publish_final_digest(date=date, slot=slot, markdown_path=markdown_path, timezone=tz)
    except PublishError as exc:
        write_result(date, slot, {
            "ok": False,
            "error": f"publish_failed: {exc}",
            "doc_url": exc.digest_url,
            "index_url": exc.index_url,
            "final_markdown": rel_runtime(markdown_path),
            "final_markdown_reused": (freshness_info or {}).get("final_markdown_reused", False),
            "stale_final_detected": (freshness_info or {}).get("stale_final_detected", False),
            "source_digest_sha256": sha,
        })
        render_status("E2E stopped during Lark publish", blocker=str(exc),
                      index_url=exc.index_url, digest_url=exc.digest_url)
        return 1
    except Exception as exc:
        write_result(date, slot, {
            "ok": False,
            "error": f"publish_failed: {exc}",
            "final_markdown": rel_runtime(markdown_path),
            "final_markdown_reused": (freshness_info or {}).get("final_markdown_reused", False),
            "stale_final_detected": (freshness_info or {}).get("stale_final_detected", False),
            "source_digest_sha256": sha,
        })
        render_status("E2E stopped during Lark publish", blocker=str(exc))
        return 1
    write_result(date, slot, {
        "ok": True,
        "digest_link": result.get("digest_link"),
        "doc_url": result.get("doc_url"),
        "index_link": result.get("index_link"),
        "index_url": result.get("index_url"),
        "notification_status": result.get("notification_status"),
        "final_markdown": rel_runtime(markdown_path),
        "template": "references/digest-template.md",
        "final_markdown_reused": (freshness_info or {}).get("final_markdown_reused", False),
        "stale_final_detected": (freshness_info or {}).get("stale_final_detected", False),
        "source_digest_sha256": sha,
    })
    render_status("digest report created and added to index",
                  index_url=result.get("index_url"), digest_url=result.get("doc_url"))
    schedule_prompt_once()
    return 0


def configured_timezone():
    routine = load_json(ROUTINE_PATH, {})
    index = load_json(os.path.join(ROOT, "index.json"), {})
    return normalize_timezone(
        os.environ.get("SLACK_DIGEST_TIMEZONE")
        or routine.get("timezone")
        or index.get("timezone")
        or "Asia/Shanghai"
    )


def digest_date(timezone):
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo(timezone)).strftime("%Y-%m-%d")
    except Exception:
        return datetime.datetime.utcnow().strftime("%Y-%m-%d")


def compute_window(slot_hour, window_hours):
    """Return (oldest, latest) epoch in UTC for the configured window."""
    now = datetime.datetime.utcnow()
    latest = calendar.timegm(now.timetuple())
    oldest = latest - window_hours * 3600
    return oldest, latest


def _copy_result_to_custom(run_dir, slot_key, artifact_sfx):
    """Write the suffix-scoped result file for fresh-check cache.

    result_<slot_key>.json (no colon) is written by publish_final_digest and
    lacks source_digest_sha256.  result_<HH:MM>.json is written by write_result
    in publish_final and includes the SHA.  Prefer the colon version.
    """
    dst = os.path.join(run_dir, f"result_{slot_key}{artifact_sfx}.json")
    colon_slot = f"{slot_key[:2]}:{slot_key[2:]}"
    for fname in [f"result_{colon_slot}.json", f"result_{slot_key}.json"]:
        src = os.path.join(run_dir, fname)
        if src == dst:
            continue
        if os.path.exists(src):
            try:
                data = load_json(src)
                if data:
                    save_json(dst, data)
                    return
            except Exception:
                pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", default="11:00", help="HH:MM in configured timezone")
    ap.add_argument("--window-hours", type=int)
    ap.add_argument("--date", default=None, help="YYYY-MM-DD; default = today in configured timezone")
    ap.add_argument("--oldest", type=int, help="override oldest epoch")
    ap.add_argument("--latest", type=int, help="override latest epoch")
    ap.add_argument("--channel", action="append", default=[],
                    help="optional Slack channel ID/name limiter; repeatable")
    ap.add_argument("--publish-existing", action="store_true",
                    help="publish an already synthesized final markdown for date/slot")
    args = ap.parse_args()

    if args.date:
        date = args.date
    else:
        date = digest_date(configured_timezone())

    if args.window_hours:
        wh = args.window_hours
    else:
        hh = int(args.slot.split(":")[0])
        wh = 19 if hh < 14 else 5

    if args.oldest and args.latest:
        oldest, latest = args.oldest, args.latest
    else:
        oldest, latest = compute_window(int(args.slot.split(":")[0]), wh)

    # Determine whether --window-hours was explicitly provided (custom manual run).
    # Custom runs use a filename with a _<N>h suffix to avoid slot collisions.
    is_custom_window = args.window_hours is not None
    custom_wh = wh if is_custom_window else None
    # Suffix isolates custom-window artifacts (history, digest, result) from the routine's
    # slot files, preventing SHA contamination and result-file clobbering.
    artifact_sfx = f"_{custom_wh}h" if custom_wh is not None else ""

    run_dir = ensure_dirs(date)
    timezone = configured_timezone()
    remember_runtime_root()
    slot_key = args.slot.replace(":", "")
    markdown_path = os.path.join(run_dir, final_md_filename(args.slot, custom_wh))
    digest_path = os.path.join(run_dir, f"digest_{slot_key}{artifact_sfx}.json")

    if args.publish_existing:
        # Write / refresh meta so the next run can verify this file, then publish.
        if os.path.exists(digest_path):
            write_final_meta(markdown_path, digest_path, wh, date, args.slot)
        try:
            ret = publish_final(date, args.slot, markdown_path,
                                digest_path=digest_path, window_hours=wh,
                                freshness_info={"final_markdown_reused": False,
                                                "stale_final_detected": False})
            if ret == 0 and artifact_sfx:
                _copy_result_to_custom(run_dir, slot_key, artifact_sfx)
            return ret
        except Exception as exc:
            write_result(date, args.slot, {
                "ok": False,
                "error": str(exc),
                "final_markdown": rel_runtime(markdown_path),
                "final_markdown_reused": False,
                "stale_final_detected": False,
            })
            render_status("agent_synthesis_required", blocker=str(exc))
            return 2

    # Step 0: refresh user cache
    subprocess.run(["python3", os.path.join(SCRIPTS, "refresh_users_cache.py")], check=False)

    # Step 1: list channels
    channels_path = os.path.join(run_dir, f"channels_{slot_key}.json")
    list_cmd = ["python3", os.path.join(SCRIPTS, "list_channels.py"), channels_path]
    for channel in args.channel:
        list_cmd += ["--channel", channel]
    r = subprocess.run(list_cmd, check=False)
    if r.returncode != 0:
        print("ERR: list_channels failed", file=sys.stderr); return 1

    # Step 3: pull history
    history_path = os.path.join(run_dir, f"history_{slot_key}{artifact_sfx}.json")
    r = subprocess.run(["python3", os.path.join(SCRIPTS, "pull_history.py"),
                        "--channels", channels_path,
                        "--oldest", str(oldest),
                        "--latest", str(latest),
                        "--output", history_path], check=False)
    if r.returncode != 0:
        print("ERR: pull_history failed", file=sys.stderr); return 1

    # Step 4: build digest (resolve names + identify owners)
    r = subprocess.run(["python3", os.path.join(SCRIPTS, "build_digest.py"),
                        "--history", history_path,
                        "--output", digest_path], check=False)
    if r.returncode != 0:
        print("ERR: build_digest failed", file=sys.stderr); return 1

    if not is_mira():
        # Check whether the existing final markdown is still valid for this exact input.
        # Validation by file existence alone is insufficient — the digest may have changed.
        is_fresh, freshness_info = check_final_freshness(
            markdown_path, digest_path, wh, date, args.slot
        )
        if freshness_info.get("stale_final_detected"):
            print(f"stale_final_detected: removing {os.path.basename(markdown_path)} "
                  f"(reason: {freshness_info.get('stale_reason')})")
            try:
                os.remove(markdown_path)
            except OSError:
                pass
            try:
                os.remove(meta_path(markdown_path))
            except OSError:
                pass

        if is_fresh:
            # Avoid re-publishing the exact same digest to a new Lark doc on every re-run.
            # Check the custom result file written by the previous successful publish.
            if artifact_sfx:
                cached = load_json(os.path.join(run_dir, f"result_{slot_key}{artifact_sfx}.json"))
                if (cached.get("ok") and
                        cached.get("source_digest_sha256") == freshness_info.get("source_digest_sha256")):
                    render_status("digest already published",
                                  index_url=cached.get("index_url"),
                                  digest_url=cached.get("doc_url"))
                    return 0
            ret = publish_final(date, args.slot, markdown_path,
                                digest_path=digest_path, window_hours=wh,
                                freshness_info=freshness_info)
            if ret == 0 and artifact_sfx:
                _copy_result_to_custom(run_dir, slot_key, artifact_sfx)
            return ret

        # Final markdown is missing or stale — hand off to host agent for synthesis.
        handoff_path, handoff = write_host_handoff(
            date, args.slot, run_dir, digest_path, history_path, markdown_path,
            oldest, latest, timezone, window_hours=wh, custom_window_hours=custom_wh,
        )
        handoff_payload = {
            "ok": False,
            "error": "agent_synthesis_required",
            "digest_json": rel_runtime(digest_path),
            "history_json": rel_runtime(history_path),
            "final_markdown": rel_runtime(markdown_path),
            "handoff": rel_runtime(handoff_path),
            "final_markdown_reused": False,
            "stale_final_detected": freshness_info.get("stale_final_detected", False),
            "source_digest_sha256": freshness_info.get("source_digest_sha256"),
        }
        if artifact_sfx:
            # Custom window: write to a suffixed result file so the routine's shared
            # result_<slot>.json is not clobbered with ok=False during synthesis.
            save_json(os.path.join(run_dir, f"result_{slot_key}{artifact_sfx}.json"), handoff_payload)
        else:
            write_result(date, args.slot, handoff_payload)
        render_status("agent_synthesis_required", blocker="final digest markdown is missing")
        print("HOST_AGENT_HANDOFF:")
        print(json.dumps(handoff, indent=2, sort_keys=True))
        return 2

    # Mira keeps the existing agent-driven Lark doc flow.
    print("--- AGENT_HANDOFF ---")
    print(json.dumps({
        "date": date,
        "slot": args.slot,
        "run_dir": run_dir,
        "digest_json": digest_path,
        "history_json": history_path,
        "next": "synthesize_and_publish",
    }))
    schedule_prompt_once()
    return 0


if __name__ == "__main__":
    sys.exit(main())
