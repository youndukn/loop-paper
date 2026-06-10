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


def ensure_installer_rejects_recursive_destinations() -> None:
    run_fail(
        [
            sys.executable,
            script("install_skill.py"),
            "--agent",
            "codex",
            "--dest",
            str(ROOT / "scripts" / "nested-install"),
        ],
        "Refusing to install inside the source checkout",
    )
    run_fail(
        [
            sys.executable,
            script("install_skill.py"),
            "--agent",
            "codex",
            "--dest",
            str(ROOT.parent),
            "--force",
            "--dry-run",
        ],
        "Refusing to install over a parent of the source checkout",
    )


def ensure_installer_rejects_file_parent() -> None:
    with tempfile.TemporaryDirectory(prefix="loop-paper-install-parent-") as tmp:
        parent_file = Path(tmp) / "not-a-directory"
        parent_file.write_text("file parent", encoding="utf-8")
        destination = parent_file / "loop-paper"
        run_fail(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "codex",
                "--dest",
                str(destination),
            ],
            f"Expected install parent directory, got file: {parent_file}",
        )


def main() -> int:
    ensure_validator_ignores_local_paper_stack()
    ensure_installed_payload_validates()
    ensure_installer_rejects_recursive_destinations()
    ensure_installer_rejects_file_parent()

    with tempfile.TemporaryDirectory(prefix="loop-paper-edge-") as tmp:
        project = Path(tmp)
        root = project / ".paper-stack"
        root_file = project / "paper-stack-file"
        root_file.write_text("not a directory", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(root_file),
                "--project-name",
                "Root File Stack",
                "--date",
                "2026-06-10",
            ],
            f"Expected paper stack root, got file: {root_file}",
        )
        run_fail(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(project / "bad-date-stack"),
                "--project-name",
                "Bad Date Stack",
                "--date",
                "2026-02-30",
            ],
            "--date must be a valid calendar date",
        )
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
        papers_file_root = project / "creator-papers-file-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(papers_file_root),
                "--project-name",
                "Loop Paper Creator Papers File Edge",
                "--date",
                "2026-06-10",
            ]
        )
        creator_papers_file = papers_file_root / "papers"
        creator_papers_file.rmdir()
        creator_papers_file.write_text("not a directory", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(papers_file_root),
                "--title",
                "Papers File Paper",
                "--hypothesis",
                "Papers path should be a directory",
                "--finding",
                "Creation needs deterministic directory errors",
                "--reference",
                "scripts/edge_case_test.py",
                "--date",
                "2026-06-10",
            ],
            f"Expected papers directory, got file: {creator_papers_file}",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(papers_file_root),
                "--title",
                "Papers File Review",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
                "--date",
                "2026-06-10",
            ],
            f"Expected papers directory, got file: {creator_papers_file}",
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
        escaped = Path(
            run_ok(
                [
                    sys.executable,
                    script("new_closed_loop_paper.py"),
                    "--root",
                    str(root),
                    "--title",
                    "Pipe | Title",
                    "--hypothesis",
                    "Pipe | claim\nwith newline",
                    "--finding",
                    "Finding | data\nsecond line",
                    "--reference",
                    "docs/reference | one\nsecond",
                    "--date",
                    "2026-06-10",
                ]
            ).stdout.strip()
        )
        escaped_text = escaped.read_text(encoding="utf-8")
        if "| H1 | Pipe \\| claim with newline |" not in escaped_text:
            raise SystemExit("Generated hypothesis table did not escape pipe/newline input")
        if "| 2026-06-10 | Finding \\| data second line |" not in escaped_text:
            raise SystemExit("Generated findings table did not escape pipe/newline input")
        if "- docs/reference | one second" not in escaped_text:
            raise SystemExit("Generated reference list did not collapse newline input")
        report_output = root / "dashboard" / "pipe-report.md"
        run_ok(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ]
        )
        report_text = report_output.read_text(encoding="utf-8")
        if "Pipe \\| Title" not in report_text:
            raise SystemExit("Exported report table did not escape title pipe")
        impact_scores = root / "dashboard" / "impact-scores.json"
        impact_scores.mkdir()
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            f"Expected impact scores JSON file, got directory: {impact_scores}",
        )
        impact_scores.rmdir()
        impact_scores.write_text("{", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "impact scores JSON is invalid",
        )
        impact_scores.write_text(json.dumps([]), encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "impact scores JSON must be an object",
        )
        impact_scores.write_text(json.dumps({"papers": {}}), encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "impact scores JSON field 'papers' must be a list",
        )
        impact_scores.write_text(json.dumps({"papers": [{}]}), encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "impact score paper item 1 missing paper_id",
        )
        impact_scores.write_text(
            json.dumps(
                {
                    "papers": [
                        {
                            "paper_id": "PAPER-0001",
                            "deterministic_partial_score": "A | B",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        run_ok(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ]
        )
        if "A \\| B" not in report_output.read_text(encoding="utf-8"):
            raise SystemExit("Exported report table did not escape score pipe")
        impact_scores.unlink()
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(root),
                "--title",
                "Bad Date Paper",
                "--hypothesis",
                "Bad date should fail",
                "--finding",
                "Generated frontmatter dates must be deterministic ISO dates",
                "--reference",
                "scripts/edge_case_test.py",
                "--date",
                "20260610",
            ],
            "--date must be YYYY-MM-DD",
        )
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(root),
                "--title",
                "Bad Minimum Hypotheses",
                "--hypothesis",
                "Minimum hypotheses should be positive",
                "--finding",
                "Silent coercion hides invalid caller input",
                "--reference",
                "scripts/edge_case_test.py",
                "--min-hypotheses",
                "0",
            ],
            "--min-hypotheses must be greater than zero",
        )
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(root),
                "--title",
                "Bad Slug Paper",
                "--slug",
                "bad/path",
                "--hypothesis",
                "Bad slug should fail",
                "--finding",
                "Unsafe custom slugs can break deterministic output paths",
                "--reference",
                "scripts/edge_case_test.py",
            ],
            "--slug must contain only ASCII letters, numbers, and single hyphens",
        )
        missing_paper = root / "papers" / "PAPER-9999-missing.md"
        for command in [
            [sys.executable, script("check_paper.py"), str(missing_paper)],
            [sys.executable, script("check_closed_loop_paper.py"), str(missing_paper), "--phase", "before"],
            [sys.executable, script("transition_paper.py"), str(missing_paper), "Research Ready"],
            [sys.executable, script("agent_review.py"), str(missing_paper)],
            [sys.executable, script("update_paper_metadata.py"), str(missing_paper), "--check"],
        ]:
            run_fail(command, f"Missing paper file: {missing_paper}")

        review_injection = create_edge_paper(root, "Agent Review Injection Edge")
        run_ok(
            [
                sys.executable,
                script("agent_review.py"),
                str(review_injection),
                "--reviewer",
                "Codex\n## Agent Review",
                "--decision",
                "AI Validated\n## Impact Score",
                "--notes",
                "Looks good\n## Impact Score\ninjected",
            ]
        )
        review_text = review_injection.read_text(encoding="utf-8")
        if review_text.count("\n## Agent Review\n") != 1:
            raise SystemExit("Agent review input injected an extra Agent Review heading")
        if review_text.count("\n## Impact Score\n") != 1:
            raise SystemExit("Agent review input injected an extra Impact Score heading")
        if "Codex ## Agent Review" not in review_text:
            raise SystemExit("Agent reviewer input was not collapsed to inline Markdown")
        if "AI Validated ## Impact Score" not in review_text:
            raise SystemExit("Agent decision input was not collapsed to inline Markdown")
        if "Looks good ## Impact Score injected" not in review_text:
            raise SystemExit("Agent review notes were not collapsed to inline Markdown")
        run_ok([sys.executable, script("check_paper.py"), str(review_injection)])

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
                "Bad Date Review",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
                "--date",
                "2026-13-01",
            ],
            "--date must be a valid calendar date",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Bad Slug Review",
                "--slug",
                "../bad",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
            ],
            "--slug must contain only ASCII letters, numbers, and single hyphens",
        )
        prompt_output_dir = root / "inbox" / "prompt-output-dir"
        prompt_output_dir.mkdir(parents=True)
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Directory Prompt Output Review",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
                "--prompt-out",
                str(prompt_output_dir),
            ],
            f"Expected prompt output file, got directory: {prompt_output_dir}",
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
        missing_answers = root / "inbox" / "missing-answers.json"
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Missing Answers Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(missing_answers),
                "--date",
                "2026-06-10",
            ],
            f"Missing answers JSON file: {missing_answers}",
        )
        answers_directory = root / "inbox" / "answers-directory.json"
        answers_directory.mkdir()
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Directory Answers Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(answers_directory),
                "--date",
                "2026-06-10",
            ],
            f"Expected answers JSON file, got directory: {answers_directory}",
        )
        invalid_json = root / "inbox" / "invalid-json-answers.json"
        invalid_json.write_text("{", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Invalid Json Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(invalid_json),
                "--date",
                "2026-06-10",
            ],
            "answers JSON is invalid",
        )
        malformed_list = root / "inbox" / "malformed-list-answers.json"
        malformed_list.write_text(json.dumps([{"id": "verdict.PAPER-0001"}]), encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Malformed List Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(malformed_list),
                "--date",
                "2026-06-10",
            ],
            "answers list items must be objects with id and answer",
        )
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
        run_fail(
            [sys.executable, script("watch_pipeline.py"), str(root), "--interval", "0", "--once"],
            "--interval must be greater than zero",
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
            [sys.executable, script("agent_review.py"), str(mismatch)],
            "paper_id PAPER-9999 does not match filename PAPER-0001",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(mismatch)],
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
        zero_root = project / "zero-id-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(zero_root),
                "--project-name",
                "Loop Paper Zero ID Edge",
                "--date",
                "2026-06-10",
            ]
        )
        zero_id = create_edge_paper(zero_root, "Zero ID Edge")
        set_paper_id(zero_id, "PAPER-0000")
        zero_path = zero_id.with_name("PAPER-0000-zero-id-edge.md")
        zero_id.rename(zero_path)
        run_fail(
            [sys.executable, script("check_paper.py"), str(zero_path)],
            "Invalid paper_id: PAPER-0000",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(zero_root), "--strict"],
            "Invalid paper_id: PAPER-0000",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(zero_root), "--last", "1"],
            "Invalid paper_id: PAPER-0000",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(zero_path), "Research Ready"],
            "Invalid paper_id: PAPER-0000",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Zero Target Review",
                "--target",
                "PAPER-0000",
                "--format",
                "json",
            ],
            "Expected PAPER-NNNN",
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
        malformed_numeric_filename_root = project / "malformed-numeric-filename-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(malformed_numeric_filename_root),
                "--project-name",
                "Loop Paper Malformed Numeric Filename Edge",
                "--date",
                "2026-06-10",
            ]
        )
        malformed_numeric_filename = create_edge_paper(
            malformed_numeric_filename_root,
            "Malformed Numeric Filename Edge",
        )
        renamed_malformed_numeric_filename = malformed_numeric_filename.with_name("PAPER-0001bad.md")
        malformed_numeric_filename.rename(renamed_malformed_numeric_filename)
        run_fail(
            [sys.executable, script("check_paper.py"), str(renamed_malformed_numeric_filename)],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(malformed_numeric_filename_root), "--strict"],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(malformed_numeric_filename_root),
                "--last",
                "1",
            ],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        run_fail(
            [
                sys.executable,
                script("transition_paper.py"),
                str(renamed_malformed_numeric_filename),
                "Research Ready",
            ],
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
        for command in [
            [sys.executable, script("index_references.py"), str(dangling_root)],
            [sys.executable, script("score_impact.py"), str(dangling_root)],
            [sys.executable, script("export_report.py"), str(dangling_root)],
            [sys.executable, script("render_dashboard.py"), str(dangling_root)],
        ]:
            run_fail(command, "Dangling relationship target: References -> PAPER-9999")
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
                "PAPER-0000",
                "--to",
                "PAPER-0001",
            ],
            "Expected PAPER-NNNN",
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
        output_dir = root / "dashboard" / "output-dir"
        output_dir.mkdir(parents=True)
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--last",
                "1",
                "--output",
                str(output_dir),
            ],
            f"Expected output file, got directory: {output_dir}",
        )
        for command in [
            [sys.executable, script("index_references.py"), str(root), "--output", str(output_dir)],
            [sys.executable, script("score_impact.py"), str(root), "--output", str(output_dir)],
            [sys.executable, script("export_report.py"), str(root), "--output", str(output_dir)],
        ]:
            run_fail(command, f"Expected output file, got directory: {output_dir}")
        output_parent_file = root / "dashboard" / "output-parent-file"
        output_parent_file.write_text("file parent", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--last",
                "1",
                "--output",
                str(output_parent_file / "combined.md"),
            ],
            f"Expected parent directory for output, got file: {output_parent_file}",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Parent File Prompt Output Review",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
                "--prompt-out",
                str(output_parent_file / "prompts.json"),
            ],
            f"Expected parent directory for prompt output, got file: {output_parent_file}",
        )
        dashboard_file_root = project / "dashboard-file-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(dashboard_file_root),
                "--project-name",
                "Loop Paper Dashboard File Edge",
                "--date",
                "2026-06-10",
            ]
        )
        create_edge_paper(dashboard_file_root, "Dashboard File Edge")
        dashboard_file = dashboard_file_root / "dashboard"
        dashboard_file.rmdir()
        dashboard_file.write_text("not a directory", encoding="utf-8")
        run_fail(
            [sys.executable, script("render_dashboard.py"), str(dashboard_file_root)],
            f"Expected dashboard directory, got file: {dashboard_file}",
        )
        papers_file_root = project / "papers-file-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(papers_file_root),
                "--project-name",
                "Loop Paper Papers File Edge",
                "--date",
                "2026-06-10",
            ]
        )
        papers_file = papers_file_root / "papers"
        papers_file.rmdir()
        papers_file.write_text("not a directory", encoding="utf-8")
        run_fail(
            [sys.executable, script("render_dashboard.py"), str(papers_file_root)],
            f"Expected papers directory, got file: {papers_file}",
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
