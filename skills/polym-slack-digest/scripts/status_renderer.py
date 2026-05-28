#!/usr/bin/env python3
"""Short deterministic status output."""


def render_status(status, blocker=None, index_url=None, digest_url=None,
                  schedule_question=False, runs=None, timezone=None,
                  state=None, lark_auth_home=None, runner_command=None):
    print(f"Status: {status}")
    if blocker:
        print(f"Exact blocker: {blocker}")
    if index_url:
        print(f"Index link: {index_url}")
    if digest_url:
        print(f"Digest link: {digest_url}")
    if runs:
        print(f"Runs: {runs}")
    if timezone:
        print(f"Timezone: {timezone}")
    if state:
        print(f"State: {state}")
    if lark_auth_home:
        print(f"Lark auth home: {lark_auth_home}")
    if runner_command:
        print(f"Runner command: {runner_command}")
    if schedule_question:
        print("Do you want to set up scheduled runs for Slack Daily Digest?")
        print("A) No, run manually only")
        print("B) Yes, once per day")
        print("C) Yes, multiple times per day")
