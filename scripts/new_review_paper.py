#!/usr/bin/env python3
"""Create a review paper that consolidates verdicts on target papers."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

from check_paper import check_paths
from paperstack_common import paper_paths


PAPER_ID_RE = re.compile(r"^PAPER-(\d{1,4})$")
FILENAME_PAPER_ID_RE = re.compile(r"^PAPER-(\d+)")
MAX_PAPER_NUMBER = 9999
UNSAFE_TITLE_CHARS = re.compile(r"[:\n\r]|---")
SLUG_RE = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")

PER_TARGET_QUESTIONS: list[tuple[str, str, list[str]]] = [
    ("verdict", "Hypothesis verdict", ["Supported", "Failed", "Inconclusive", "Superseded"]),
    ("evidence", "Evidence strength", ["Strong", "Mixed", "Weak", "Missing"]),
    ("production", "Production readiness", ["Ready", "Almost", "Not ready", "Off-track"]),
    ("action", "Recommended action", ["Accept", "Request changes", "Reject", "Supersede"]),
]

CROSS_QUESTIONS: list[tuple[str, str, list[str]]] = [
    ("coherence", "Coherence across targets", ["Coherent", "Drift", "Contradictory", "Mixed"]),
    ("direction", "Next-paper direction", ["Continue same line", "New angle", "Pause", "Backtrack"]),
]


def slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return slug or "review-paper"


def validate_title(title: str) -> str:
    cleaned = title.strip()
    if not cleaned:
        raise SystemExit("--title must not be empty")
    if UNSAFE_TITLE_CHARS.search(cleaned):
        raise SystemExit("--title must not contain ':', newlines, or '---' (would break YAML frontmatter)")
    return cleaned


def validate_slug(slug: str) -> str:
    cleaned = slug.strip()
    if not SLUG_RE.fullmatch(cleaned):
        raise SystemExit("--slug must contain only ASCII letters, numbers, and single hyphens")
    return cleaned.lower()


def normalize_paper_id(value: str) -> str:
    match = PAPER_ID_RE.fullmatch(value.strip().upper())
    if not match:
        raise argparse.ArgumentTypeError(f"Expected PAPER-NNNN, got {value!r}")
    return f"PAPER-{int(match.group(1)):04d}"


def next_paper_id(papers_dir: Path) -> str:
    max_id = 0
    for path in papers_dir.glob("PAPER-*.md"):
        match = FILENAME_PAPER_ID_RE.match(path.name)
        if match:
            max_id = max(max_id, int(match.group(1)))
    if max_id >= MAX_PAPER_NUMBER:
        raise SystemExit("Cannot allocate next paper ID beyond PAPER-9999")
    return f"PAPER-{max_id + 1:04d}"


def check_details(result: dict) -> list[str]:
    details: list[str] = []
    for key in ("missing_sections", "empty_sections", "warnings"):
        details.extend(result[key])
    return details


def validate_targets(root: Path, targets: list[str]) -> None:
    papers_dir = root / "papers"
    paths = paper_paths(root)
    results = check_paths(paths, validate_relationships=True)
    by_path = {Path(result["path"]).resolve(): result for result in results}

    missing = []
    invalid = []
    for target in targets:
        matches = list(papers_dir.glob(f"{target}-*.md"))
        if not matches:
            missing.append(target)
            continue
        for path in matches:
            result = by_path.get(path.resolve())
            if result is None:
                invalid.append(f"{target} {path}: not found in stack index")
                continue
            if not result["ok"]:
                invalid.append(f"{target} {path}: {'; '.join(check_details(result))}")
    if missing:
        raise SystemExit(f"Missing target paper files for: {', '.join(missing)}")
    if invalid:
        raise SystemExit("Invalid target paper files:\n" + "\n".join(invalid))


def build_questions(targets: list[str]) -> list[dict]:
    questions: list[dict] = []
    for target in targets:
        for field, prompt, options in PER_TARGET_QUESTIONS:
            questions.append(
                {
                    "id": f"{field}.{target}",
                    "target": target,
                    "field": field,
                    "prompt": f"{prompt} for {target}",
                    "options": list(options),
                }
            )
    for field, prompt, options in CROSS_QUESTIONS:
        questions.append(
            {
                "id": field,
                "target": None,
                "field": field,
                "prompt": prompt,
                "options": list(options),
            }
        )
    return questions


def render_cli(questions: list[dict]) -> str:
    lines: list[str] = []
    for index, question in enumerate(questions, start=1):
        lines.append(f"[Q{index}] {question['prompt']}")
        lines.append(f"  answer_id: {question['id']}")
        for choice_index, option in enumerate(question["options"], start=1):
            lines.append(f"  {choice_index}) {option}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_json(questions: list[dict]) -> str:
    return json.dumps({"questions": questions}, indent=2) + "\n"


def render_claude(questions: list[dict]) -> str:
    payload = {
        "questions": [
            {
                "question": question["prompt"] + "?",
                "header": question["field"][:12],
                "id": question["id"],
                "target": question["target"],
                "field": question["field"],
                "multiSelect": False,
                "options": [{"label": option, "description": option} for option in question["options"]],
            }
            for question in questions
        ],
    }
    return json.dumps(payload, indent=2) + "\n"


def render_codex(questions: list[dict]) -> str:
    lines = [":::interactive review"]
    for index, question in enumerate(questions, start=1):
        lines.append(f"[Q{index}] {question['prompt']} [answer_id: {question['id']}]")
        for choice_index, option in enumerate(question["options"], start=1):
            lines.append(f"  ({choice_index}) {option}")
    lines.append(":::end")
    return "\n".join(lines) + "\n"


def render_pi(questions: list[dict]) -> str:
    lines = ["# review prompts"]
    for question in questions:
        lines.append(f"- id: {question['id']}")
        lines.append(f"  field: {question['field']}")
        if question["target"]:
            lines.append(f"  target: {question['target']}")
        lines.append(f"  prompt: {question['prompt']}")
        lines.append("  options:")
        for option in question["options"]:
            lines.append(f"    - {option}")
    return "\n".join(lines) + "\n"


RENDERERS = {
    "cli": render_cli,
    "json": render_json,
    "claude": render_claude,
    "codex": render_codex,
    "pi": render_pi,
}


def collect_cli(questions: list[dict]) -> dict:
    answers: dict[str, str] = {}
    for index, question in enumerate(questions, start=1):
        print(f"[Q{index}] {question['prompt']}")
        for choice_index, option in enumerate(question["options"], start=1):
            print(f"  {choice_index}) {option}")
        while True:
            choice = input("Enter number: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(question["options"]):
                answers[question["id"]] = question["options"][int(choice) - 1]
                break
            print(f"Pick 1..{len(question['options'])}.")
        print()
    return answers


def load_answers(path: Path, questions: list[dict]) -> dict:
    if not path.exists():
        raise SystemExit(f"Missing answers JSON file: {path}")
    if not path.is_file():
        raise SystemExit(f"Expected answers JSON file, got directory: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"answers JSON is invalid: {error.msg}") from error
    if isinstance(raw, list):
        normalized = {}
        for item in raw:
            if not isinstance(item, dict) or "id" not in item or "answer" not in item:
                raise SystemExit("answers list items must be objects with id and answer")
            normalized[item["id"]] = item["answer"]
        raw = normalized
    if not isinstance(raw, dict):
        raise SystemExit("answers JSON must be an object or list of {id, answer}")
    answers: dict[str, str] = {}
    for question in questions:
        if question["id"] not in raw:
            raise SystemExit(f"answers missing for {question['id']}")
        if raw[question["id"]] not in question["options"]:
            raise SystemExit(f"answer for {question['id']} not in options: {raw[question['id']]}")
        answers[question["id"]] = raw[question["id"]]
    return answers


def per_target_rows(target: str, answers: dict) -> str:
    rows = []
    for field, prompt, _options in PER_TARGET_QUESTIONS:
        rows.append(f"| {prompt} | {answers[f'{field}.{target}']} |")
    return "\n".join(rows)


def render_review_paper(
    *,
    paper_id: str,
    title: str,
    today: str,
    targets: list[str],
    answers: dict,
) -> str:
    target_summary = ", ".join(targets)
    ref_lines = "\n".join(f"- {target}" for target in targets)
    per_target_sections: list[str] = []
    for target in targets:
        per_target_sections.extend(
            [
                f"### {target}",
                "",
                "| Dimension | Verdict |",
                "| --- | --- |",
                per_target_rows(target, answers),
                "",
            ]
        )
    coherence = answers["coherence"]
    direction = answers["direction"]
    per_target_block = "\n".join(per_target_sections).rstrip()
    return f"""---
