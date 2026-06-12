#!/usr/bin/env python3
"""Create a Paper Stack paper with required closed-loop fill slots."""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

from paper_html import INTERACTIVE_FENCE
from paperstack_common import (
    find_ids,
    parse_frontmatter,
    read_paper_text,
    markdown_inline,
    markdown_table_cell,
    next_paper_id,
    paper_paths,
    paper_id_from_path,
    proposal_gate_applies,
    slugify,
    validate_iso_date,
    validate_slug,
    validate_title,
    wrap_paper_source,
    write_text_output,
)


HEADING_LINE_RE = re.compile(r"^#", flags=re.MULTILINE)


def validate_abstract(abstract: str | None) -> str | None:
    if abstract is None:
        return None
    cleaned = abstract.strip()
    if not cleaned:
        return None
    if HEADING_LINE_RE.search(cleaned):
        raise SystemExit("--abstract must not contain markdown heading lines")
    return cleaned


def table_rows(values: list[str], minimum: int, row_builder) -> str:
    rows = []
    for index in range(max(len(values), minimum)):
        value = values[index] if index < len(values) else ""
        rows.append(row_builder(index + 1, value))
    return "\n".join(rows)


def reference_paper_ids(references: list[str], *, paper_id: str, known_ids: set[str]) -> list[str]:
    ids = sorted({found for reference in references for found in find_ids(reference)})
    if paper_id in ids:
        raise SystemExit(f"Reference list cannot target the paper being created: {paper_id}")
    missing = [item for item in ids if item not in known_ids]
    if missing:
        raise SystemExit("Reference list contains unknown paper IDs: " + ", ".join(missing))
    return ids


def render_paper(
    *,
    paper_id: str,
    title: str,
    today: str,
    hypotheses: list[str],
    findings: list[str],
    references: list[str],
    reference_ids: list[str],
    min_hypotheses: int,
    abstract: str | None = None,
    proposal_record: str | None = None,
) -> str:
    hypothesis_rows = table_rows(
        hypotheses,
        min_hypotheses,
        lambda index, value: (
            f"| H{index} | {markdown_table_cell(value or 'BEFORE_REQUIRED: falsifiable claim')} | "
            "BEFORE_REQUIRED: baseline evidence | "
            "BEFORE_REQUIRED: validation method | Open |"
        ),
    )
    finding_rows = table_rows(
        findings,
        1,
        lambda _index, value: (
            f"| {today} | {markdown_table_cell(value or 'BEFORE_REQUIRED: concrete prior finding')} | "
            "BEFORE_REQUIRED: evidence path or command | "
            "BEFORE_REQUIRED: implementation boundary |"
        ),
    )
    reference_lines = "\n".join(
        f"- {markdown_inline(reference)}" for reference in references
    ) or "- BEFORE_REQUIRED: reference file, paper, artifact, or command output"
    relationship_references = ", ".join(reference_ids) if reference_ids else "None"
    provenance_lines = (
        f"abstract_provenance: human_selected\nproposal_record: {proposal_record}\n"
        if proposal_record
        else ""
    )
    return f"""---
paper_id: {paper_id}
title: {title}
status: Draft
created: {today}
updated: {today}
owners: []
reviewers: []
impact_score: TBD
paper_kind: closed_loop
closed_loop_schema: paper_closed_loop.v3
{provenance_lines}---

# {paper_id} {title}

## Abstract

{abstract or "BEFORE_REQUIRED: state the work unit, why it matters, and what completion would prove. If this is retrospective, say so explicitly."}

## Hypothesis

Every change must start here before implementation.

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
References: {relationship_references}
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
  Superseded in both the Hypothesis Ledger Verdict column and this block,
  with the evidence reason.

AI validation evidence:

- [ ] AI validation evidence recorded

## Agent Review

Agent reviewer:
Review date:
Decision: AFTER_REQUIRED: Draft/Plan Ready/Implemented/AI Validated/Rejected
Notes:

- AFTER_REQUIRED: agent review findings

- [ ] Agent reviewed paper structure
- [ ] Agent confirmed evidence backs the recorded verdict

## Impact Score

Impact score: TBD

Basis:

- Downstream references: AFTER_REQUIRED: TBD until measured
- Validation strength: AFTER_REQUIRED: TBD until validation runs
- Measured outcome: AFTER_REQUIRED: before/after delta or failed result

- [ ] Impact score is based on evidence, not agent guesswork
"""


def create_paper(
    *,
    root: Path,
    title: str,
    hypotheses: list[str],
    findings: list[str],
    references: list[str],
    paper_date: str,
    min_hypotheses: int = 2,
    slug: str | None = None,
    abstract: str | None = None,
    proposal_record: str | None = None,
) -> Path:
    paper_date = validate_iso_date(paper_date)
    if min_hypotheses < 2:
        raise SystemExit("--min-hypotheses must be >= 2 for paper_closed_loop.v3")
    if proposal_record and not (root / proposal_record).is_file():
        raise SystemExit(f"Missing proposal record file: {root / proposal_record}")

    papers_dir = root / "papers"
    existing_paths = paper_paths(root)
    pending = []
    for existing in existing_paths:
        text = read_paper_text(existing)
        if INTERACTIVE_FENCE in text and not parse_frontmatter(text)[0].get("interaction_review"):
            pending.append(paper_id_from_path(existing))
    if pending:
        raise SystemExit(
            "Interactive papers pending human review: " + ", ".join(pending) + ". "
            "Ask the human to review the interaction (pipeline.py --open <id>), "
            "then record the answer with ack_interaction.py --status reviewed|waived."
        )
    paper_id = next_paper_id(papers_dir)
    if not proposal_record and proposal_gate_applies(root, paper_id):
        raise SystemExit(
            f"{paper_id} requires a human-gated proposal in this stack; "
            "create it via propose_paper.py instead of new_closed_loop_paper.py"
        )
    title = validate_title(title)
    slug = validate_slug(slug) if slug else slugify(title, fallback="closed-loop-paper")
    known_ids = {paper_id_from_path(path) for path in existing_paths}
    reference_ids = reference_paper_ids(references, paper_id=paper_id, known_ids=known_ids)
    path = papers_dir / f"{paper_id}-{slug}.html"
    if path.exists():
        raise SystemExit(f"Refusing to overwrite existing paper: {path}")
    write_text_output(
        path,
        wrap_paper_source(render_paper(
            paper_id=paper_id,
            title=title,
            today=paper_date,
            hypotheses=hypotheses,
            findings=findings,
            references=references,
            reference_ids=reference_ids,
            min_hypotheses=min_hypotheses,
            abstract=validate_abstract(abstract),
            proposal_record=proposal_record,
        )),
        label="paper",
    )
    return path


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
    parser.add_argument(
        "--abstract",
        default=None,
        help="Abstract text. If omitted, the BEFORE_REQUIRED placeholder is used.",
    )
    parser.add_argument(
        "--proposal-record",
        default=None,
        help="Root-relative proposal record path; marks the abstract and hypotheses as human-selected.",
    )
    args = parser.parse_args()
    print(
        create_paper(
            root=args.root,
            title=args.title,
            hypotheses=args.hypothesis,
            findings=args.finding,
            references=args.reference,
            paper_date=args.date,
            min_hypotheses=args.min_hypotheses,
            slug=args.slug,
            abstract=args.abstract,
            proposal_record=args.proposal_record,
        )
    )


if __name__ == "__main__":
    main()
