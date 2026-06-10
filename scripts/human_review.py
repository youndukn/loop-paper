#!/usr/bin/env python3
"""Apply a password-verified human review to a Paper Stack paper."""

from __future__ import annotations

import argparse
import getpass
import hmac
import os
import re
import sys
from pathlib import Path

from paperstack_common import (
    load_paper,
    load_reviewers,
    paper_root_from_path,
    parse_frontmatter,
    password_hash,
    replace_frontmatter,
    today,
    verification_token,
)


def read_password() -> str:
    return os.environ.get("PAPER_STACK_REVIEW_PASSWORD") or getpass.getpass("Review password: ")


def verify_password(root: Path, reviewer: str, password: str) -> tuple[bool, str, dict]:
    config = load_reviewers(root)
    reviewer_config = config.get("reviewers", {}).get(reviewer)
    if not reviewer_config:
        return False, f"reviewer is not registered: {reviewer}", {}
    candidate = password_hash(password, reviewer_config["salt"], int(reviewer_config["iterations"]))
    if not hmac.compare_digest(candidate, reviewer_config["password_hash"]):
        return False, "review password did not match", {}
    return True, "password verified", reviewer_config


def human_validation_checked(text: str) -> str:
    pattern = r"(Human validation evidence:\s*\n)(.*?)(?=\n## |\Z)"

    def replace(match: re.Match[str]) -> str:
        block = match.group(2)
        block = re.sub(r"- \[ \] Human validation required", "- [x] Human validation approved by password-verified reviewer", block)
        return match.group(1) + block

    return re.sub(pattern, replace, text, count=1, flags=re.IGNORECASE | re.DOTALL)


def replace_human_review(text: str, reviewer: str, decision: str, notes: str, token: str) -> str:
    section = f"""## Human Review

Human reviewer: {reviewer}
Review date: {today()}
Decision: {decision}
Verification: password-verified:{token}
Notes: {notes}

- [x] Human reviewed the paper
- [x] Human accepted the validation evidence
"""
    pattern = r"^## Human Review\s*\n.*?(?=^## |\Z)"
    if not re.search(pattern, text, flags=re.MULTILINE | re.DOTALL):
        return text.rstrip() + "\n\n" + section + "\n"
    return re.sub(pattern, section + "\n", text, count=1, flags=re.MULTILINE | re.DOTALL)


def main() -> int:
    parser = argparse.ArgumentParser(description="Password-verified Paper Stack human review.")
    parser.add_argument("paper", help="Path to PAPER-*.md")
    parser.add_argument("--reviewer", required=True, help="Registered human reviewer name")
    parser.add_argument("--decision", choices=["Accepted", "Approved", "Rejected"], default="Accepted")
    parser.add_argument("--notes", default="Password-verified human review.")
    parser.add_argument("--accept-validation", action="store_true", help="Mark human validation evidence checked")
    parser.add_argument("--set-status", action="store_true", help="Set paper status from review decision")
    args = parser.parse_args()

    path = Path(args.paper)
    root = paper_root_from_path(path)
    password = read_password()
    ok, message, reviewer_config = verify_password(root, args.reviewer, password)
    if not ok:
        print(f"FAIL {message}", file=sys.stderr)
        return 1

    paper = load_paper(path)
    token = verification_token(args.reviewer, paper["paper_id"], today(), args.decision, reviewer_config["password_hash"])
    text = replace_human_review(paper["text"], args.reviewer, args.decision, args.notes, token)
    if args.accept_validation:
        text = human_validation_checked(text)
    if args.set_status:
        metadata, _ = parse_frontmatter(text)
        metadata["status"] = "Accepted" if args.decision in {"Accepted", "Approved"} else "Rejected"
        metadata["updated"] = today()
        text = replace_frontmatter(text, metadata)
    path.write_text(text, encoding="utf-8")
    print(f"{paper['paper_id']} human review recorded by {args.reviewer}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
