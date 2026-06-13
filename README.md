# Loop Paper

Loop Paper runs work as paper-backed loops: hypothesis, evidence, verdict.
The paper stack is the source of truth — no change without a paper, every
claim carries evidence (including proof of failure), and papers read in
numeric order reconstruct the path. Theme: concise, verifiable points,
direct wording. Everything that would drift is a deterministic script.

## Install

Requires Python 3.10+.

One-command install:

```bash
npx skills add youndukn/loop-paper
```

Clone the repository:

```bash
git clone https://github.com/youndukn/loop-paper.git
cd loop-paper
```

Use the installer for common agents:

```bash
python3 scripts/install_skill.py --agent codex
python3 scripts/install_skill.py --agent claude
python3 scripts/install_skill.py --agent hermes
python3 scripts/install_skill.py --agent pi
```

Install everywhere the script knows about:

```bash
python3 scripts/install_skill.py --agent all
```

Supported targets include OpenAI Codex, Claude Code, Hermes Agent, pi-mono,
OpenClaw, and generic Agent Skills directories. See
[docs/install.md](docs/install.md) for user/project paths, dry-run usage,
manual clone commands, and custom destinations.

## Drive It With Goals

The name stays loop-paper — "loop" is the word everyone uses — but drive it
with a goal, not a timer. In Claude or Codex: `/goal make this into
production level` (Claude Code without `/goal`: `/loop make this into
production level`, no interval). The loop stops on `Accepted`, `Rejected`,
or `Superseded` — not on a clock.

## Quick Start

From any project repository, initialize the project-local paper structure:

```bash
python3 ~/.codex/skills/loop-paper/scripts/init_loop_paper.py \
  --root .paper-stack \
  --project-name "My Project" \
  --seed-paper
```

`--seed-paper` creates `PAPER-0001` only when the stack has no papers yet. It
is safe to rerun the initializer; existing stacks report
`"seed_paper_skipped": true` instead of creating duplicate seed papers.
By default, init also installs a cooperative Claude Code PreToolUse hook in
`.claude/settings.json`; use `--no-claude-hook` to skip it. The hook blocks
Write/Edit/MultiEdit, NotebookEdit, and obvious Bash writes while no paper is
open. It is a workflow guardrail, not a security sandbox.

Research first, capture the baseline, then propose. The human's selection is
the loop's source of truth. At least one `--finding` is required:

```bash
# Phase 1 — render multiple-choice prompts (cli|json|claude|codex|pi):
python3 ~/.codex/skills/loop-paper/scripts/propose_paper.py \
  --root .paper-stack \
  --title "Short Work Unit Title" \
  --candidate-abstract "Framing A ..." \
  --candidate-abstract "Framing B ..." \
  --candidate-set "Claim one||Claim two" \
  --candidate-set "Alt claim one||Alt claim two" \
  --finding "Research result and baseline this proposal is grounded in" \
  --format claude --prompt-out .paper-stack/inbox/proposal-prompts.json

# Phase 2 — create the paper from the selection (same arguments plus):
#   --answers .paper-stack/inbox/proposal-answers.json
```

The selection is persisted in `proposals/`; the checker rejects drift.
`More abstraction` exits 2 and requests a new round.
Proposal records are local workflow artifacts: the checker validates that the
paper matches the selected abstract, hypotheses, title, and paper ID, but this
is not cryptographic proof of human origin in an agent-writable repository.
An answers JSON file can be keyed by question id:

```json
{
  "abstract": "Framing A ...",
  "hypothesis_set": "Claim one | Claim two",
  "gate": "Implement now"
}
```

Direct creation is only for stacks whose proposal gate allows it, or when the
human stated the hypothesis verbatim before a gate applies. Fresh initialized
stacks gate from `PAPER-0001`, so use `propose_paper.py` there.

```bash
python3 ~/.codex/skills/loop-paper/scripts/new_closed_loop_paper.py \
  --root .paper-stack \
  --title "Short Work Unit Title" \
  --hypothesis "This change will produce a measurable effect" \
  --finding "Prior finding or reason this is worth doing" \
  --reference "docs/current_findings.md"
```

If `--reference` contains existing `PAPER-NNNN` IDs, the creator mirrors them
into the deterministic `References:` relationship line and rejects unknown IDs.

Check the before phase:

```bash
python3 ~/.codex/skills/loop-paper/scripts/check_closed_loop_paper.py \
  .paper-stack/papers/PAPER-0002-short-work-unit-title.html \
  --phase before
```

Move through the before-gated states before implementation:

```bash
python3 ~/.codex/skills/loop-paper/scripts/transition_paper.py \
  .paper-stack/papers/PAPER-0002-short-work-unit-title.html "Research Ready"
python3 ~/.codex/skills/loop-paper/scripts/transition_paper.py \
  .paper-stack/papers/PAPER-0002-short-work-unit-title.html "Plan Ready"
python3 ~/.codex/skills/loop-paper/scripts/transition_paper.py \
  .paper-stack/papers/PAPER-0002-short-work-unit-title.html Implementing
```

Evidence comes from `execute_run.py`. The run record stores command, exit
code, output, and a self-consistency digest over those fields. This detects accidental
tampering; it is not a signature or proof of independent execution:

```bash
python3 ~/.codex/skills/loop-paper/scripts/execute_run.py \
  --root .paper-stack \
  --paper PAPER-0002 \
  --label suites \
  -- python3 -m pytest
```

