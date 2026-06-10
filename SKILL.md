---
name: loop-paper
description: Use when initializing, planning, executing, validating, summarizing, combining, or closing research-paper-style work loops. Trigger for creating a project-local .paper-stack structure, Paper Stack workflows, closed-loop papers, deterministic paper dashboards, hypothesis/baseline/validation gates, human-review-safe acceptance, combining multiple papers by ID interval, or selecting best reference papers for a new or closing paper.
---

# Loop Paper

Loop Paper treats meaningful work as a paper-backed loop: claim, prior work,
implementation plan, validation plan, evidence, verdict, review, and impact.

Use `.paper-stack/` in the active project unless the user gives another root.
Resolve scripts relative to this `SKILL.md` and execute them with absolute
paths when working outside the skill directory.

## Initialize A Project

For a new project or a repo without a clear paper structure, initialize first:

```bash
python3 scripts/init_loop_paper.py \
  --root .paper-stack \
  --project-name "Project Name"
```

This creates the generalizable directory contract:

```text
.paper-stack/
  papers/       canonical paper loops
  runs/         command, validation, benchmark, and inspection evidence
  fixes/        implementation change records and rollback notes
  references/   stable prior work and source notes
  inbox/        untriaged claims, links, and ideas
  dashboard/    generated reports; do not hand-edit
  config/       local Loop Paper config and reviewer registry
  archive/      superseded or exported material
```

Use `--seed-paper` when the initialization itself should create the first
closed-loop paper.

## Core Rules

1. Create or locate the active paper before substantial implementation.
2. Record the hypothesis, baseline evidence, implementation TODOs, validation
   plan, and references before changing code or prompts.
3. Keep `Validation Plan` separate from `Validation`; the plan says what would
   count, and validation records what actually happened.
4. Mark AI-actionable validation only after executing or inspecting evidence.
5. Never mark human validation, human review, or human impact grades complete
   by hand. Use `scripts/human_review.py` for password-verified human review.
6. Use deterministic scripts for paper metadata, graph edges, dashboards,
   impact components, reports, transitions, and combined summaries.
7. If work happened before the paper existed, mark the evidence as
   retrospective. Do not rewrite history to make the hypothesis earlier.

## Main Workflow

1. Create a closed-loop paper:

   ```bash
   python3 scripts/new_closed_loop_paper.py \
     --root .paper-stack \
     --title "Short Work Unit Title" \
     --hypothesis "The change will produce a measurable effect" \
     --finding "Concrete prior finding that justifies this work" \
     --reference "docs/current_findings.md"
   ```

2. Fill all `BEFORE_REQUIRED` slots, then check the before phase:

   ```bash
   python3 scripts/check_closed_loop_paper.py \
     .paper-stack/papers/PAPER-XXXX-title.md \
     --phase before
   ```

3. Implement only the active hypothesis.

4. Record after evidence, verdicts, run/fix records, and reference edges:

   ```text
   References: PAPER-0001
   Depends on: PAPER-0002
   Supersedes: None
   Contradicts: None
   Extends: PAPER-0003
   ```

5. Check the after phase and run the deterministic pipeline:

   ```bash
   python3 scripts/check_closed_loop_paper.py \
     .paper-stack/papers/PAPER-XXXX-title.md \
     --phase after

   python3 scripts/pipeline.py .paper-stack
   ```

## Deterministic Combine

Use `scripts/combine_papers.py` when closing multiple papers, creating a
summary across nearby papers, or choosing references for a new paper.

Always select papers by an explicit deterministic interval or explicit IDs:

```bash
python3 scripts/combine_papers.py .paper-stack \
  --from PAPER-0030 \
  --to PAPER-0045 \
  --interval-size 5 \
  --mode both \
  --target-paper PAPER-0046 \
  --output .paper-stack/dashboard/combined-PAPER-0030-PAPER-0045.md
```

Selection is stable by numeric paper ID. Summary chunks are stable by
`--interval-size`. Reference candidates are ranked without model judgment using
status, inbound graph references, explicit relationship edges, paper-ID
distance to the target, and deterministic text-term overlap.

Use:

- `--mode summary` for interval summaries only.
- `--mode references` for ranked reference candidates and relationship lines.
- `--mode both` when closing a set of papers and preparing a next paper.
- `--last N` only for a recent deterministic suffix.
- `--ids PAPER-0001 PAPER-0007` only when the user names exact papers.

## Paper States

Use these statuses exactly unless the project defines a local variant:

```text
Draft
Research Ready
Plan Ready
Implementing
Implemented
AI Validated
Human Review Required
Accepted
Rejected
Superseded
```

Allowed progression:

```text
Draft -> Research Ready -> Plan Ready -> Implementing -> Implemented -> AI Validated -> Human Review Required -> Accepted
```

Move to `Rejected` when a hypothesis fails or the user rejects the paper. Move
to `Superseded` when a later paper replaces it.

## Required Sections

Each paper must contain these top-level sections:

```markdown
# PAPER-0001 Title
## Abstract
## Hypothesis
## Prior Research
## References
## Implementation Plan
## Validation Plan
## Validation
## Agent Review
## Human Review
## Impact Score
```

Leave human-only checkboxes unchecked until a human explicitly approves them.

## Resources

- `assets/paper-template.md`: Base paper template.
- `assets/structure-template.md`: Project-local `.paper-stack/structure.md` template.
- `references/paper-states.md`: Detailed state and gate rules.
- `references/impact-scoring.md`: Evidence-based impact scoring.
- `scripts/init_loop_paper.py`: Initialize the generalizable `.paper-stack` structure.
- `scripts/new_closed_loop_paper.py`: Create a hypothesis-first paper.
- `scripts/check_closed_loop_paper.py`: Validate before/after closed-loop slots.
- `scripts/combine_papers.py`: Deterministically summarize intervals and rank references.
- `scripts/new_paper.py`: Create a basic paper with the next ID.
- `scripts/check_paper.py`: Validate required sections and gate integrity.
- `scripts/pipeline.py`: Run metadata sync, human-gate validation, graph index,
  impact scoring, dashboard render, and report export.
- `scripts/index_references.py`: Build `dashboard/references.json`.
- `scripts/score_impact.py`: Calculate deterministic impact components.
- `scripts/transition_paper.py`: Enforce allowed status transitions.
- `scripts/human_review.py`: Apply password-verified human review.
- `scripts/render_dashboard.py`: Build `dashboard/data.json` and dashboard HTML.
- `scripts/export_report.py`: Generate `dashboard/report.md`.
