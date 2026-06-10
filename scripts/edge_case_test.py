#!/usr/bin/env python3
"""Exercise Loop Paper CLI rejection paths that protect workflow determinism."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent


def script(name: str) -> str:
    return str(SCRIPT_DIR / name)


def run_ok(command: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        print("$ " + " ".join(command), file=sys.stderr)
        if completed.stdout:
            print(completed.stdout, file=sys.stderr, end="")
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")
        raise SystemExit(completed.returncode)
    return completed


def run_fail(command: list[str], expected: str) -> None:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    output = completed.stdout + completed.stderr
    if completed.returncode == 0:
        print("$ " + " ".join(command), file=sys.stderr)
        print("Expected command to fail, but it succeeded.", file=sys.stderr)
        raise SystemExit(1)
    if expected not in output:
        print("$ " + " ".join(command), file=sys.stderr)
        print(output, file=sys.stderr, end="")
        print(f"Expected failure output to contain: {expected!r}", file=sys.stderr)
        raise SystemExit(1)


def write_answers(path: Path, *, evidence: str = "Strong") -> None:
    answers = {
        "verdict.PAPER-0001": "Supported",
        "evidence.PAPER-0001": evidence,
        "production.PAPER-0001": "Ready",
        "action.PAPER-0001": "Accept",
        "coherence": "Coherent",
        "direction": "Continue same line",
    }
    path.write_text(json.dumps(answers, indent=2), encoding="utf-8")


def mark_checkboxes(text: str, labels: list[str]) -> str:
    for label in labels:
        text = text.replace(f"- [ ] {label}", f"- [x] {label}")
    return text


def make_before_ready_with_uppercase_checks(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace("BEFORE_REQUIRED:", "Recorded:")
    text = mark_checkboxes(
        text,
        [
            "Hypothesis is specific",
            "Hypothesis can be validated or rejected",
            "Baseline evidence is recorded before implementation",
            "Prior work is cited, or missing prior work is explicitly acknowledged",
            "Implementation plan is concrete",
            "Dependencies are named",
            "Risks are named",
            "Recorded: test/verifier/check to run",
        ],
    )
    text = text.replace("- [x]", "- [X]")
    path.write_text(text, encoding="utf-8")


def make_before_ready_except_prior_research(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace("BEFORE_REQUIRED:", "Recorded:")
    text = mark_checkboxes(
        text,
        [
            "Hypothesis is specific",
            "Hypothesis can be validated or rejected",
            "Baseline evidence is recorded before implementation",
            "Implementation plan is concrete",
            "Dependencies are named",
            "Risks are named",
            "Recorded: test/verifier/check to run",
        ],
    )
    path.write_text(text, encoding="utf-8")


def make_before_ready_except_validation_plan(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace("BEFORE_REQUIRED:", "Recorded:")
    text = mark_checkboxes(
        text,
        [
            "Hypothesis is specific",
            "Hypothesis can be validated or rejected",
            "Baseline evidence is recorded before implementation",
            "Prior work is cited, or missing prior work is explicitly acknowledged",
            "Implementation plan is concrete",
            "Dependencies are named",
            "Risks are named",
        ],
    )
    path.write_text(text, encoding="utf-8")


def make_after_ready_except_validation_evidence(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace("BEFORE_REQUIRED:", "Recorded:")
    text = text.replace("AFTER_REQUIRED:", "Recorded:")
    text = mark_checkboxes(
        text,
        [
            "Hypothesis is specific",
            "Hypothesis can be validated or rejected",
            "Baseline evidence is recorded before implementation",
            "Prior work is cited, or missing prior work is explicitly acknowledged",
            "Implementation plan is concrete",
            "Dependencies are named",
            "Risks are named",
            "Recorded: test/verifier/check to run",
            "Agent reviewed paper structure",
            "Agent confirmed evidence backs the recorded verdict",
            "Impact score is based on evidence, not agent guesswork",
        ],
    )
    text = text.replace(
        "- Recorded: mark each hypothesis Supported, Failed, Inconclusive, or\n  Superseded, with the evidence reason.",
        "- Supported: edge-case verdict recorded with evidence pending.",
    )
    path.write_text(text, encoding="utf-8")


def set_status(path: Path, status: str) -> None:
    text = path.read_text(encoding="utf-8")
    if "status: Draft" not in text:
        raise SystemExit(f"Expected draft status in {path}")
    path.write_text(text.replace("status: Draft", f"status: {status}", 1), encoding="utf-8")


def set_paper_id(path: Path, paper_id: str) -> None:
    text = path.read_text(encoding="utf-8")
    current = path.name.split("-", 2)
    if len(current) < 2:
        raise SystemExit(f"Cannot infer paper id from {path}")
    filename_id = "-".join(current[:2])
    if f"paper_id: {filename_id}" not in text:
        raise SystemExit(f"Expected paper_id {filename_id} in {path}")
    path.write_text(text.replace(f"paper_id: {filename_id}", f"paper_id: {paper_id}", 1), encoding="utf-8")


def create_edge_paper(root: Path, title: str) -> Path:
    return Path(
        run_ok(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(root),
                "--title",
                title,
                "--hypothesis",
                f"{title} can exercise a checker edge case",
                "--finding",
                "Edge tests need a generated paper",
                "--reference",
                "scripts/edge_case_test.py",
                "--date",
                "2026-06-10",
            ]
        ).stdout.strip()
    )


def ensure_validator_ignores_local_paper_stack() -> None:
    local_skill = ROOT / ".paper-stack" / "validator-ignore" / "SKILL.md"
    local_skill.parent.mkdir(parents=True, exist_ok=True)
    local_skill.write_text(
        "---\nname: local-artifact\ndescription: ignored local test artifact\n---\n",
        encoding="utf-8",
    )
    try:
        run_ok([sys.executable, script("validate_skill_repo.py")])
    finally:
        local_skill.unlink(missing_ok=True)
        try:
            local_skill.parent.rmdir()
        except OSError:
            pass


def ensure_installed_payload_validates() -> None:
    with tempfile.TemporaryDirectory(prefix="loop-paper-installed-") as tmp:
        destination = Path(tmp) / "loop-paper"
        run_ok(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "codex",
                "--dest",
                str(destination),
            ]
        )
        run_ok([sys.executable, str(destination / "scripts" / "validate_skill_repo.py")])
        run_ok([sys.executable, str(destination / "scripts" / "smoke_test.py")])


def main() -> int:
    ensure_validator_ignores_local_paper_stack()
    ensure_installed_payload_validates()

    with tempfile.TemporaryDirectory(prefix="loop-paper-edge-") as tmp:
        project = Path(tmp)
        root = project / ".paper-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(root),
                "--project-name",
                "Loop Paper Edge Cases",
                "--date",
                "2026-06-10",
            ]
        )
        created = Path(
            run_ok(
                [
                    sys.executable,
                    script("new_closed_loop_paper.py"),
                    "--root",
                    str(root),
                    "--title",
                    "Edge Target",
                    "--hypothesis",
                    "Edge tests can target a paper",
                    "--finding",
                    "Edge tests need at least one paper",
                    "--reference",
                    "scripts/edge_case_test.py",
                    "--date",
                    "2026-06-10",
                ]
            ).stdout.strip()
        )

        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Missing Target Review",
                "--target",
                "PAPER-9999",
                "--format",
                "json",
            ],
            "Missing target paper files for: PAPER-9999",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Malformed Target Review",
                "--target",
                "PAPER-0001-extra",
                "--format",
                "json",
            ],
            "Expected PAPER-NNNN",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Oversized Target Review",
                "--target",
                "PAPER-10000",
                "--format",
                "json",
            ],
            "Expected PAPER-NNNN",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Bad: Title",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
            ],
            "--title must not contain",
        )

        answers = root / "inbox" / "bad-answers.json"
        answers.parent.mkdir(parents=True, exist_ok=True)
        write_answers(answers, evidence="Unsupported option")
        before_count = len(list((root / "papers").glob("PAPER-*.md")))
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Bad Answer Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(answers),
                "--date",
                "2026-06-10",
            ],
            "not in options",
        )
        after_count = len(list((root / "papers").glob("PAPER-*.md")))
        if before_count != after_count:
            raise SystemExit("Failed review answer validation wrote a paper unexpectedly")

        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(created), "--phase", "before"],
            "BEFORE_REQUIRED slots remain",
        )
        prior_gate = create_edge_paper(root, "Prior Gate Edge")
        make_before_ready_except_prior_research(prior_gate)
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(prior_gate), "--phase", "before"],
            "prior research checkboxes are not all checked",
        )
        run_ok([sys.executable, script("transition_paper.py"), str(prior_gate), "Research Ready"])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(prior_gate), "Plan Ready"],
            "prior research checkboxes are not all checked",
        )
        uppercase_gate = create_edge_paper(root, "Uppercase Checkbox Edge")
        make_before_ready_with_uppercase_checks(uppercase_gate)
        run_ok(
            [sys.executable, script("check_closed_loop_paper.py"), str(uppercase_gate), "--phase", "before"]
        )
        validation_plan_gate = create_edge_paper(root, "Validation Plan Gate Edge")
        make_before_ready_except_validation_plan(validation_plan_gate)
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(validation_plan_gate), "--phase", "before"],
            "validation plan checkboxes are not all checked",
        )
        validation_evidence_gate = create_edge_paper(root, "Validation Evidence Gate Edge")
        make_after_ready_except_validation_evidence(validation_evidence_gate)
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(validation_evidence_gate), "--phase", "after"],
            "validation evidence checkbox is not checked",
        )
        for status in ["Research Ready", "Plan Ready", "Implementing", "Implemented"]:
            run_ok([sys.executable, script("transition_paper.py"), str(validation_evidence_gate), status])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(validation_evidence_gate), "AI Validated"],
            "validation evidence checkbox is not checked",
        )
        pipeline_gate = create_edge_paper(root, "Pipeline Gate Edge")
        make_after_ready_except_validation_evidence(pipeline_gate)
        set_status(pipeline_gate, "AI Validated")
        run_fail(
            [sys.executable, script("pipeline.py"), str(root), "--strict"],
            "validation evidence checkbox is not checked",
        )
        run_fail(
            [sys.executable, script("watch_pipeline.py"), str(root), "--once"],
            "validation evidence checkbox is not checked",
        )
        status_root = project / "status-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(status_root),
                "--project-name",
                "Loop Paper Status Edge",
                "--date",
                "2026-06-10",
            ]
        )
        invalid_status_gate = create_edge_paper(status_root, "Invalid Status Edge")
        set_status(invalid_status_gate, "Totally Done")
        run_fail(
            [sys.executable, script("check_paper.py"), str(invalid_status_gate)],
            "Invalid status: Totally Done",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(status_root), "--strict"],
            "Invalid status: Totally Done",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(status_root), "--last", "1"],
            "Cannot combine invalid papers",
        )
        identity_root = project / "identity-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(identity_root),
                "--project-name",
                "Loop Paper Identity Edge",
                "--date",
                "2026-06-10",
            ]
        )
        mismatch = create_edge_paper(identity_root, "Identity Mismatch Edge")
        set_paper_id(mismatch, "PAPER-9999")
        run_fail(
            [sys.executable, script("check_paper.py"), str(mismatch)],
            "paper_id PAPER-9999 does not match filename PAPER-0001",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(identity_root), "--strict"],
            "paper_id PAPER-9999 does not match filename PAPER-0001",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(identity_root), "--last", "1"],
            "Cannot combine invalid papers",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(mismatch), "Research Ready"],
            "paper_id PAPER-9999 does not match filename PAPER-0001",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(identity_root),
                "--title",
                "Invalid Identity Target Review",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
            ],
            "paper_id PAPER-9999 does not match filename PAPER-0001",
        )
        filename_root = project / "filename-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(filename_root),
                "--project-name",
                "Loop Paper Filename Edge",
                "--date",
                "2026-06-10",
            ]
        )
        bad_filename = create_edge_paper(filename_root, "Bad Filename Edge")
        renamed_bad_filename = bad_filename.with_name("PAPER-bad-filename.md")
        bad_filename.rename(renamed_bad_filename)
        run_fail(
            [sys.executable, script("check_paper.py"), str(renamed_bad_filename)],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(filename_root), "--strict"],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(renamed_bad_filename), "Research Ready"],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        dangling_root = project / "dangling-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(dangling_root),
                "--project-name",
                "Loop Paper Dangling Edge",
                "--date",
                "2026-06-10",
            ]
        )
        dangling = create_edge_paper(dangling_root, "Dangling Reference Edge")
        dangling.write_text(
            dangling.read_text(encoding="utf-8").replace(
                "References: None",
                "References: PAPER-9999",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(dangling_root)],
            "Dangling relationship target: References -> PAPER-9999",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(dangling_root), "--strict"],
            "Dangling relationship target: References -> PAPER-9999",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(dangling_root), "--last", "1"],
            "Dangling relationship target: References -> PAPER-9999",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(dangling), "Research Ready"],
            "Dangling relationship target: References -> PAPER-9999",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(dangling_root),
                "--title",
                "Dangling Target Review",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
            ],
            "Dangling relationship target: References -> PAPER-9999",
        )
        duplicate_root = project / "duplicate-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(duplicate_root),
                "--project-name",
                "Loop Paper Duplicate Edge",
                "--date",
                "2026-06-10",
            ]
        )
        duplicate = create_edge_paper(duplicate_root, "Duplicate Identity Edge")
        duplicate_copy = duplicate.with_name("PAPER-0001-duplicate-copy.md")
        duplicate_copy.write_text(duplicate.read_text(encoding="utf-8"), encoding="utf-8")
        run_fail(
            [sys.executable, script("check_paper.py"), str(duplicate_root)],
            "Duplicate paper_id in stack: PAPER-0001",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(duplicate_root), "--strict"],
            "Duplicate paper_id in stack: PAPER-0001",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(duplicate_root), "--last", "1"],
            "Duplicate paper_id in stack: PAPER-0001",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(duplicate), "Research Ready"],
            "Duplicate paper_id in stack: PAPER-0001",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(duplicate_root),
                "--title",
                "Duplicate Target Review",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
            ],
            "Duplicate paper_id in stack: PAPER-0001",
        )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--ids",
                "PAPER-0001",
                "--last",
                "1",
            ],
            "Choose exactly one selection mode",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(root), "--from", "PAPER-0001"],
            "Interval selection requires both --from and --to",
        )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--from",
                "PAPER-0001-extra",
                "--to",
                "PAPER-0002",
            ],
            "Expected PAPER-NNNN",
        )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--from",
                "PAPER-0002",
                "--to",
                "PAPER-0001",
            ],
            "--from must be less than or equal to --to",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(root), "--last", "0"],
            "--last must be greater than zero",
        )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--last",
                "1",
                "--max-references",
                "0",
            ],
            "--max-references must be greater than zero",
        )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--last",
                "1",
                "--mode",
                "references",
                "--target-paper",
                "PAPER-9999",
            ],
            "Missing target paper ID for reference ranking: PAPER-9999",
        )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(project / "missing-root"),
                "--last",
                "1",
            ],
            "No papers found under",
        )
        overflow_root = project / "overflow-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(overflow_root),
                "--project-name",
                "Loop Paper Overflow Edge",
                "--date",
                "2026-06-10",
            ]
        )
        overflow_papers = overflow_root / "papers"
        overflow_papers.mkdir(parents=True, exist_ok=True)
        create_edge_paper(overflow_root, "Overflow Target Edge")
        (overflow_papers / "PAPER-9999-last.md").write_text("", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(overflow_root),
                "--title",
                "Overflow Paper",
                "--hypothesis",
                "Overflow should fail",
                "--finding",
                "PAPER-NNNN has a finite range",
                "--reference",
                "scripts/edge_case_test.py",
            ],
            "Cannot allocate next paper ID beyond PAPER-9999",
        )
        overflow_answers = overflow_root / "inbox" / "answers.json"
        overflow_answers.parent.mkdir(parents=True, exist_ok=True)
        write_answers(overflow_answers)
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(overflow_root),
                "--title",
                "Overflow Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(overflow_answers),
            ],
            "Cannot allocate next paper ID beyond PAPER-9999",
        )

    print("OK loop-paper edge-case test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
