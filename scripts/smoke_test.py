#!/usr/bin/env python3
"""Run an end-to-end Loop Paper smoke test in a temporary project."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def run(command: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        print("$ " + " ".join(command), file=sys.stderr)
        if completed.stdout:
            print(completed.stdout, file=sys.stderr, end="")
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")
        raise SystemExit(completed.returncode)
    return completed


def script(name: str) -> str:
    return str(SCRIPT_DIR / name)


def replace_all(text: str, replacements: dict[str, str]) -> str:
    for old, new in replacements.items():
        if old not in text:
            raise SystemExit(f"Expected template text not found: {old!r}")
        text = text.replace(old, new)
    return text


def complete_closed_loop_paper(path: Path, *, title: str) -> None:
    text = path.read_text(encoding="utf-8")
    replacements = {
        "BEFORE_REQUIRED: state the work unit, why it matters, and what completion would\nprove. If this is retrospective, say so explicitly.": (
            f"{title} validates the smoke-test closed-loop path and records the next step."
        ),
        "BEFORE_REQUIRED: baseline evidence": "Baseline evidence recorded",
        "BEFORE_REQUIRED: validation method": "Run deterministic smoke verifier",
        "Prior Research Status: BEFORE_REQUIRED: Present/Missing/Retrospective": "Prior Research Status: Present",
        "Risk: BEFORE_REQUIRED: Low/Medium/High": "Risk: Low",
        "BEFORE_REQUIRED: evidence path or command": "scripts/smoke_test.py",
        "BEFORE_REQUIRED: implementation boundary": "Temporary smoke project only",
        "BEFORE_REQUIRED: first implementation step tied to a hypothesis": "Create a closed-loop paper",
        "BEFORE_REQUIRED: second implementation step tied to a hypothesis": "Validate and transition the paper",
        "BEFORE_REQUIRED: risk or failure mode": "Template drift could break transition gates",
        "BEFORE_REQUIRED: how to preserve or undo failed work": "Delete the temporary smoke project",
        "BEFORE_REQUIRED: command, artifact, metric, screenshot, or reason baseline is\n  unavailable": (
            "Smoke-test project initialized"
        ),
        "AFTER_REQUIRED: command, artifact, metric, screenshot, or inspection": "Smoke verifier completed",
        "[ ] BEFORE_REQUIRED: test/verifier/check to run": "[x] Run deterministic smoke verifier",
        "BEFORE_REQUIRED: exact baseline output or inspected evidence": "Baseline output captured",
        "AFTER_REQUIRED: exact post-change output or inspected evidence": "After output captured",
        "AFTER_REQUIRED: mark each hypothesis Supported, Failed, Inconclusive, or\n  Superseded, with the evidence reason.": (
            "Supported: deterministic smoke verifier completed."
        ),
        "[ ] AI validation evidence recorded": "[x] AI validation evidence recorded",
        "Agent reviewer:": "Agent reviewer: smoke-test",
        "Review date:": "Review date: 2026-06-10",
        "Decision: AFTER_REQUIRED: Draft/Plan Ready/Implemented/AI Validated/Rejected": "Decision: AI Validated",
        "AFTER_REQUIRED: agent review findings": "No agent findings",
        "[ ] Agent reviewed paper structure": "[x] Agent reviewed paper structure",
        "[ ] Agent confirmed evidence backs the recorded verdict": "[x] Agent confirmed evidence backs the recorded verdict",
        "AFTER_REQUIRED: TBD until measured": "Measured by smoke verifier",
        "AFTER_REQUIRED: TBD until validation runs": "Validation passed in smoke verifier",
        "AFTER_REQUIRED: before/after delta or failed result": "No regression observed",
        "[ ] Impact score is based on evidence, not agent guesswork": "[x] Impact score is based on evidence, not agent guesswork",
    }
    text = replace_all(text, replacements)
    text = re.sub(
        r"AFTER_REQUIRED: `\.paper-stack/runs/RUN-YYYY-MM-DD-(PAPER-\d{4})-short-name\.md`",
        r".paper-stack/runs/RUN-2026-06-10-\1-smoke.md",
        text,
    )
    text = re.sub(
        r"AFTER_REQUIRED: `\.paper-stack/fixes/FIX-YYYY-MM-DD-(PAPER-\d{4})-short-name\.md`",
        r".paper-stack/fixes/FIX-2026-06-10-\1-smoke.md",
        text,
    )
    text = text.replace("[ ] Hypothesis is specific", "[x] Hypothesis is specific")
    text = text.replace("[ ] Hypothesis can be validated or rejected", "[x] Hypothesis can be validated or rejected")
    text = text.replace("[ ] Baseline evidence is recorded before implementation", "[x] Baseline evidence is recorded before implementation")
    text = text.replace("[ ] Prior work is cited, or missing prior work is explicitly acknowledged", "[x] Prior work is cited, or missing prior work is explicitly acknowledged")
    text = text.replace("[ ] Implementation plan is concrete", "[x] Implementation plan is concrete")
    text = text.replace("[ ] Dependencies are named", "[x] Dependencies are named")
    text = text.replace("[ ] Risks are named", "[x] Risks are named")
    remaining = sorted(set(re.findall(r".{0,60}\b(?:BEFORE_REQUIRED|AFTER_REQUIRED)\b.{0,60}", text)))
    if remaining:
        details = "\n".join(f"- {item.strip()}" for item in remaining)
        raise SystemExit(f"Required placeholders remain in {path}:\n{details}")
    path.write_text(text, encoding="utf-8")


def transition_to_accepted(path: Path) -> None:
    for status in [
        "Research Ready",
        "Plan Ready",
        "Implementing",
        "Implemented",
        "AI Validated",
        "Accepted",
    ]:
        run([sys.executable, script("transition_paper.py"), str(path), status])


def ensure_prompt_ids(root: Path, target: str) -> None:
    for fmt in ["cli", "json", "claude", "codex", "pi"]:
        output = root / "inbox" / f"review-prompts-{fmt}.txt"
        run(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Review Prompt Smoke",
                "--target",
                target,
                "--format",
                fmt,
                "--prompt-out",
                str(output),
            ]
        )
        text = output.read_text(encoding="utf-8")
        if f"verdict.{target}" not in text:
            raise SystemExit(f"{fmt} prompt output is missing answer IDs")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="loop-paper-smoke-") as tmp:
        project = Path(tmp)
        root = project / ".paper-stack"
        run(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(root),
                "--project-name",
                "Loop Paper Smoke",
                "--date",
                "2026-06-10",
            ]
        )

        papers = []
        for index in [1, 2]:
            created = run(
                [
                    sys.executable,
                    script("new_closed_loop_paper.py"),
                    "--root",
                    str(root),
                    "--title",
                    f"Smoke Target {index}",
                    "--hypothesis",
                    f"Smoke target {index} can complete the loop",
                    "--finding",
                    "The smoke test needs a closed-loop target",
                    "--reference",
                    "scripts/smoke_test.py",
                    "--min-hypotheses",
                    "1",
                    "--date",
                    "2026-06-10",
                ]
            )
            path = Path(created.stdout.strip())
            complete_closed_loop_paper(path, title=f"Smoke target {index}")
            run([sys.executable, script("check_closed_loop_paper.py"), str(path), "--phase", "before"])
            run([sys.executable, script("check_closed_loop_paper.py"), str(path), "--phase", "after"])
            transition_to_accepted(path)
            papers.append(path)

        ensure_prompt_ids(root, "PAPER-0001")
        answers = {
            "verdict.PAPER-0001": "Supported",
            "evidence.PAPER-0001": "Strong",
            "production.PAPER-0001": "Ready",
            "action.PAPER-0001": "Accept",
            "verdict.PAPER-0002": "Supported",
            "evidence.PAPER-0002": "Strong",
            "production.PAPER-0002": "Ready",
            "action.PAPER-0002": "Accept",
            "coherence": "Coherent",
            "direction": "Continue same line",
        }
        answers_path = root / "inbox" / "answers.json"
        answers_path.write_text(json.dumps(answers, indent=2), encoding="utf-8")
        review = Path(
            run(
                [
                    sys.executable,
                    script("new_review_paper.py"),
                    "--root",
                    str(root),
                    "--title",
                    "Smoke Review",
                    "--target",
                    "PAPER-0001",
                    "--target",
                    "PAPER-0002",
                    "--answers",
                    str(answers_path),
                    "--date",
                    "2026-06-10",
                ]
            ).stdout.strip()
        )
        run([sys.executable, script("check_closed_loop_paper.py"), str(review), "--phase", "after"])
        run([sys.executable, script("transition_paper.py"), str(review), "Accepted"])
        run(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--from",
                "PAPER-0001",
                "--to",
                "PAPER-0003",
                "--interval-size",
                "2",
                "--mode",
                "both",
                "--target-paper",
                "PAPER-0003",
                "--json",
            ]
        )
        run([sys.executable, script("pipeline.py"), str(root), "--strict"])
        print("OK loop-paper smoke test")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