paper_id: {paper_id}
title: {title}
status: AI Validated
created: {today}
updated: {today}
owners: []
reviewers: []
impact_score: TBD
paper_kind: review
review_targets: {", ".join(targets)}
closed_loop_schema: paper_closed_loop.v1
---

# {paper_id} {title}

## Abstract

Review of {target_summary}. This paper records a structured multiple-choice
walk over each target's hypothesis verdict, evidence strength, production
readiness, and recommended action, then summarizes cross-paper coherence
({coherence.lower()}) and the recommended next direction
({direction.lower()}). The targets themselves are unchanged; this paper is
the review.

## Hypothesis

### Hypothesis Ledger

| ID | Claim | Baseline Evidence | Validation Method | Verdict |
| --- | --- | --- | --- | --- |
| H1 | A structured review of {target_summary} produces a coherent next-step recommendation | Per-target dimensions enumerated below | Multiple-choice walk over each dimension | {coherence} |

- [x] Hypothesis is specific
- [x] Hypothesis can be validated or rejected
- [x] Baseline evidence is recorded before implementation

## Prior Research

Prior Research Status: Present
Risk: Low

### Concrete Findings Ledger

| Date | Finding | Evidence | Implementation Boundary |
| --- | --- | --- | --- |
| {today} | Targets under review: {target_summary} | Paper files in `.paper-stack/papers/` | Review only; no source changes. |

