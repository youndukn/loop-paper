#!/usr/bin/env python3
"""Check whether a closed-loop paper has required before/after slots filled."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from check_paper import check_file, check_paths, result_details
from paperstack_common import (
    REQUIRED_SECTIONS,
    checked_count,
    paper_paths,
    paper_root_from_path,
    require_paper_file,
    split_sections,
)


PLACEHOLDER_RE = re.compile(r"\b(BEFORE_REQUIRED|AFTER_REQUIRED)\b")
VERDICT_BULLET_RE = re.compile(
    r"^\s*-\s+(Supported|Failed|Inconclusive|Superseded)\s*:",
    flags=re.MULTILINE,
)
PRIOR_STATUS_RE = re.compile(r"^Prior Research Status:\s*(.+?)\s*$", flags=re.MULTILINE)
RISK_RE = re.compile(r"^Risk:\s*(.+?)\s*$", flags=re.MULTILINE)
PRIOR_RESEARCH_STATUSES = {"Present", "Missing", "Retrospective"}
RISK_LEVELS = {"Low", "Medium", "High"}
IMPLEMENTATION_PLAN_LABELS = ["TODO", "Risks", "Rollback/undo"]
VALIDATION_PLAN_LABELS = [
    "Before-change evidence",
    "After-change evidence to collect",
    "AI-actionable validation",
]
VALIDATION_SECTION_LABELS = ["Before", "After", "Verdict", "AI validation evidence"]


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


def table_cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def non_checkbox_lines(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"- \[[ xX]\]", stripped):
            continue
        lines.append(stripped)
    return lines


def content_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def labeled_block(section_text: str, label: str, following_labels: list[str]) -> str:
    labels = "|".join(re.escape(item) for item in following_labels)
    pattern = rf"^{re.escape(label)}:\s*$\n(?P<body>.*?)(?=^(?:{labels}):\s*$|\Z)"
    match = re.search(pattern, section_text, flags=re.MULTILINE | re.DOTALL)
    return match.group("body") if match else ""


def implementation_plan_errors(section_text: str) -> list[str]:
    errors: list[str] = []
    for index, label in enumerate(IMPLEMENTATION_PLAN_LABELS):
        following = IMPLEMENTATION_PLAN_LABELS[index + 1 :]
        body = labeled_block(section_text, label, following)
        lines = content_lines(body) if label == "TODO" else non_checkbox_lines(body)
        if not lines:
            errors.append(f"implementation plan {label} block has no concrete content")
    return errors


def validation_plan_errors(section_text: str) -> list[str]:
    errors: list[str] = []
    before = labeled_block(
        section_text,
        "Before-change evidence",
        VALIDATION_PLAN_LABELS[1:],
    )
    if not non_checkbox_lines(before):
        errors.append("validation plan Before-change evidence block has no concrete content")

    actionable = labeled_block(section_text, "AI-actionable validation", [])
    if not content_lines(actionable):
        errors.append("validation plan AI-actionable validation block has no concrete content")
    return errors


def validation_section_errors(section_text: str) -> list[str]:
    errors: list[str] = []
    for label in ["Before", "After"]:
        index = VALIDATION_SECTION_LABELS.index(label)
        body = labeled_block(section_text, label, VALIDATION_SECTION_LABELS[index + 1 :])
        if not non_checkbox_lines(body):
            errors.append(f"validation {label} block has no concrete evidence")
    return errors


def hypothesis_ledger_errors(rows: list[str]) -> list[str]:
    errors: list[str] = []
    required = [
        ("Claim", 1),
        ("Baseline Evidence", 2),
        ("Validation Method", 3),
    ]
    for index, row in enumerate(rows, start=1):
        cells = table_cells(row)
        if len(cells) < 5:
            errors.append(f"hypothesis ledger row {index} must have 5 columns")
            continue
        missing = [label for label, cell_index in required if not cells[cell_index]]
        if missing:
            errors.append(
                f"hypothesis ledger row {index} has empty required cells: "
                + ", ".join(missing)
            )
    return errors


def prior_research_ledger_errors(rows: list[str]) -> list[str]:
    errors: list[str] = []
    required = [
        ("Date", 0),
        ("Finding", 1),
        ("Evidence", 2),
        ("Implementation Boundary", 3),
    ]
    for index, row in enumerate(rows, start=1):
        cells = table_cells(row)
        if len(cells) < 4:
            errors.append(f"prior research ledger row {index} must have 4 columns")
            continue
        missing = [label for label, cell_index in required if not cells[cell_index]]
        if missing:
            errors.append(
                f"prior research ledger row {index} has empty required cells: "
                + ", ".join(missing)
            )
    return errors


def prior_research_errors(sections: dict[str, str]) -> list[str]:
    prior = sections.get("Prior Research", "")
    refs = sections.get("References", "")
    errors: list[str] = []
    status_match = PRIOR_STATUS_RE.search(prior)
    if not status_match:
        errors.append("prior research must declare Prior Research Status")
    else:
        status = status_match.group(1).strip()
        if status not in PRIOR_RESEARCH_STATUSES:
            errors.append(
                "invalid Prior Research Status: "
                f"{status}; expected Present, Missing, or Retrospective"
            )
    risk_match = RISK_RE.search(prior)
    if not risk_match:
        errors.append("prior research must declare Risk")
    else:
        risk = risk_match.group(1).strip()
        if risk not in RISK_LEVELS:
            errors.append(f"invalid Risk: {risk}; expected Low, Medium, or High")
    if "Prior Research Status: Missing" in prior and "Risk: High" not in prior:
        errors.append("missing prior research must explicitly mark Risk: High")
    if "- TBD" in refs and "Prior Research Status: Missing" not in prior:
        errors.append("references are TBD without explicit missing prior research acknowledgement")
    return errors


def structural_result(path: Path) -> dict:
    require_paper_file(path)
    if path.parent.name != "papers":
        return check_file(path)

    root = paper_root_from_path(path)
    results = check_paths(paper_paths(root), validate_relationships=True)
    for result in results:
        if Path(result["path"]) == path:
            return result
    raise SystemExit(f"Paper is not under a recognized papers directory: {path}")


def validate_paper(path: Path, phase: str) -> list[str]:
    try:
        structural = structural_result(path)
    except SystemExit as error:
        return [str(error)]
    structural_errors = result_details(structural)
    require_paper_file(path)
    text = path.read_text(encoding="utf-8")
    errors: list[str] = [
        "Paper structure check failed: " + "; ".join(structural_errors)
    ] if structural_errors else []
    if "closed_loop_schema: paper_closed_loop.v1" not in text:
        errors.append("missing closed_loop_schema: paper_closed_loop.v1")
    for name in REQUIRED_SECTIONS:
        if not section(text, name):
            errors.append(f"missing or empty section: {name}")
    hypothesis = section(text, "Hypothesis")
    rows = table_data_rows(hypothesis)
    if len(rows) < 1:
        errors.append("hypothesis ledger has no data rows")
    else:
        errors.extend(hypothesis_ledger_errors(rows))
    if phase in {"before", "after"}:
        before_placeholders = re.findall(r"\bBEFORE_REQUIRED\b", text)
        if before_placeholders:
            errors.append(
                f"before phase incomplete: {len(before_placeholders)} BEFORE_REQUIRED slots remain"
            )
        if checked_count(hypothesis) < 3:
            errors.append("before phase incomplete: hypothesis checkboxes are not all checked")
        prior = section(text, "Prior Research")
        errors.extend(prior_research_errors(split_sections(text)))
        prior_rows = table_data_rows(prior)
        if len(prior_rows) < 1:
            errors.append("prior research ledger has no data rows")
        else:
            errors.extend(prior_research_ledger_errors(prior_rows))
        if checked_count(prior) < 1:
            errors.append("before phase incomplete: prior research checkboxes are not all checked")
        plan = section(text, "Implementation Plan")
        errors.extend(implementation_plan_errors(plan))
        if checked_count(plan) < 3:
            errors.append("before phase incomplete: implementation plan checkboxes are not all checked")
        validation_plan = section(text, "Validation Plan")
        errors.extend(validation_plan_errors(validation_plan))
        if checked_count(validation_plan) < 1:
            errors.append("before phase incomplete: validation plan checkboxes are not all checked")
    if phase == "after":
        after_placeholders = re.findall(r"\bAFTER_REQUIRED\b", text)
        if after_placeholders:
            errors.append(
                f"after phase incomplete: {len(after_placeholders)} AFTER_REQUIRED slots remain"
            )
        validation = section(text, "Validation")
        errors.extend(validation_section_errors(validation))
        if not VERDICT_BULLET_RE.search(validation):
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
