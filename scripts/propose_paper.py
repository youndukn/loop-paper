#!/usr/bin/env python3
"""Propose a closed-loop paper via multiple-choice human selection.

Phase 1 renders prompts for an Abstract framing, a Hypothesis set, and an
'Implement now / More abstraction' gate (same formats as new_review_paper.py).
Phase 2 (--answers) either creates the paper with the chosen abstract and
hypotheses — persisting the selection as a proposal record the checker
enforces — or emits a reproposal_requested payload and exits with status 2.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from new_closed_loop_paper import create_paper
from paperstack_common import next_paper_id, paper_id_lock, paper_paths, validate_iso_date, validate_title
from prompt_common import RENDERERS, collect_cli, load_answers, render_prompts


HYPOTHESIS_SEPARATOR = "||"
GATE_OPTIONS = ["Implement now", "More abstraction"]
REPROPOSAL_EXIT_CODE = 2
PROPOSAL_SCHEMA = "loop_paper.proposal.v1"


def clean_strings(values: list[str]) -> list[str]:
    return [item.strip() for item in values if item and item.strip()]


def parse_hypothesis_set(raw: str) -> list[str]:
    return [piece.strip() for piece in raw.split(HYPOTHESIS_SEPARATOR) if piece.strip()]


def set_label(items: list[str]) -> str:
    return " | ".join(items)


def validate_candidates(abstracts: list[str], sets: list[list[str]]) -> None:
    if len(abstracts) < 2:
        raise SystemExit("Need at least 2 --candidate-abstract values")
    if len(set(abstracts)) != len(abstracts):
        raise SystemExit("--candidate-abstract values must be unique")
    if len(sets) < 2:
        raise SystemExit("Need at least 2 --candidate-set values")
    short = [index + 1 for index, items in enumerate(sets) if len(items) < 2]
    if short:
        raise SystemExit(
            "Each --candidate-set must have >= 2 hypotheses (separated by "
            f"'{HYPOTHESIS_SEPARATOR}'); sets {short} are short"
        )
    labels = [set_label(items) for items in sets]
    if len(set(labels)) != len(labels):
        raise SystemExit("--candidate-set values must render unique option labels")


def build_questions(abstracts: list[str], sets: list[list[str]]) -> list[dict]:
    return [
        {
            "id": "abstract",
            "field": "abstract",
            "header": "Abstract",
            "prompt": "Pick an Abstract framing",
            "options": list(abstracts),
        },
        {
            "id": "hypothesis_set",
            "field": "hypothesis_set",
            "header": "Hypotheses",
            "prompt": "Pick a Hypothesis set",
            "options": [set_label(items) for items in sets],
        },
        {
            "id": "gate",
            "field": "gate",
            "header": "Gate",
            "prompt": "Implement now, or request another round of candidates?",
            "options": list(GATE_OPTIONS),
        },
    ]


def collect_cli_with_note(questions: list[dict]) -> dict:
    answers = collect_cli(questions)
    if answers.get("gate") == "More abstraction":
        note = input("Note for the next round (optional, ENTER to skip): ").strip()
        if note:
            answers["note"] = note
    return answers


def write_proposal_record(
    *,
    root: Path,
    paper_id: str,
    title: str,
    paper_date: str,
    abstracts: list[str],
    sets: list[list[str]],
    answers: dict,
    chosen_set: list[str],
) -> str:
    relative = f"proposals/PROPOSAL-{paper_id}.json"
    path = root / relative
    payload = {
        "schema": PROPOSAL_SCHEMA,
        "paper_id": paper_id,
        "title": title,
        "date": paper_date,
        "candidates": {"abstracts": abstracts, "hypothesis_sets": sets},
        "chosen": {"abstract": answers["abstract"], "hypotheses": chosen_set},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, indent=2) + "\n")
    except FileExistsError as error:
        raise SystemExit(f"Refusing to overwrite existing proposal record: {path}") from error
    return relative


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Propose a closed-loop paper via multiple-choice human selection."
    )
    parser.add_argument("--root", type=Path, default=Path(".paper-stack"))
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--candidate-abstract",
        action="append",
        default=[],
        help="Candidate Abstract framing. Repeat at least 2 times.",
    )
    parser.add_argument(
        "--candidate-set",
        action="append",
        default=[],
        help=(
            "Candidate hypothesis set. Hypotheses separated by "
            f"'{HYPOTHESIS_SEPARATOR}'. Repeat at least 2 times, each with >= 2 hypotheses."
        ),
    )
    parser.add_argument("--finding", action="append", default=[])
    parser.add_argument("--reference", action="append", default=[])
    parser.add_argument("--format", choices=list(RENDERERS), default="cli")
    parser.add_argument(
        "--prompt-out",
        type=Path,
        help="Write phase-1 prompts here (default stdout). Ignored when --answers is set.",
    )
    parser.add_argument(
        "--answers",
        type=Path,
        help="JSON file with answers. Skip phase 1 and either create the paper or request reproposal.",
    )
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    args.date = validate_iso_date(args.date)

    title = validate_title(args.title)
    paper_paths(args.root)
    abstracts = clean_strings(args.candidate_abstract)
    sets = [parse_hypothesis_set(value) for value in args.candidate_set]
    sets = [items for items in sets if items]
    validate_candidates(abstracts, sets)
    findings = clean_strings(args.finding)
    if not findings:
        raise SystemExit(
            "Need at least 1 --finding: research what should change and capture "
            "the baseline before proposing candidates"
        )
    questions = build_questions(abstracts, sets)

    if args.answers is None and args.format != "cli":
        prompt_text = render_prompts(questions, args.format, kind="proposal")
        if args.prompt_out:
            args.prompt_out.parent.mkdir(parents=True, exist_ok=True)
            args.prompt_out.write_text(prompt_text, encoding="utf-8")
            print(args.prompt_out)
        else:
            sys.stdout.write(prompt_text)
        return 0

    if args.answers is not None:
        answers = load_answers(args.answers, questions, extra_keys=("note",))
    else:
        answers = collect_cli_with_note(questions)

    if answers["gate"] == "More abstraction":
        payload = {"action": "reproposal_requested"}
        if answers.get("note"):
            payload["note"] = answers["note"]
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        return REPROPOSAL_EXIT_CODE

    set_labels = [set_label(items) for items in sets]
    chosen_set = sets[set_labels.index(answers["hypothesis_set"])]
    with paper_id_lock(args.root / "papers"):
        paper_id = next_paper_id(args.root / "papers")
        record = write_proposal_record(
            root=args.root,
            paper_id=paper_id,
            title=title,
            paper_date=args.date,
            abstracts=abstracts,
            sets=sets,
            answers=answers,
            chosen_set=chosen_set,
        )
        try:
            path = create_paper(
                root=args.root,
                title=title,
                hypotheses=chosen_set,
                findings=findings,
                references=clean_strings(args.reference),
                paper_date=args.date,
                min_hypotheses=len(chosen_set),
                abstract=answers["abstract"],
                proposal_record=record,
                paper_id=paper_id,
                lock=False,
            )
        except BaseException:
            (args.root / record).unlink(missing_ok=True)
            raise
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
