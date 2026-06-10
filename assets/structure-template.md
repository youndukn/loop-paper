# Loop Paper Structure

This directory is the project-local state for paper-backed work loops.

## Directories

- `papers/`: canonical paper files. One paper per work loop. File names use
  `PAPER-NNNN-short-title.md`.
- `runs/`: validation and experiment records. Use for command output, verifier
  results, benchmark snapshots, screenshots, and inspected artifacts.
- `fixes/`: implementation records. Use for change summaries, touched files,
  rollback notes, and links to validating run records.
- `references/`: stable prior work and source notes that are not themselves
  papers.
- `inbox/`: untriaged claims, user notes, external links, or experiment ideas
  before they become papers.
- `dashboard/`: generated outputs from `scripts/pipeline.py`. Do not hand-edit.
- `config/`: local Loop Paper configuration, reviewer registry, and policy.
- `archive/`: superseded or exported paper-stack material kept for history.

## File Contracts

Papers own claims and verdicts. They should stay concise and link to runs,
fixes, and references instead of embedding long logs.

Run records own evidence. A run record should include:

- date
- related paper ID
- command or inspection performed
- exact artifact paths
- result
- follow-up needed

Fix records own implementation details. A fix record should include:

- date
- related paper ID
- files or modules changed
- reason for the change
- rollback notes
- validating run records

Generated dashboard files are disposable. Regenerate them from papers instead
of editing them manually.

## Relationship Lines

Use explicit `None` instead of blank relationship labels:

```text
References: None
Depends on: None
Supersedes: None
Contradicts: None
Extends: None
```

## Closeout

Before closing a work loop, run:

```bash
python3 /path/to/loop-paper/scripts/check_closed_loop_paper.py \
  .paper-stack/papers/PAPER-NNNN-title.md \
  --phase after

python3 /path/to/loop-paper/scripts/pipeline.py .paper-stack
```
