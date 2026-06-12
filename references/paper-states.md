# Paper States

Use these states to keep work paper-first instead of todo-first.

## Draft

The paper exists but required sections may be incomplete. Papers enter via
the proposal gate (`scripts/propose_paper.py`), which records the
human-selected abstract and hypotheses in `proposals/`. From `Draft` onward
every check phase rejects drift: the chosen abstract stays the unchanged
prefix and the chosen claims are not edited.

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
- For schema v3 papers, every after-evidence bullet cites a run record written
  by `scripts/execute_run.py`; the checker verifies the attestation marker and
  output digest, so hand-authored or tampered evidence fails.
- Every Hypothesis Ledger row has a final verdict: `Supported`, `Failed`,
  `Inconclusive`, or `Superseded`.
- The Abstract states the hypothesis verdict and next step, appended after
  the human-selected framing when the paper has a proposal record.
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

The hypothesis failed, evidence was insufficient, or a human rejected the
paper. Failure needs proof exactly like success.

Entry criteria (`check_closed_loop_paper.py --phase rejected`, enforced by
`transition_paper.py` and the pipeline):

- Every Hypothesis Ledger row has a resolved verdict (no `Open`).
- Validation records a `Failed`, `Inconclusive`, or `Superseded` verdict with
  its evidence reason, and the Before/After evidence blocks are filled with
  no remaining placeholders.

## Superseded

Another paper replaces this one.

Entry criteria (enforced by `transition_paper.py` and the pipeline):

- At least one other paper in the stack declares `Supersedes:` this paper's
  ID, so the replacement is itself a paper, not an assertion.
