#!/usr/bin/env python3
"""Check whether a closed-loop paper has required before/after slots filled."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from check_paper import check_file, check_paths, result_details
from paperstack_common import (
    REQUIRED_SECTIONS,
    STATUSES,
    checked_count,
    paper_paths,
    paper_root_from_path,
    require_paper_file,
    split_sections,
    validate_iso_date,
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
HYPOTHESIS_VERDICTS = {"Supported", "Failed", "Inconclusive", "Superseded"}
IMPLEMENTATION_PLAN_LABELS = ["TODO", "Risks", "Rollback/undo"]
VALIDATION_PLAN_LABELS = [
    "Before-change evidence",
    "After-change evidence to collect",
    "AI-actionable validation",
]
EXECUTION_RECORD_LABELS = ["Run records", "Fix records"]
VALIDATION_SECTION_LABELS = ["Before", "After", "Verdict", "AI validation evidence"]
AGENT_REVIEW_FIELD_RE = re.compile(
    r"^(Agent reviewer|Review date|Decision):[ \t]*(.*?)[ \t]*$",
    flags=re.MULTILINE,
)
IMPACT_SCORE_RE = re.compile(r"^Impact score:[ \t]*(.*?)[ \t]*$", flags=re.MULTILINE)
IMPACT_BASIS_RE = re.compile(
    r"^-\s+(Downstream references|Validation strength|Measured outcome):[ \t]*(.*?)[ \t]*$",
    flags=re.MULTILINE,
)
IMPACT_BASIS_FIELDS = ["Downstream references", "Validation strength", "Measured outcome"]
HYPOTHESIS_CHECKBOXES = [
    "Hypothesis is specific",
    "Hypothesis can be validated or rejected",
    "Baseline evidence is recorded before implementation",
]
PRIOR_RESEARCH_CHECKBOXES = [
    "Prior work is cited, or missing prior work is explicitly acknowledged",
]
IMPLEMENTATION_PLAN_CHECKBOXES = [
    "Implementation plan is concrete",
    "Dependencies are named",
    "Risks are named",
]
VALIDATION_CHECKBOXES = ["AI validation evidence recorded"]
AGENT_REVIEW_CHECKBOXES = [
    "Agent reviewed paper structure",
    "Agent confirmed evidence backs the recorded verdict",
]
IMPACT_SCORE_CHECKBOXES = [
    "Impact score is based on evidence, not agent guesswork",
]


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


def missing_checked_labels(section_text: str, labels: list[str]) -> list[str]:
    missing: list[str] = []
    for label in labels:
        pattern = rf"^\s*-\s+\[[xX]\]\s+{re.escape(label)}\s*$"
        if not re.search(pattern, section_text, flags=re.MULTILINE):
            missing.append(label)
    return missing


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
    elif checked_count(actionable) < 1:
        errors.append("validation plan AI-actionable validation block has no checked item")
    return errors


def validation_section_errors(section_text: str) -> list[str]:
    errors: list[str] = []
    for label in ["Before", "After"]:
        index = VALIDATION_SECTION_LABELS.index(label)
        body = labeled_block(section_text, label, VALIDATION_SECTION_LABELS[index + 1 :])
        if not non_checkbox_lines(body):
            errors.append(f"validation {label} block has no concrete evidence")
    return errors


def execution_record_errors(section_text: str) -> list[str]:
    errors: list[str] = []
    for index, label in enumerate(EXECUTION_RECORD_LABELS):
        body = labeled_block(section_text, label, EXECUTION_RECORD_LABELS[index + 1 :])
        if not non_checkbox_lines(body):
            errors.append(f"execution records {label} block has no concrete content")
    return errors


def agent_review_errors(section_text: str) -> list[str]:
    matches = list(AGENT_REVIEW_FIELD_RE.finditer(section_text))
    values = {match.group(1): match.group(2).strip() for match in matches}
    counts = {
        field: sum(1 for match in matches if match.group(1) == field)
        for field in ["Agent reviewer", "Review date", "Decision"]
    }
    errors: list[str] = []
    for field in ["Agent reviewer", "Review date", "Decision"]:
        if counts[field] > 1:
            errors.append(f"agent review duplicate {field}")
        if not values.get(field):
            errors.append(f"agent review missing {field}")
    decision = values.get("Decision")
    if decision and decision not in STATUSES:
        errors.append(
            "agent review invalid Decision: "
            f"{decision}; expected one of: {', '.join(STATUSES)}"
        )
    review_date = values.get("Review date")
    if review_date:
        try:
            validate_iso_date(review_date, label="Review date")
        except SystemExit as error:
            errors.append(str(error))
    return errors


def impact_score_errors(section_text: str) -> list[str]:
    errors: list[str] = []
    score_matches = list(IMPACT_SCORE_RE.finditer(section_text))
    if len(score_matches) > 1:
        errors.append("impact score duplicate Impact score value")
    score_match = score_matches[0] if score_matches else None
    if not score_match or not score_match.group(1).strip():
        errors.append("impact score missing Impact score value")
    elif score_match.group(1).strip() != "TBD":
        try:
            score = float(score_match.group(1).strip())
        except ValueError:
            errors.append("impact score value must be TBD or a number from 0 to 10")
        else:
            if not 0 <= score <= 10:
                errors.append("impact score value must be TBD or a number from 0 to 10")

    basis_matches = list(IMPACT_BASIS_RE.finditer(section_text))
    basis_values = {match.group(1): match.group(2).strip() for match in basis_matches}
    basis_counts = {
        field: sum(1 for match in basis_matches if match.group(1) == field)
        for field in IMPACT_BASIS_FIELDS
    }
    for field in IMPACT_BASIS_FIELDS:
        if basis_counts[field] > 1:
            errors.append(f"impact score basis duplicate {field}")
        if not basis_values.get(field):
            errors.append(f"impact score basis missing {field}")
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


def hypothesis_ledger_verdict_errors(rows: list[str]) -> list[str]:
    errors: list[str] = []
    for index, row in enumerate(rows, start=1):
        cells = table_cells(row)
        if len(cells) < 5:
            continue
        verdict = cells[4]
        if verdict not in HYPOTHESIS_VERDICTS:
            errors.append(
                f"hypothesis ledger row {index} has invalid after verdict: "
                f"{verdict or '<empty>'}; expected one of: "
                + ", ".join(sorted(HYPOTHESIS_VERDICTS))
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
        if missing_checked_labels(hypothesis, HYPOTHESIS_CHECKBOXES):
            errors.append("before phase incomplete: hypothesis checkboxes are not all checked")
        prior = section(text, "Prior Research")
        errors.extend(prior_research_errors(split_sections(text)))
        prior_rows = table_data_rows(prior)
        if len(prior_rows) < 1:
            errors.append("prior research ledger has no data rows")
        else:
            errors.extend(prior_research_ledger_errors(prior_rows))
        if missing_checked_labels(prior, PRIOR_RESEARCH_CHECKBOXES):
            errors.append("before phase incomplete: prior research checkboxes are not all checked")
        plan = section(text, "Implementation Plan")
        errors.extend(implementation_plan_errors(plan))
        if missing_checked_labels(plan, IMPLEMENTATION_PLAN_CHECKBOXES):
            errors.append("before phase incomplete: implementation plan checkboxes are not all checked")
        validation_plan = section(text, "Validation Plan")
        errors.extend(validation_plan_errors(validation_plan))
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
        errors.extend(hypothesis_ledger_verdict_errors(rows))
        if missing_checked_labels(validation, VALIDATION_CHECKBOXES):
            errors.append("after phase incomplete: validation evidence checkbox is not checked")
        execution_records = section(text, "Execution Records")
        errors.extend(execution_record_errors(execution_records))
        agent = section(text, "Agent Review")
        errors.extend(agent_review_errors(agent))
        if missing_checked_labels(agent, AGENT_REVIEW_CHECKBOXES):
            errors.append("after phase incomplete: agent review checkboxes are not all checked")
        impact = section(text, "Impact Score")
        errors.extend(impact_score_errors(impact))
        if missing_checked_labels(impact, IMPACT_SCORE_CHECKBOXES):
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