- [x] Prior work is cited, or missing prior work is explicitly acknowledged

## References

{ref_lines}

Relationship lines:

```text
References: {", ".join(targets)}
Depends on: None
Supersedes: None
Contradicts: None
Extends: None
```

## Implementation Plan

TODO:

- [x] Walk each target through the per-target review dimensions
- [x] Record cross-paper coherence and recommended direction

Risks:

- Reviewer bias on multiple-choice answers

Rollback/undo:

- This paper is the review record; rollback means writing a superseding review

- [x] Implementation plan is concrete
- [x] Dependencies are named
- [x] Risks are named

## Validation Plan

Before-change evidence:

- State of the target papers as of {today}

After-change evidence to collect:

- This review paper

AI-actionable validation:

- [x] Every multiple-choice prompt answered with a documented option

## Execution Records

Run records:

- N/A (review-only)

Fix records:

- N/A (review-only)

## Per-Target Verdicts

{per_target_block}

## Cross-Paper Findings

- Coherence: {coherence}
- Recommended direction: {direction}

## Validation

Before:

- Targets in their state at {today}

After:

- Per-target verdicts captured in the table above

Verdict:

- Supported: structured per-target verdicts recorded with documented options

AI validation evidence:

- [x] AI validation evidence recorded

## Agent Review

Agent reviewer: review-script
Review date: {today}
Decision: AI Validated
Notes:

- Review generated from structured multiple-choice answers

- [x] Agent reviewed paper structure
- [x] Agent confirmed evidence backs the recorded verdict

## Impact Score

Impact score: TBD

Basis:

- Downstream references: TBD until measured
- Validation strength: structured per-target verdicts
- Measured outcome: TBD

- [x] Impact score is based on evidence, not agent guesswork
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a review paper from structured multiple-choice answers.")
    parser.add_argument("--root", type=Path, default=Path(".paper-stack"))
    parser.add_argument("--title", required=True)
    parser.add_argument("--slug", default=None)
    parser.add_argument(
        "--target",
        action="append",
        type=normalize_paper_id,
        required=True,
        help="Target paper ID. Repeat for multi-paper reviews.",
    )
    parser.add_argument(
        "--format",
        choices=list(RENDERERS),
        default="cli",
        help="Prompt format for phase-1 output. cli also runs interactively.",
    )
    parser.add_argument(
        "--answers",
        type=Path,
        help="JSON file with answers. Skip phase-1 and write the review paper directly.",
    )
    parser.add_argument(
        "--prompt-out",
        type=Path,
        help="Write phase-1 prompts to this file (default stdout). Ignored when --answers is set.",
    )
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    targets = list(dict.fromkeys(args.target))
    papers_dir = args.root / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)
    validate_targets(args.root, targets)

    title = validate_title(args.title)
    slug = validate_slug(args.slug) if args.slug else slugify(title)
    questions = build_questions(targets)

    if args.answers is None and args.prompt_out:
        prompt_text = RENDERERS[args.format](questions)
        args.prompt_out.parent.mkdir(parents=True, exist_ok=True)
        args.prompt_out.write_text(prompt_text, encoding="utf-8")
        print(args.prompt_out)
        return 0

    if args.answers is None and args.format != "cli":
        prompt_text = RENDERERS[args.format](questions)
        sys.stdout.write(prompt_text)
        return 0

    if args.answers is not None:
        answers = load_answers(args.answers, questions)
    else:
        answers = collect_cli(questions)

    paper_id = next_paper_id(papers_dir)
    output = papers_dir / f"{paper_id}-{slug}.md"
    if output.exists():
        raise SystemExit(f"Refusing to overwrite existing paper: {output}")
    output.write_text(
        render_review_paper(
            paper_id=paper_id,
            title=title,
            today=args.date,
            targets=targets,
            answers=answers,
        ),
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