After validation, add `## Validation` verdict bullets with the exact prefix
format `- Supported: ...`, `- Failed: ...`, `- Inconclusive: ...`, or
`- Superseded: ...`, and list cited files in `## Execution Records`.

Then check the after phase, run the pipeline gate, and open the dashboard at
the new paper — every paper write ends on its page:

```bash
python3 ~/.codex/skills/loop-paper/scripts/check_closed_loop_paper.py \
  .paper-stack/papers/PAPER-0002-short-work-unit-title.html \
  --phase after

python3 ~/.codex/skills/loop-paper/scripts/pipeline.py .paper-stack --open PAPER-0002
```

If the after gate passes, close through the positive states:

```bash
python3 ~/.codex/skills/loop-paper/scripts/transition_paper.py \
  .paper-stack/papers/PAPER-0002-short-work-unit-title.html Implemented
python3 ~/.codex/skills/loop-paper/scripts/transition_paper.py \
  .paper-stack/papers/PAPER-0002-short-work-unit-title.html "AI Validated"
python3 ~/.codex/skills/loop-paper/scripts/transition_paper.py \
  .paper-stack/papers/PAPER-0002-short-work-unit-title.html Accepted
```

The pipeline rejects advanced-status papers that do not satisfy their phase
gates: `Plan Ready` through `Implemented` require the before gate, and
`AI Validated`/`Accepted` require the after gate. `Draft`/`Research Ready`
papers are checked structurally (including proposal drift), `Rejected` papers
must record proof of the failure, and `Superseded` papers must be superseded
by an actual paper that declares `Supersedes:` them.

## Review Papers

Reviews are papers. `new_review_paper.py` renders multiple-choice prompts
per target, then writes a review paper citing the targets via `References:`.

```bash
# Phase 1 — render prompts for the host agent (cli|json|claude|codex|pi):
python3 ~/.codex/skills/loop-paper/scripts/new_review_paper.py \
  --root .paper-stack \
  --title "Review of PAPER-0010 and PAPER-0011" \
  --target PAPER-0010 --target PAPER-0011 \
  --format claude --prompt-out .paper-stack/inbox/prompts.json

# Phase 2 — generate the paper from collected answers:
python3 ~/.codex/skills/loop-paper/scripts/new_review_paper.py \
  --root .paper-stack \
  --title "Review of PAPER-0010 and PAPER-0011" \
  --target PAPER-0010 --target PAPER-0011 \
  --answers .paper-stack/inbox/answers.json
```

Dimensions per target: verdict, evidence strength, production readiness,
action; cross-paper: coherence, direction. The generated paper passes
`check_closed_loop_paper.py --phase after` out of the box. Phase-2
`answers.json` maps `answer_id` values to option labels.

## Combine Papers

Close or summarize an interval and rank references for the next paper:

```bash
python3 ~/.codex/skills/loop-paper/scripts/combine_papers.py .paper-stack \
  --from PAPER-0030 \
  --to PAPER-0045 \
  --interval-size 5 \
  --mode both \
  --target-paper PAPER-0046 \
  --output .paper-stack/dashboard/combined-PAPER-0030-PAPER-0045.md
```

Selection is stable by numeric paper ID. Explicit `--from`/`--to` boundaries
and every interior paper ID must exist in the stack, so a mistyped or missing
paper cannot silently produce a partial interval. Use `--ids` for intentional
sparse selections. Reference ranking is deterministic and uses status, inbound
references, explicit relation edges, target-paper distance, and term overlap.
When `--target-paper` is supplied, that paper must exist in the stack.

## Repository Structure

```text
loop-paper/
├── README.md                  # public repository guide
├── SKILL.md                   # loadable skill instructions
├── agents/
│   └── openai.yaml            # Codex UI metadata
├── assets/
│   └── structure-template.md  # .paper-stack/structure.md template
├── docs/
│   └── install.md             # multi-agent installation guide
├── references/
│   ├── impact-scoring.md
│   └── paper-states.md
└── scripts/
    ├── install_skill.py
    ├── init_loop_paper.py
    ├── new_closed_loop_paper.py
    ├── check_closed_loop_paper.py
    ├── combine_papers.py
    ├── pipeline.py
    └── ...
```

The project-local structure created by `init_loop_paper.py` is:

```text
.paper-stack/
  papers/       canonical paper loops
  proposals/    human-selected abstract/hypothesis records
  runs/         validation evidence and command results
  fixes/        implementation change records
  references/   source notes and prior work
  inbox/        untriaged ideas or claims
  dashboard/    generated reports
  config/       local config
  archive/      old or superseded material
```

Papers own claims and verdicts. `runs/` owns evidence. `fixes/` owns
implementation details. `dashboard/` is generated and should not be hand-edited.

## Validate This Repo

Run the repository validator before publishing changes:

```bash
python3 scripts/validate_skill_repo.py
python3 scripts/smoke_test.py
python3 scripts/edge_case_test.py
```

The validator checks skill files, resource references, CI coverage, and
Python syntax. The smoke test runs the happy path end to end; the edge-case
test runs the rejection paths (proposal, review, attestation, transitions,
pipeline gates, combine, installer).

## Public Repo Notes

This is a single-skill repository, so the skill lives at the repository root.
Multi-skill repositories often use a flat `skills/<skill-name>/` layout; for a
single skill, the root layout keeps installation simple while preserving the
standard skill anatomy: `SKILL.md`, optional `agents/`, `scripts/`,
`references/`, and `assets/`.
