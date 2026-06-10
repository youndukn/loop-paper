#!/usr/bin/env python3
"""Register or rotate a password for a Paper Stack human reviewer."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import secrets
from pathlib import Path

from paperstack_common import load_reviewers, password_hash, reviewers_path, today


DEFAULT_ITERATIONS = 200_000


def read_password() -> str:
    password = os.environ.get("PAPER_STACK_REVIEW_PASSWORD")
    if password:
        return password
    first = getpass.getpass("Review password: ")
    second = getpass.getpass("Confirm review password: ")
    if first != second:
        raise SystemExit("FAIL passwords do not match")
    return first


def main() -> int:
    parser = argparse.ArgumentParser(description="Set a Paper Stack human reviewer password.")
    parser.add_argument("root", nargs="?", default=".paper-stack", help="Paper Stack root")
    parser.add_argument("--reviewer", required=True, help="Human reviewer name")
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS, help="PBKDF2 iterations")
    args = parser.parse_args()

    root = Path(args.root)
    config = load_reviewers(root)
    config.setdefault("reviewers", {})
    salt = secrets.token_hex(16)
    password = read_password()
    config["reviewers"][args.reviewer] = {
        "salt": salt,
        "iterations": args.iterations,
        "password_hash": password_hash(password, salt, args.iterations),
        "updated": today(),
    }
    path = reviewers_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"reviewer registered: {args.reviewer}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
