---
name: loop-paper
description: Use when running substantial work as a hypothesis-first paper loop — initializing a project-local .paper-stack, creating or closing a closed-loop paper, validating before/after gates, combining paper intervals, or ranking reference papers.
---

# Loop Paper

Loop Paper treats meaningful work as a paper-backed loop: claim, prior work,
implementation plan, validation plan, evidence, verdict, review, and impact.

## Operating Model

The loop runs autonomously. Papers walk
`Draft -> Research Ready -> Plan Ready -> Implementing -> Implemented ->
AI Validated -> Accepted` without any human checkbox gate. The agent is
expected to keep producing papers indefinitely, one after the next.

**Review is itself a paper, not a checkbox.** When a target paper needs
review, write a *review paper* whose body assesses the targets via a
structured multiple-choice walk. The review paper sits in the same paper
stack and flows through the same loop. It does not block or modify the
target papers; it cites them.

Use `scripts/new_review_paper.py` to drive the review:

```bash
# Phase 1 — render the multiple-choice prompts for the host agent:
python3 scripts/new_review_paper.py \
  --root .paper-stack \
  --title "Quarter Review of PAPER-0010 and PAPER-0011" \
  --target PAPER-0010 --target PAPER-0011 \
  --format claude --prompt-out .paper-stack/inbox/prompts.json

# (Host agent presents the prompts to the user and writes answers.json)

# Phase 2 — generate the review paper from answers:
python3 scripts/new_review_paper.py \
  --root .paper-stack \
  --title "Quarter Review of PAPER-0010 and PAPER-0011" \
  --target PAPER-0010 --target PAPER-0011 \
  --answers .paper-stack/inbox/answers.json
```

`--format` selects the prompt rendering: `cli` (interactive stdin),
`json` (canonical), `claude` (AskUserQuestion-shape JSON), `codex` (codex
interactive block), `pi` (pi-mono YAML-style). Same questions in every
format. The per-target dimensions are: hypothesis verdict, evidence
strength, production readiness, recommended action. The cross-paper
dimensions are: coherence and recommended next direction.

## Purpose

The loop exists so a human can reconstruct the full path of the work by
reading only the `Abstract` sections of the papers, in numeric order. Every
abstract must:

- Stand alone (no jargon that requires reading the body).
- Name the work unit, the hypothesis, the verdict, and the next step.
- Read as the next sentence in the project's running narrative when placed
  after the previous paper's abstract.

When writing or updating an abstract, optimize for the reader who has not
read any other section of any paper. The abstract is the only deliverable
guaranteed to be read.

## Production Bar

A loop is "done" only when its work is production-level. The AI treats any
state below production — TODOs, untested code, mocks, partial validation,
unmeasured outcomes — as in-progress, regardless of how many checkboxes are
ticked. Acceptable terminal states are:

- The paper reaches `Accepted` with production-level evidence, and the loop
  is paused intentionally because no further production-impacting work
  remains for now.
- The paper reaches `Rejected` because the hypothesis failed.
- The paper is `Superseded` by a stronger one.

Do not pause a loop just because the immediate change runs locally. Keep
iterating until the change would survive being shipped.

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
  config/       local Loop Paper config
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
5. The loop runs autonomously through `Accepted`. There is no human-checkbox
   gate. If a paper needs human assessment, write a *review paper* with
   `scripts/new_review_paper.py` that cites the target via `References:`.
   Do not pause or stall waiting for a human on the target paper.
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

   The pipeline is also a gate: papers in `Plan Ready`, `Implementing`, or
   `Implemented` must pass `--phase before`; papers in `AI Validated` or
   `Accepted` must pass `--phase after`.

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

Selection is stable by numeric paper ID, and explicit `--from`/`--to`
interval boundaries plus every interior paper ID must exist in the stack. Use
`--ids` for intentional sparse selections. Summary chunks are stable by
`--interval-size`. Reference candidates are ranked without model judgment using
status, inbound graph references, explicit relationship edges, paper-ID
distance to the target, and deterministic text-term overlap.

Use:

- `--mode summary` for interval summaries only.
- `--mode references` for ranked reference candidates and relationship lines.
- `--mode both` when closing a set of papers and preparing a next paper.
- `--target-paper PAPER-NNNN` only when that target paper exists in the stack.
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
Accepted
Rejected
Superseded
```

Allowed progression:

```text
Draft -> Research Ready -> Plan Ready -> Implementing -> Implemented -> AI Validated -> Accepted
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
## Impact Score
```

## Resources

- `assets/structure-template.md`: Project-local `.paper-stack/structure.md` template.
- `references/paper-states.md`: Detailed state and gate rules.
- `references/impact-scoring.md`: Evidence-based impact scoring.
- `scripts/init_loop_paper.py`: Initialize the generalizable `.paper-stack` structure.
- `scripts/new_closed_loop_paper.py`: Create a hypothesis-first paper.
- `scripts/new_review_paper.py`: Create a review paper from structured multiple-choice answers across one or more target papers.
- `scripts/check_closed_loop_paper.py`: Validate before/after closed-loop slots.
- `scripts/check_paper.py`: Validate required sections.
- `scripts/combine_papers.py`: Deterministically summarize intervals and rank references.
- `scripts/pipeline.py`: Run metadata sync, graph index, impact scoring, phase gates, dashboard render, and report export.
- `scripts/index_references.py`: Build `dashboard/references.json`.
- `scripts/score_impact.py`: Calculate deterministic impact components.
- `scripts/transition_paper.py`: Enforce allowed status transitions.
- `scripts/update_paper_metadata.py`: Synchronize paper frontmatter with deterministic paper contents.
- `scripts/agent_review.py`: Record or refresh the `Agent Review` section on a paper.
- `scripts/render_dashboard.py`: Build `dashboard/data.json` and dashboard HTML.
- `scripts/export_report.py`: Generate `dashboard/report.md`.
- `scripts/watch_pipeline.py`: Poll papers and rerun the deterministic pipeline on changes.
- `scripts/paperstack_common.py`: Shared deterministic helpers for bundled scripts.
- `scripts/install_skill.py`: Install the portable skill payload into supported agent skill directories.
- `scripts/validate_skill_repo.py`: Validate the public skill repository contract.
- `scripts/smoke_test.py`: Run the end-to-end happy-path workflow smoke test.
- `scripts/edge_case_test.py`: Run deterministic rejection-path tests for review and combine CLIs.
