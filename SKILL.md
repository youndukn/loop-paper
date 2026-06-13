---
name: loop-paper
description: Use when changing a codebase or company structure that runs on hypothesis-first paper loops — initializing a project-local .paper-stack, proposing abstract/hypothesis candidates for human selection, creating or closing a closed-loop paper, validating phase gates, combining paper intervals, or ranking reference papers.
---

# Loop Paper

Work runs as paper-backed loops: claim, prior work, plan, evidence, verdict,
review, impact.

The contract: no change to the codebase — or the company structure it
defines — without a paper. Every claim carries evidence, including proof of
failure. Papers read in numeric order reconstruct the path.

A paper is one self-rendering HTML file (`papers/PAPER-NNNN-title.html`):
the canonical, gate-checked markdown source lives in its `paper-source`
block; the file renders it as HTML with tables, checkboxes, and diff
highlighting, and fenced ```html blocks render live — add interactivity when
it explains better. Rendered checkboxes are clickable; the human's review
state persists in the browser without touching the canonical source. `scripts/convert_papers.py` migrates markdown stacks.

## Operating Model

The human chooses the abstract and hypotheses; that selection is the source
of truth. One blocking human gate, at proposal time:

1. Research first: inspect the code and the paper stack; capture the
   measurable baseline.
2. Draft candidate abstracts and hypothesis sets, each derived from a
   recorded finding.
3. `scripts/propose_paper.py` renders the multiple-choice prompts. No
   `--finding`, no proposal.
4. The human picks one abstract, one hypothesis set, and `Implement now` or
   `More abstraction` (new candidate round).
5. `Implement now` creates the paper and persists the selection in
   `proposals/`. The checker rejects later drift.

The gate is enforced by scripts, not by convention. Stack config declares
`proposal_gate.required_from` (init defaults to `PAPER-0001`; `PAPER-0002`
with `--seed-paper`): from that id on, `new_closed_loop_paper.py` refuses
direct creation and the checker fails any closed-loop paper without a valid
proposal record — so always create papers through `propose_paper.py`. Init
also installs a cooperative Claude Code PreToolUse hook
(`<stack>/hooks/guard_paper_loop.py`, registered in the project's
`.claude/settings.json`, opt out with `--no-claude-hook`) that blocks file
edits while no paper is in an open status. It covers Write/Edit/MultiEdit,
NotebookEdit, and obvious Bash writes, but it is not a security sandbox. If
the hook blocks you, do not work around it: research findings, then run
`propose_paper.py`.

Proposal records are local workflow artifacts. The checker validates that a
paper matches its selected abstract, hypotheses, title, and paper ID; it does
not cryptographically prove human origin in an agent-writable repository.

After selection the loop is autonomous:
`Draft -> Research Ready -> Plan Ready -> Implementing -> Implemented ->
AI Validated -> Accepted`.

Review is a paper, not a checkbox: `scripts/new_review_paper.py` renders
per-target prompts (verdict, evidence strength, production readiness,
action) and cross-paper prompts (coherence, direction), then writes a review
paper citing the targets. It never blocks or modifies them.

Proposal and review prompts share `--format cli|json|claude|codex|pi`
(`claude` is AskUserQuestion-shaped JSON) and the `--prompt-out` /
`--answers` two-phase flow. Answers JSON can be an object keyed by question
id, or a list of `{ "id": "...", "answer": "..." }` objects; values must
match option labels exactly.

## Abstract Contract

The path is read through abstracts alone. Each abstract stands alone and
names the work unit, hypothesis, verdict, and next step. A human-selected
abstract is an immutable prefix: append the verdict, never rewrite it. The
after gate enforces both.

## Production Bar

Done means production-level. TODOs, mocks, partial validation, and
unmeasured outcomes are in-progress regardless of checkboxes. Iterate until
the change would survive shipping; close only through the gated terminal
states in Paper States.

Default root: `.paper-stack/`. Resolve scripts relative to this `SKILL.md`
and run them with absolute paths outside the skill directory.

## Initialize A Project

```bash
python3 scripts/init_loop_paper.py \
  --root .paper-stack \
  --project-name "Project Name"
```

```text
.paper-stack/
  papers/       canonical paper loops
  proposals/    human-selected abstract/hypothesis records
  runs/         attested run records and inspection evidence
  fixes/        implementation change records and rollback notes
  references/   stable prior work and source notes
  inbox/        untriaged claims, links, and ideas
  dashboard/    generated reports; do not hand-edit
  config/       local Loop Paper config
  archive/      superseded or exported material
