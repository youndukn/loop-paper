#!/usr/bin/env python3
"""Create a Paper Stack paper with required closed-loop fill slots."""

from __future__ import annotations

import argparse
import re
import unicodedata
from datetime import date
from pathlib import Path


PAPER_ID_RE = re.compile(r"^PAPER-(\d+)")


def slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return slug or "closed-loop-paper"


def next_paper_id(papers_dir: Path) -> str:
    max_id = 0
    for path in papers_dir.glob("PAPER-*.md"):
        match = PAPER_ID_RE.match(path.name)
        if match:
            max_id = max(max_id, int(match.group(1)))
    return f"PAPER-{max_id + 1:04d}"


def table_rows(values: list[str], minimum: int, row_builder) -> str:
    rows = []
    for index in range(max(len(values), minimum)):
        value = values[index] if index < len(values) else ""
        rows.append(row_builder(index + 1, value))
    return "\n".join(rows)


def render_paper(
    *,
    paper_id: str,
    title: str,
    today: str,
    hypotheses: list[str],
    findings: list[str],
    references: list[str],
    min_hypotheses: int,
) -> str:
    hypothesis_rows = table_rows(
        hypotheses,
        min_hypotheses,
        lambda index, value: (
            f"| H{index} | {value or 'BEFORE_REQUIRED: falsifiable claim'} | "
            "BEFORE_REQUIRED: baseline evidence | "
            "BEFORE_REQUIRED: validation method | Open |"
        ),
    )
    finding_rows = table_rows(
        findings,
        1,
        lambda _index, value: (
            f"| {today} | {value or 'BEFORE_REQUIRED: concrete prior finding'} | "
            "BEFORE_REQUIRED: evidence path or command | "
            "BEFORE_REQUIRED: implementation boundary |"
        ),
    )
    reference_lines = "\n".join(
        f"- {reference}" for reference in references
    ) or "- BEFORE_REQUIRED: reference file, paper, artifact, or command output"
    return f"""---
paper_id: {paper_id}
title: {title}
status: Draft
created: {today}
updated: {today}
owners: []
reviewers: []
impact_score: TBD
closed_loop_schema: paper_closed_loop.v1
---

# {paper_id} {title}

## Abstract

BEFORE_REQUIRED: state the work unit, why it matters, and what completion would
prove. If this is retrospective, say so explicitly.

## Hypothesis

Every substantial change must start here before implementation.

### Hypothesis Ledger

| ID | Claim | Baseline Evidence | Validation Method | Verdict |
| --- | --- | --- | --- | --- |
{hypothesis_rows}

- [ ] Hypothesis is specific
- [ ] Hypothesis can be validated or rejected
- [ ] Baseline evidence is recorded before implementation

## Prior Research

Prior Research Status: BEFORE_REQUIRED: Present/Missing/Retrospective
Risk: BEFORE_REQUIRED: Low/Medium/High

### Concrete Findings Ledger

| Date | Finding | Evidence | Implementation Boundary |
| --- | --- | --- | --- |
{finding_rows}

- [ ] Prior work is cited, or missing prior work is explicitly acknowledged

## References

{reference_lines}

Relationship lines:

```text
References: None
Depends on: None
Supersedes: None
Contradicts: None
Extends: None
```

## Implementation Plan

TODO:

- [ ] BEFORE_REQUIRED: first implementation step tied to a hypothesis
- [ ] BEFORE_REQUIRED: second implementation step tied to a hypothesis

Risks:

- BEFORE_REQUIRED: risk or failure mode

Rollback/undo:

- BEFORE_REQUIRED: how to preserve or undo failed work

- [ ] Implementation plan is concrete
- [ ] Dependencies are named
- [ ] Risks are named

## Validation Plan

Define acceptable evidence before validating.

Before-change evidence:

- BEFORE_REQUIRED: command, artifact, metric, screenshot, or reason baseline is
  unavailable

After-change evidence to collect:

- AFTER_REQUIRED: command, artifact, metric, screenshot, or inspection

AI-actionable validation:

- [ ] BEFORE_REQUIRED: test/verifier/check to run

Human-required validation:

- [ ] Human validation required if the claim needs product, prose, UX, or taste
  judgment

## Execution Records

Run records:

- AFTER_REQUIRED: `.paper-stack/runs/RUN-YYYY-MM-DD-{paper_id}-short-name.md`

Fix records:

- AFTER_REQUIRED: `.paper-stack/fixes/FIX-YYYY-MM-DD-{paper_id}-short-name.md`

## Validation

Record actual evidence only after execution or inspection.

Before:

- BEFORE_REQUIRED: exact baseline output or inspected evidence

After:

- AFTER_REQUIRED: exact post-change output or inspected evidence

Verdict:

- AFTER_REQUIRED: mark each hypothesis Supported, Failed, Inconclusive, or
  Superseded, with the evidence reason.

Human validation evidence:

- [ ] Human validation required

## Agent Review

Agent reviewer:
Review date:
Decision: AFTER_REQUIRED: Draft/Plan Ready/Implemented/AI Validated/Rejected
Notes:

- AFTER_REQUIRED: agent review findings

- [ ] Agent reviewed paper structure
- [ ] Agent confirmed remaining human-only gates are still human-only

## Human Review

Human reviewer:
Review date:
Decision: Pending
Verification:
Notes:

- [ ] Human reviewed the paper
- [ ] Human accepted the validation evidence

## Impact Score

Impact score: TBD

Basis:

- Downstream references: AFTER_REQUIRED: TBD until measured
- Validation strength: AFTER_REQUIRED: TBD until validation runs
- Human grade: TBD
- Measured outcome: AFTER_REQUIRED: before/after delta or failed result

- [ ] Impact score is based on evidence, not agent guesswork
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(".paper-stack"))
    parser.add_argument("--title", required=True)
    parser.add_argument("--slug", default=None)
    parser.add_argument("--hypothesis", action="append", default=[])
    parser.add_argument("--finding", action="append", default=[])
    parser.add_argument("--reference", action="append", default=[])
    parser.add_argument("--min-hypotheses", type=int, default=2)
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    papers_dir = args.root / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)
    paper_id = next_paper_id(papers_dir)
    slug = args.slug or slugify(args.title)
    path = papers_dir / f"{paper_id}-{slug}.md"
    if path.exists():
        raise SystemExit(f"Refusing to overwrite existing paper: {path}")
    path.write_text(
        render_paper(
            paper_id=paper_id,
            title=args.title,
            today=args.date,
            hypotheses=args.hypothesis,
            findings=args.finding,
            references=args.reference,
            min_hypotheses=max(1, args.min_hypotheses),
        ),
        encoding="utf-8",
    )
    print(path)


if __name__ == "__main__":
    main()
