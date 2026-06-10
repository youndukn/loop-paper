#!/usr/bin/env python3
"""Check whether a closed-loop paper has required before/after slots filled."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from paperstack_common import REQUIRED_SECTIONS, checked_count, split_sections


PLACEHOLDER_RE = re.compile(r"\b(BEFORE_REQUIRED|AFTER_REQUIRED)\b")


def section(text: str, name: str) -> str:
    return split_sections(text).get(name, "")


def table_data_rows(section_text: str) -> list[str]:
    rows = []
    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if "---" in stripped:
            continue
        if stripped.lower().startswith("| id ") or stripped.lower().startswith("| date "):
            continue
        rows.append(stripped)
    return rows


def validate_paper(path: Path, phase: str) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if "closed_loop_schema: paper_closed_loop.v1" not in text:
        errors.append("missing closed_loop_schema: paper_closed_loop.v1")
    for name in REQUIRED_SECTIONS:
        if not section(text, name):
            errors.append(f"missing or empty section: {name}")
    hypothesis = section(text, "Hypothesis")
    rows = table_data_rows(hypothesis)
    if len(rows) < 1:
        errors.append("hypothesis ledger has no data rows")
    if phase in {"before", "after"}:
        before_placeholders = re.findall(r"\bBEFORE_REQUIRED\b", text)
        if before_placeholders:
            errors.append(
                f"before phase incomplete: {len(before_placeholders)} BEFORE_REQUIRED slots remain"
            )
        if checked_count(hypothesis) < 3:
            errors.append("before phase incomplete: hypothesis checkboxes are not all checked")
        prior = section(text, "Prior Research")
        if checked_count(prior) < 1:
            errors.append("before phase incomplete: prior research checkboxes are not all checked")
        plan = section(text, "Implementation Plan")
        if checked_count(plan) < 3:
            errors.append("before phase incomplete: implementation plan checkboxes are not all checked")
        validation_plan = section(text, "Validation Plan")
        if checked_count(validation_plan) < 1:
            errors.append("before phase incomplete: validation plan checkboxes are not all checked")
    if phase == "after":
        after_placeholders = re.findall(r"\bAFTER_REQUIRED\b", text)
        if after_placeholders:
            errors.append(
                f"after phase incomplete: {len(after_placeholders)} AFTER_REQUIRED slots remain"
            )
        validation = section(text, "Validation")
        if not re.search(r"\b(Supported|Failed|Inconclusive|Superseded)\b", validation):
            errors.append("after phase incomplete: no hypothesis verdict recorded")
        if checked_count(validation) < 1:
            errors.append("after phase incomplete: validation evidence checkbox is not checked")
        agent = section(text, "Agent Review")
        if checked_count(agent) < 2:
            errors.append("after phase incomplete: agent review checkboxes are not all checked")
        impact = section(text, "Impact Score")
        if checked_count(impact) < 1:
            errors.append("after phase incomplete: impact evidence checkbox is not checked")
    if phase == "draft" and not PLACEHOLDER_RE.search(text):
        errors.append("draft check expected fillable required slots, but none were found")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paper", type=Path)
    parser.add_argument(
        "--phase",
        choices=("draft", "before", "after"),
        default="after",
        help=(
            "draft: template has required slots; before: BEFORE_REQUIRED filled; "
            "after: BEFORE_REQUIRED and AFTER_REQUIRED filled with verdicts"
        ),
    )
    args = parser.parse_args()

    errors = validate_paper(args.paper, args.phase)
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        raise SystemExit(1)
    print(f"OK {args.paper} phase={args.phase}")


if __name__ == "__main__":
    main()
