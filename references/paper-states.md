# Paper States

Use these states to keep work paper-first instead of todo-first.

## Draft

The paper exists but required sections may be incomplete.

Exit criteria:

- Hypothesis exists.
- Abstract exists.

## Research Ready

The paper has enough prior work to justify planning, or explicitly states that prior research is missing and risk is high.

Exit criteria:

- Prior Research is filled.
- References are filled or absence is explicitly acknowledged.

## Plan Ready

Implementation and validation plans are concrete enough to execute.

Exit criteria:

- Implementation Plan names likely changes.
- Validation Plan names the AI-actionable evidence the paper will collect.
- `check_closed_loop_paper.py --phase before` passes before advancing to this
  state or later implementation states.

## Implementing

Work is actively being changed.

Exit criteria:

- Implementation is complete enough to validate.

## Implemented

The implementation exists, but validation has not yet completed.

Exit criteria:

- AI-actionable validation has been attempted or explicitly marked not applicable.

## AI Validated

Agent-actionable checks passed and evidence is recorded.

Exit criteria:

- Validation section contains command output summaries, file links, screenshots, metrics, or inspection notes.
- Every Hypothesis Ledger row has a final verdict: `Supported`, `Failed`,
  `Inconclusive`, or `Superseded`.
- `check_closed_loop_paper.py --phase after` passes before advancing to this
  state or `Accepted`.

## Accepted

The paper is complete.

Exit criteria:

- AI validation evidence is recorded.
- Impact score has an evidence basis where measurable.
- `pipeline.py` passes, including the closed-loop phase gate for the paper's
  current status.

If a human needs to review the paper, write a separate review paper with
`scripts/new_review_paper.py` that cites it via `References:`. The target
paper itself stays on the autonomous loop.

## Rejected

The hypothesis failed, evidence was insufficient, or a human rejected the paper.

## Superseded

Another paper replaces this one.
