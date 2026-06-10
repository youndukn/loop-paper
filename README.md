# Loop Paper

Loop Paper is a Codex skill for running work as paper-backed loops: hypothesis,
prior work, implementation plan, validation plan, evidence, verdict, review,
and impact.

The skill is intentionally deterministic where drift would hurt: it includes
scripts for initializing a `.paper-stack`, checking paper gates, generating
dashboards, indexing references, scoring deterministic impact components, and
combining paper intervals.

## Install

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

## Quick Start

From any project repository, initialize the project-local paper structure:

```bash
python3 ~/.codex/skills/loop-paper/scripts/init_loop_paper.py \
  --root .paper-stack \
  --project-name "My Project" \
  --seed-paper
```

Create a new closed-loop paper before substantial work:

```bash
python3 ~/.codex/skills/loop-paper/scripts/new_closed_loop_paper.py \
  --root .paper-stack \
  --title "Short Work Unit Title" \
  --hypothesis "This change will produce a measurable effect" \
  --finding "Prior finding or reason this is worth doing" \
  --reference "docs/current_findings.md"
```

Check the before phase:

```bash
python3 ~/.codex/skills/loop-paper/scripts/check_closed_loop_paper.py \
  .paper-stack/papers/PAPER-0001-short-work-unit-title.md \
  --phase before
```

After implementation and validation, check the after phase and regenerate the
dashboard:

```bash
python3 ~/.codex/skills/loop-paper/scripts/check_closed_loop_paper.py \
  .paper-stack/papers/PAPER-0001-short-work-unit-title.md \
  --phase after

python3 ~/.codex/skills/loop-paper/scripts/pipeline.py .paper-stack
```

## Review Papers

Reviews are themselves papers. `new_review_paper.py` walks the user (or the
host agent) through structured multiple-choice prompts for each target
paper, then writes a review paper that cites the targets via `References:`.

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

Per-target dimensions: hypothesis verdict, evidence strength, production
readiness, recommended action. Cross-paper dimensions: coherence and next
direction. The generated paper conforms to the closed-loop schema and
passes `check_closed_loop_paper.py --phase after` out of the box. Phase-1
prompts include `answer_id` values; phase 2 expects `answers.json` to map
those IDs to selected option labels.

## Combine Papers

Use `combine_papers.py` to close or summarize an interval and generate ranked
reference candidates for the next paper:

```bash
python3 ~/.codex/skills/loop-paper/scripts/combine_papers.py .paper-stack \
  --from PAPER-0030 \
  --to PAPER-0045 \
  --interval-size 5 \
  --mode both \
  --target-paper PAPER-0046 \
  --output .paper-stack/dashboard/combined-PAPER-0030-PAPER-0045.md
```

Selection is stable by numeric paper ID. Reference ranking is deterministic and
uses status, inbound references, explicit relation edges, target-paper distance,
and term overlap.

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

It checks the required skill files, resource references, CI coverage, retired
workflow references, `agents/openai.yaml`, nested `SKILL.md` files, and Python
syntax. The smoke test exercises initialization, closed-loop paper transitions,
review-paper generation, prompt formats, combining, and the dashboard/report
pipeline. The edge-case test exercises rejection paths for invalid review
inputs and ambiguous combine selections.

## Public Repo Notes

This is a single-skill repository, so the skill lives at the repository root.
Multi-skill repositories often use a flat `skills/<skill-name>/` layout; for a
single skill, the root layout keeps installation simple while preserving the
standard skill anatomy: `SKILL.md`, optional `agents/`, `scripts/`,
`references/`, and `assets/`.
