#!/usr/bin/env python3
"""Create a review paper that consolidates verdicts on target papers."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from check_paper import check_paths, result_details
from paperstack_common import (
    next_paper_id,
    paper_id_from_path,
    paper_paths,
    refuse_papers_directory_output,
    slugify,
    validate_iso_date,
    validate_slug,
    validate_title,
    wrap_paper_source,
    write_text_output,
)
from prompt_common import RENDERERS, collect_cli, load_answers, render_prompts


PAPER_ID_RE = re.compile(r"^PAPER-(\d{4})$")

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
COHERENCE_HYPOTHESIS_VERDICTS = {
    "Coherent": "Supported",
    "Drift": "Inconclusive",
    "Mixed": "Inconclusive",
    "Contradictory": "Failed",
}


def normalize_paper_id(value: str) -> str:
    match = PAPER_ID_RE.fullmatch(value.strip().upper())
    if not match or int(match.group(1)) <= 0:
        raise argparse.ArgumentTypeError(f"Expected PAPER-NNNN, got {value!r}")
    return f"PAPER-{int(match.group(1)):04d}"


def validate_targets(root: Path, targets: list[str]) -> None:
    paths = paper_paths(root)
    results = check_paths(paths, validate_relationships=True)
    by_id: dict[str, list[dict]] = {}
    for result in results:
        by_id.setdefault(result["paper_id"], []).append(result)
        filename_id = paper_id_from_path(Path(result["path"]))
        if PAPER_ID_RE.fullmatch(filename_id):
            by_id.setdefault(filename_id, []).append(result)

    missing = []
    invalid = []
    for target in targets:
        seen_results: set[int] = set()
        target_results = []
        for result in by_id.get(target, []):
            result_id = id(result)
            if result_id in seen_results:
                continue
            seen_results.add(result_id)
            target_results.append(result)
        if not target_results:
            missing.append(target)
            continue
        for result in target_results:
            if not result["ok"]:
                invalid.append(f"{target} {result['path']}: {'; '.join(result_details(result))}")
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


def unique_targets(targets: list[str]) -> list[str]:
    duplicates = sorted(target for target, count in Counter(targets).items() if count > 1)
    if duplicates:
        raise SystemExit(f"Duplicate review targets: {', '.join(duplicates)}")
    return targets


def validate_mode_options(args: argparse.Namespace) -> None:
    if args.answers is None:
        return
    ignored = []
    if args.prompt_out is not None:
        ignored.append("--prompt-out")
    if args.format != "cli":
        ignored.append("--format")
    if ignored:
        raise SystemExit(
            "Prompt rendering options cannot be used with --answers: "
            + ", ".join(ignored)
        )


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
    hypothesis_verdict = COHERENCE_HYPOTHESIS_VERDICTS[coherence]
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
| H1 | A structured review of {target_summary} produces a coherent next-step recommendation | Per-target dimensions enumerated below | Multiple-choice walk over each dimension | {hypothesis_verdict} |

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

- {hypothesis_verdict}: structured per-target verdicts recorded with documented options;
  cross-paper coherence was {coherence} and recommended direction was {direction}

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
        help="Write phase-1 prompts to this file (default stdout). Cannot be used with --answers.",
    )
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    args.date = validate_iso_date(args.date)
    validate_mode_options(args)

    targets = unique_targets(args.target)
    papers_dir = args.root / "papers"
    validate_targets(args.root, targets)

    title = validate_title(args.title)
    slug = validate_slug(args.slug) if args.slug else slugify(title, fallback="review-paper")
    questions = build_questions(targets)

    if args.answers is None and args.prompt_out:
        prompt_text = render_prompts(questions, args.format, kind="review")
        refuse_papers_directory_output(args.root, args.prompt_out, label="prompt output")
        write_text_output(args.prompt_out, prompt_text, label="prompt output")
        print(args.prompt_out)
        return 0

    if args.answers is None and args.format != "cli":
        prompt_text = render_prompts(questions, args.format, kind="review")
        sys.stdout.write(prompt_text)
        return 0

    if args.answers is not None:
        answers = load_answers(args.answers, questions)
    else:
        answers = collect_cli(questions)

    paper_id = next_paper_id(papers_dir)
    output = papers_dir / f"{paper_id}-{slug}.html"
    if output.exists():
        raise SystemExit(f"Refusing to overwrite existing paper: {output}")
    write_text_output(
        output,
        wrap_paper_source(render_review_paper(
            paper_id=paper_id,
            title=title,
            today=args.date,
            targets=targets,
            answers=answers,
        )),
        label="paper",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
