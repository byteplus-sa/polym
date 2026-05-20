#!/usr/bin/env python3
"""Public polym-eval-db CLI for resolving and bootstrapping the SQLite path."""

from __future__ import annotations

import argparse

from db_utils import default_db_path, ensure_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve polym-eval-db SQLite path")
    parser.add_argument("--db", default="", help="Optional explicit DB path")
    parser.add_argument(
        "--ensure",
        action="store_true",
        help="Download the default eval.db if it is missing",
    )
    args = parser.parse_args()

    db_path = ensure_db(args.db or None) if args.ensure else default_db_path()
    print(db_path)


if __name__ == "__main__":
    main()