```

`--seed-paper` creates the first closed-loop paper during initialization.

## Core Rules

1. Every change flows through a paper. New papers go through the proposal
   gate; direct creation with `new_closed_loop_paper.py` only when the human
   stated the hypothesis verbatim.
2. Record hypothesis, baseline evidence, TODOs, validation plan, and
   references before changing anything.
3. `Validation Plan` says what would count; `Validation` records what
   happened. Never merge them.
4. Mark AI-actionable validation only after executing or inspecting
   evidence.
5. Metadata, graph edges, dashboards, impact, reports, transitions, and
   summaries: deterministic scripts only.
6. Work done before the paper existed is retrospective evidence. Never
   backdate a hypothesis.
7. Concise, verifiable, direct — in papers and implementation. Every claim,
   bullet, and code change earns its place. Link to runs and fixes; never
   embed logs. Smallest implementation that proves the hypothesis. The
   after-bloat cap enforces this on evidence.

## Main Workflow

1. Research, capture the baseline, record findings as `--finding`
   (required), then let the human select:

   ```bash
   # Phase 1 — render the multiple-choice prompts for the host agent:
   python3 scripts/propose_paper.py \
     --root .paper-stack \
     --title "Short Work Unit Title" \
     --candidate-abstract "Framing A ..." \
     --candidate-abstract "Framing B ..." \
     --candidate-set "Claim one||Claim two" \
     --candidate-set "Alt claim one||Alt claim two" \
     --finding "Research result and baseline behind these candidates" \
     --reference "docs/current_findings.md" \
     --format claude --prompt-out .paper-stack/inbox/proposal-prompts.json

   # Phase 2 — create the paper from the selection (same arguments plus):
   #   --answers .paper-stack/inbox/proposal-answers.json
   ```

   Example answers file:

   ```json
   {
     "abstract": "Framing A ...",
     "hypothesis_set": "Claim one | Claim two",
     "gate": "Implement now"
   }
   ```

   `More abstraction` prints `reproposal_requested` and exits 2: draft a new
   round. `Implement now` writes the proposal record and the paper.
   `PAPER-NNNN` IDs in `--reference` become the `References:` line; unknown
   IDs are rejected.

2. Fill all `BEFORE_REQUIRED` slots, then:

   ```bash
   python3 scripts/check_closed_loop_paper.py \
     .paper-stack/papers/PAPER-XXXX-title.html \
     --phase before
   ```

3. Move through the before-gated states, then implement only the active
   hypothesis:

   ```bash
   python3 scripts/transition_paper.py \
     .paper-stack/papers/PAPER-XXXX-title.html "Research Ready"
   python3 scripts/transition_paper.py \
     .paper-stack/papers/PAPER-XXXX-title.html "Plan Ready"
   python3 scripts/transition_paper.py \
     .paper-stack/papers/PAPER-XXXX-title.html Implementing
   ```

4. Evidence comes from `execute_run.py`, which runs the command and writes a
   record containing command, exit code, output, and a local self-consistency
   digest. This detects accidental tampering, but it is not a signature and
   does not prove independent execution. v3 papers reject after-evidence
   without a cited run record:

   ```bash
   python3 scripts/execute_run.py \
     --root .paper-stack \
     --paper PAPER-XXXX \
     --label suites \
     -- python3 -m pytest
   ```

   In `## Validation`, verdict bullets must use this exact shape:

   ```markdown
   - Supported: evidence reason with a RUN-* citation
   - Failed: evidence reason with a RUN-* citation
   - Inconclusive: evidence reason with a RUN-* citation
   - Superseded: evidence reason with a RUN-* citation
   ```

   Record run/fix records in `## Execution Records`, plus reference edges:

   ```text
   References: PAPER-0001
   Depends on: PAPER-0002
   Supersedes: None
   Contradicts: None
   Extends: PAPER-0003
   ```

5. Append the verdict and next step to the abstract, then check, gate, and
   open the dashboard at the paper you just wrote — every paper write ends
   with the human-readable page:

   ```bash
   python3 scripts/check_closed_loop_paper.py \
     .paper-stack/papers/PAPER-XXXX-title.html \
     --phase after

   python3 scripts/pipeline.py .paper-stack --open PAPER-XXXX
   ```

   If the after gate passes, close through the positive states:

   ```bash
   python3 scripts/transition_paper.py \
     .paper-stack/papers/PAPER-XXXX-title.html Implemented
   python3 scripts/transition_paper.py \
     .paper-stack/papers/PAPER-XXXX-title.html "AI Validated"
   python3 scripts/transition_paper.py \
     .paper-stack/papers/PAPER-XXXX-title.html Accepted
   ```

   The pipeline enforces the phase gates on every run: papers in `Draft` or
   `Research Ready` must pass `--phase structural` (base structure and
   proposal drift); papers in `Plan Ready`, `Implementing`, or `Implemented`
   must pass `--phase before`; papers in `AI Validated` or `Accepted` must
   pass `--phase after`; `Rejected` papers must pass `--phase rejected`; and
   `Superseded` papers must have another paper declaring `Supersedes:` them.

6. Interaction review: papers with live ```html blocks block the next
   paper's creation until the human was asked. Open the page
   (`pipeline.py --open PAPER-NNNN`), ask, record the answer with
   `scripts/ack_interaction.py --paper PAPER-NNNN --status reviewed|waived`.

## Deterministic Combine

Close intervals, summarize, and rank references with
`scripts/combine_papers.py`:

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
`--interval-size`. Reference ranking is deterministic: status, inbound
references, relationship edges, ID distance, term overlap.

- `--mode summary`: interval summaries only.
- `--mode references`: ranked reference candidates and relationship lines.
- `--mode both`: close a set and prepare the next paper.
- `--target-paper PAPER-NNNN`: only when that paper exists in the stack.
- `--last N`: only for a recent deterministic suffix.
- `--ids PAPER-0001 PAPER-0007`: only when the user names exact papers.

## Paper States

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

Progression:

```text
Draft -> Research Ready -> Plan Ready -> Implementing -> Implemented -> AI Validated -> Accepted
```

Failure needs proof exactly like success: `Rejected` requires the
`--phase rejected` gate (resolved ledger verdicts plus a
Failed/Inconclusive/Superseded verdict with its evidence reason);
`Superseded` requires another paper declaring `Supersedes:` it.

## Required Sections

```markdown
# PAPER-0001 Title
## Abstract
## Hypothesis
## Prior Research
## References
## Implementation Plan
## Validation Plan
## Execution Records
## Validation
## Agent Review
## Impact Score
```

## Resources

- `assets/structure-template.md`: Project-local `.paper-stack/structure.md` template.
- `references/paper-states.md`: Detailed state and gate rules.
- `references/impact-scoring.md`: Evidence-based impact scoring.
- `scripts/init_loop_paper.py`: Initialize the `.paper-stack` structure.
- `scripts/propose_paper.py`: Render researched candidates for human selection and create the chosen paper.
- `scripts/new_closed_loop_paper.py`: Create a hypothesis-first paper.
- `scripts/convert_papers.py`: Convert markdown papers to HTML containers (lossless, verified roundtrip).
- `scripts/ack_interaction.py`: Record the human's interaction-review decision on an interactive paper.
- `scripts/execute_run.py`: Execute a validation command and write a run record (command, exit code, output, self-consistency digest).
- `scripts/new_review_paper.py`: Create a review paper from structured multiple-choice answers.
- `scripts/prompt_common.py`: Shared prompt rendering and answer loading.
- `scripts/paper_html.py`: HTML paper container — canonical markdown source embedded in a self-rendering interactive HTML file.
- `scripts/check_closed_loop_paper.py`: Validate phase gates, proposal drift, and attestation.
- `scripts/check_paper.py`: Validate required structure.
- `scripts/combine_papers.py`: Summarize intervals and rank references.
- `scripts/pipeline.py`: Metadata sync, graph index, impact scoring, phase gates, dashboard, report.
- `scripts/index_references.py`: Build `dashboard/references.json`.
- `scripts/score_impact.py`: Deterministic impact components.
- `scripts/transition_paper.py`: Enforce status transitions.
- `scripts/update_paper_metadata.py`: Sync frontmatter with paper contents.
- `scripts/agent_review.py`: Record the `Agent Review` section.
- `scripts/render_dashboard.py`: Build dashboard data and HTML.
- `scripts/export_report.py`: Generate `dashboard/report.md`.
- `scripts/watch_pipeline.py`: Rerun the pipeline on paper changes.
- `scripts/paperstack_common.py`: Shared deterministic helpers.
- `scripts/install_skill.py`: Install the skill into agent skill directories.
- `scripts/validate_skill_repo.py`: Validate the repository contract.
- `scripts/smoke_test.py`: End-to-end happy-path test.
- `scripts/edge_case_test.py`: Rejection-path tests for proposal, review, attestation, and combine.
