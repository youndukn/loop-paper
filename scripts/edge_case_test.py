#!/usr/bin/env python3
"""Exercise Loop Paper CLI rejection paths that protect workflow determinism."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import date
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


def ensure_validator_rejects_malformed_skill_frontmatter() -> None:
    skill = ROOT / "SKILL.md"
    original = skill.read_text(encoding="utf-8")
    try:
        skill.write_text(
            original.replace("name: loop-paper", "name: loop-paper\nname: duplicate-loop-paper", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("validate_skill_repo.py")],
            "duplicate frontmatter key: name",
        )
        skill.write_text(
            original.replace("description:", "description", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("validate_skill_repo.py")],
            "malformed frontmatter line",
        )
    finally:
        skill.write_text(original, encoding="utf-8")


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
        run_fail(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "codex",
                "--dest",
                str(destination),
                "--dry-run",
            ],
            f"Expected install parent directory, got file: {parent_file}",
        )
        nested_destination = parent_file / "nested" / "loop-paper"
        run_fail(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "codex",
                "--dest",
                str(nested_destination),
            ],
            f"Expected install parent directory, got file: {parent_file}",
        )
        run_fail(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "codex",
                "--dest",
                str(nested_destination),
                "--dry-run",
            ],
            f"Expected install parent directory, got file: {parent_file}",
        )


def main() -> int:
    ensure_validator_ignores_local_paper_stack()
    ensure_validator_rejects_malformed_skill_frontmatter()
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
        root_parent_file = project / "root-parent-file"
        root_parent_file.write_text("not a directory", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(root_parent_file / "nested-stack"),
                "--project-name",
                "Nested Root File Stack",
                "--date",
                "2026-06-10",
            ],
            f"Expected parent directory for paper stack root, got file: {root_parent_file}",
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
        missing_review_root = project / "missing-review-root"
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(missing_review_root),
                "--title",
                "Missing Root Review",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
                "--date",
                "2026-06-10",
            ],
            f"Missing papers directory: {missing_review_root / 'papers'}",
        )
        if missing_review_root.exists():
            raise SystemExit("Review paper creation initialized a missing root unexpectedly")
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
        script_title = Path(
            run_ok(
                [
                    sys.executable,
                    script("new_closed_loop_paper.py"),
                    "--root",
                    str(root),
                    "--title",
                    "Script </script> Edge",
                    "--hypothesis",
                    "Dashboard JSON should not close inline scripts",
                    "--finding",
                    "Generated dashboards embed paper metadata in JavaScript",
                    "--reference",
                    "scripts/edge_case_test.py",
                    "--date",
                    "2026-06-10",
                ]
            ).stdout.strip()
        )
        run_ok([sys.executable, script("render_dashboard.py"), str(root)])
        dashboard_html = (root / "dashboard" / "index.html").read_text(encoding="utf-8")
        if "Script </script> Edge" in dashboard_html:
            raise SystemExit("Dashboard embedded an unescaped script-closing title")
        if "Script <\\/script> Edge" not in dashboard_html:
            raise SystemExit("Dashboard did not preserve escaped script-closing title")
        if not script_title.exists():
            raise SystemExit("Script-title paper was not created")
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
        impact_scores.write_text(json.dumps({"papers": [{"paper_id": "PAPER-1"}]}), encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "impact score paper item 1 has invalid paper_id: PAPER-1",
        )
        impact_scores.write_text(json.dumps({"papers": [{"paper_id": "PAPER-9999"}]}), encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "impact score references unknown paper_id: PAPER-9999",
        )
        impact_scores.write_text(
            json.dumps({"papers": [{"paper_id": "PAPER-0001"}, {"paper_id": "PAPER-0001"}]}),
            encoding="utf-8",
        )
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "duplicate impact score paper_id: PAPER-0001",
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

        review_repair = create_edge_paper(root, "Agent Review Repair Edge")
        repair_text = review_repair.read_text(encoding="utf-8")
        review_start = repair_text.index("\n## Agent Review\n")
        impact_start = repair_text.index("\n## Impact Score\n")
        review_repair.write_text(
            repair_text[:review_start] + repair_text[impact_start:],
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(review_repair)],
            "Agent Review",
        )
        run_ok([sys.executable, script("agent_review.py"), str(review_repair)])
        run_ok([sys.executable, script("check_paper.py"), str(review_repair)])
        if "Agent reviewer: Codex" not in review_repair.read_text(encoding="utf-8"):
            raise SystemExit("Agent review did not repair missing Agent Review section")

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
        if f"updated: {date.today().isoformat()}" not in review_text:
            raise SystemExit("Agent review did not refresh updated frontmatter")
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
                "Short Target Review",
                "--target",
                "PAPER-1",
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
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Duplicate Explicit Target Review",
                "--target",
                "PAPER-0001",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
            ],
            "Duplicate review targets: PAPER-0001",
        )

        no_slug_target_root = project / "no-slug-target-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(no_slug_target_root),
                "--project-name",
                "Loop Paper No Slug Target Edge",
                "--date",
                "2026-06-10",
            ]
        )
        slugged_target = create_edge_paper(no_slug_target_root, "No Slug Target Edge")
        no_slug_target = no_slug_target_root / "papers" / "PAPER-0001.md"
        slugged_target.rename(no_slug_target)
        no_slug_answers = no_slug_target_root / "inbox" / "answers.json"
        no_slug_answers.parent.mkdir(parents=True, exist_ok=True)
        write_answers(no_slug_answers)
        no_slug_review = Path(
            run_ok(
                [
                    sys.executable,
                    script("new_review_paper.py"),
                    "--root",
                    str(no_slug_target_root),
                    "--title",
                    "No Slug Target Review",
                    "--target",
                    "PAPER-0001",
                    "--answers",
                    str(no_slug_answers),
                    "--date",
                    "2026-06-10",
                ]
            ).stdout.strip()
        )
        if not no_slug_review.exists():
            raise SystemExit("Review paper was not created for canonical no-slug target")
        run_ok([sys.executable, script("check_paper.py"), str(no_slug_target_root)])

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
        duplicate_answer_list = root / "inbox" / "duplicate-answer-list.json"
        duplicate_answer_list.write_text(
            json.dumps(
                [
                    {"id": "verdict.PAPER-0001", "answer": "Supported"},
                    {"id": "verdict.PAPER-0001", "answer": "Failed"},
                ]
            ),
            encoding="utf-8",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Duplicate Answer Id Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(duplicate_answer_list),
                "--date",
                "2026-06-10",
            ],
            "duplicate answer id: verdict.PAPER-0001",
        )
        unknown_answer = root / "inbox" / "unknown-answer.json"
        write_answers(unknown_answer)
        unknown_payload = json.loads(unknown_answer.read_text(encoding="utf-8"))
        unknown_payload["unexpected.PAPER-0001"] = "Supported"
        unknown_answer.write_text(json.dumps(unknown_payload), encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Unknown Answer Id Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(unknown_answer),
                "--date",
                "2026-06-10",
            ],
            "answers contain unknown ids: unexpected.PAPER-0001",
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

        review_meta_root = project / "review-metadata-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(review_meta_root),
                "--project-name",
                "Loop Paper Review Metadata Edge",
                "--date",
                "2026-06-10",
            ]
        )
        create_edge_paper(review_meta_root, "Review Metadata Target")
        review_answers = review_meta_root / "inbox" / "answers.json"
        review_answers.parent.mkdir(parents=True, exist_ok=True)
        write_answers(review_answers)
        review_paper = Path(
            run_ok(
                [
                    sys.executable,
                    script("new_review_paper.py"),
                    "--root",
                    str(review_meta_root),
                    "--title",
                    "Review Metadata Paper",
                    "--target",
                    "PAPER-0001",
                    "--answers",
                    str(review_answers),
                    "--date",
                    "2026-06-10",
                ]
            ).stdout.strip()
        )
        run_ok([sys.executable, script("check_paper.py"), str(review_meta_root)])
        review_text = review_paper.read_text(encoding="utf-8")
        review_paper.write_text(
            review_text.replace("paper_kind: review", "paper_kind: mystery", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(review_paper)],
            "Invalid paper_kind: mystery",
        )
        review_paper.write_text(review_text, encoding="utf-8")
        review_paper.write_text(
            review_text.replace("review_targets: PAPER-0001", "review_targets: PAPER-1", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(review_paper)],
            "Invalid review_targets entry: PAPER-1",
        )
        review_paper.write_text(review_text, encoding="utf-8")
        review_paper.write_text(
            review_text.replace("review_targets: PAPER-0001", "review_targets: PAPER-9999", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(review_meta_root)],
            "Dangling review target: PAPER-9999",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(review_meta_root), "--strict"],
            "Dangling review target: PAPER-9999",
        )
        review_paper.write_text(review_text, encoding="utf-8")
        review_id = "-".join(review_paper.name.split("-", 2)[:2])
        review_paper.write_text(
            review_text.replace("review_targets: PAPER-0001", f"review_targets: {review_id}", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(review_meta_root)],
            f"Review paper cannot target itself: {review_id}",
        )
        review_paper.write_text(review_text, encoding="utf-8")
        review_paper.write_text(
            review_text.replace("References: PAPER-0001", "References: None", 1),
            encoding="utf-8",
        )
        for command in [
            [sys.executable, script("check_paper.py"), str(review_meta_root)],
            [sys.executable, script("pipeline.py"), str(review_meta_root), "--strict"],
            [sys.executable, script("render_dashboard.py"), str(review_meta_root)],
            [sys.executable, script("index_references.py"), str(review_meta_root)],
            [
                sys.executable,
                script("combine_papers.py"),
                str(review_meta_root),
                "--ids",
                "PAPER-0001",
                review_id,
            ],
        ]:
            run_fail(command, "review_targets must match References relationship targets")
        review_paper.write_text(review_text, encoding="utf-8")
        closed_loop_with_targets = review_meta_root / "papers" / "PAPER-0001-review-metadata-target.md"
        closed_loop_text = closed_loop_with_targets.read_text(encoding="utf-8")
        closed_loop_with_targets.write_text(
            closed_loop_text.replace(
                "impact_score: TBD\n",
                "impact_score: TBD\nreview_targets: PAPER-0002\n",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(closed_loop_with_targets)],
            "review_targets requires paper_kind: review",
        )

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
        run_ok(
            [
                sys.executable,
                script("transition_paper.py"),
                str(validation_plan_gate),
                "Plan Ready",
                "--force",
            ]
        )
        run_ok([sys.executable, script("transition_paper.py"), str(validation_plan_gate), "Research Ready"])
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
        phase_output_root = project / "phase-output-gate-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(phase_output_root),
                "--project-name",
                "Loop Paper Phase Output Gate",
                "--date",
                "2026-06-10",
            ]
        )
        phase_output_gate = create_edge_paper(phase_output_root, "Phase Output Gate Edge")
        make_after_ready_except_validation_evidence(phase_output_gate)
        set_status(phase_output_gate, "AI Validated")
        run_fail(
            [sys.executable, script("pipeline.py"), str(phase_output_root), "--strict"],
            "SKIP generated outputs",
        )
        blocked_outputs = [
            phase_output_root / "dashboard" / "references.json",
            phase_output_root / "dashboard" / "impact-scores.json",
            phase_output_root / "dashboard" / "index.html",
            phase_output_root / "dashboard" / "report.md",
            phase_output_root / "dashboard" / "pipeline-summary.json",
        ]
        written = [str(path) for path in blocked_outputs if path.exists()]
        if written:
            raise SystemExit("Failed phase gate wrote generated outputs: " + ", ".join(written))
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
        missing_status_root = project / "missing-status-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(missing_status_root),
                "--project-name",
                "Loop Paper Missing Status Edge",
                "--date",
                "2026-06-10",
            ]
        )
        missing_status = create_edge_paper(missing_status_root, "Missing Status Edge")
        missing_status.write_text(
            missing_status.read_text(encoding="utf-8").replace("status: Draft\n", "", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(missing_status)],
            "Missing status frontmatter",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(missing_status), "Research Ready"],
            "Missing status frontmatter",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(missing_status), "--check"],
            "CHANGED PAPER-0001",
        )
        run_ok([sys.executable, script("update_paper_metadata.py"), str(missing_status)])
        run_ok([sys.executable, script("check_paper.py"), str(missing_status)])
        run_ok([sys.executable, script("pipeline.py"), str(missing_status_root), "--strict"])
        run_ok([sys.executable, script("combine_papers.py"), str(missing_status_root), "--last", "1"])
        missing_title_root = project / "missing-title-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(missing_title_root),
                "--project-name",
                "Loop Paper Missing Title Edge",
                "--date",
                "2026-06-10",
            ]
        )
        missing_title = create_edge_paper(missing_title_root, "Missing Title Edge")
        missing_title.write_text(
            missing_title.read_text(encoding="utf-8").replace("title: Missing Title Edge\n", "", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(missing_title)],
            "Missing title frontmatter",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(missing_title), "Research Ready"],
            "Missing title frontmatter",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(missing_title), "--check"],
            "CHANGED PAPER-0001",
        )
        run_ok([sys.executable, script("update_paper_metadata.py"), str(missing_title)])
        run_ok([sys.executable, script("check_paper.py"), str(missing_title)])
        run_ok([sys.executable, script("pipeline.py"), str(missing_title_root), "--strict"])
        run_ok([sys.executable, script("combine_papers.py"), str(missing_title_root), "--last", "1"])
        date_root = project / "date-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(date_root),
                "--project-name",
                "Loop Paper Date Edge",
                "--date",
                "2026-06-10",
            ]
        )
        invalid_date = create_edge_paper(date_root, "Invalid Metadata Date Edge")
        invalid_date.write_text(
            invalid_date.read_text(encoding="utf-8").replace("created: 2026-06-10", "created: 2026-02-30", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(invalid_date)],
            "created must be a valid calendar date",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(date_root), "--strict"],
            "created must be a valid calendar date",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(date_root), "--last", "1"],
            "Cannot combine invalid papers",
        )
        frontmatter_root = project / "frontmatter-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(frontmatter_root),
                "--project-name",
                "Loop Paper Frontmatter Edge",
                "--date",
                "2026-06-10",
            ]
        )
        malformed_frontmatter = create_edge_paper(frontmatter_root, "Malformed Frontmatter Edge")
        malformed_frontmatter.write_text(
            malformed_frontmatter.read_text(encoding="utf-8").replace(
                "status: Draft",
                "status Draft",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(malformed_frontmatter)],
            "Malformed frontmatter line",
        )
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(malformed_frontmatter), "--phase", "before"],
            "Malformed frontmatter line",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(frontmatter_root), "--strict"],
            "Malformed frontmatter line",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(frontmatter_root), "--last", "1"],
            "Cannot combine invalid papers",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(malformed_frontmatter), "Research Ready"],
            "Malformed frontmatter line",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(malformed_frontmatter), "Research Ready", "--force"],
            "Malformed frontmatter line",
        )
        malformed_close_root = project / "malformed-frontmatter-close-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(malformed_close_root),
                "--project-name",
                "Loop Paper Malformed Frontmatter Close Edge",
                "--date",
                "2026-06-10",
            ]
        )
        malformed_close = create_edge_paper(malformed_close_root, "Malformed Frontmatter Close Edge")
        malformed_close.write_text(
            malformed_close.read_text(encoding="utf-8").replace("\n---\n\n# PAPER-0001", "\n---bad\n\n# PAPER-0001", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(malformed_close)],
            "Unterminated YAML frontmatter",
        )
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(malformed_close), "--phase", "before"],
            "Unterminated YAML frontmatter",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(malformed_close_root), "--strict"],
            "Unterminated YAML frontmatter",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(malformed_close_root), "--last", "1"],
            "Cannot combine invalid papers",
        )
        duplicate_frontmatter_root = project / "duplicate-frontmatter-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(duplicate_frontmatter_root),
                "--project-name",
                "Loop Paper Duplicate Frontmatter Edge",
                "--date",
                "2026-06-10",
            ]
        )
        duplicate_frontmatter = create_edge_paper(duplicate_frontmatter_root, "Duplicate Frontmatter Edge")
        duplicate_frontmatter.write_text(
            duplicate_frontmatter.read_text(encoding="utf-8").replace(
                "status: Draft",
                "status: Draft\nstatus: Accepted",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(duplicate_frontmatter)],
            "Duplicate frontmatter key: status",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(duplicate_frontmatter_root), "--strict"],
            "Duplicate frontmatter key: status",
        )
        heading_root = project / "heading-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(heading_root),
                "--project-name",
                "Loop Paper Heading Edge",
                "--date",
                "2026-06-10",
            ]
        )
        heading_mismatch = create_edge_paper(heading_root, "Heading Mismatch Edge")
        heading_mismatch.write_text(
            heading_mismatch.read_text(encoding="utf-8").replace(
                "# PAPER-0001 Heading Mismatch Edge",
                "# PAPER-9999 Heading Mismatch Edge",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(heading_mismatch)],
            "heading paper_id PAPER-9999 does not match PAPER-0001",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(heading_root), "--strict"],
            "heading paper_id PAPER-9999 does not match PAPER-0001",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(heading_root), "--last", "1"],
            "Cannot combine invalid papers",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(heading_mismatch), "Research Ready"],
            "heading paper_id PAPER-9999 does not match PAPER-0001",
        )
        title_heading_root = project / "title-heading-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(title_heading_root),
                "--project-name",
                "Loop Paper Title Heading Edge",
                "--date",
                "2026-06-10",
            ]
        )
        title_heading = create_edge_paper(title_heading_root, "Title Heading Edge")
        title_heading.write_text(
            title_heading.read_text(encoding="utf-8").replace(
                "# PAPER-0001 Title Heading Edge",
                "# PAPER-0001 Different Visible Title",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(title_heading)],
            "heading title 'Different Visible Title' does not match title frontmatter",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(title_heading), "Research Ready"],
            "heading title 'Different Visible Title' does not match title frontmatter",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(title_heading), "--check"],
            "CHANGED PAPER-0001",
        )
        run_ok([sys.executable, script("update_paper_metadata.py"), str(title_heading)])
        run_ok([sys.executable, script("check_paper.py"), str(title_heading)])
        run_ok([sys.executable, script("pipeline.py"), str(title_heading_root), "--strict"])
        run_ok([sys.executable, script("combine_papers.py"), str(title_heading_root), "--last", "1"])
        duplicate_heading_root = project / "duplicate-heading-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(duplicate_heading_root),
                "--project-name",
                "Loop Paper Duplicate Heading Edge",
                "--date",
                "2026-06-10",
            ]
        )
        duplicate_heading = create_edge_paper(duplicate_heading_root, "Duplicate Heading Edge")
        duplicate_heading.write_text(
            duplicate_heading.read_text(encoding="utf-8").replace(
                "# PAPER-0001 Duplicate Heading Edge",
                "# PAPER-0001 Duplicate Heading Edge\n\n# PAPER-0001 Duplicate Heading Edge Copy",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(duplicate_heading)],
            "Duplicate top-level paper heading",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(duplicate_heading_root), "--strict"],
            "Duplicate top-level paper heading",
        )
        duplicate_section_root = project / "duplicate-section-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(duplicate_section_root),
                "--project-name",
                "Loop Paper Duplicate Section Edge",
                "--date",
                "2026-06-10",
            ]
        )
        duplicate_section = create_edge_paper(duplicate_section_root, "Duplicate Section Edge")
        duplicate_section.write_text(
            duplicate_section.read_text(encoding="utf-8").replace(
                "## Validation\n",
                "## Validation\n\nInjected duplicate section.\n\n## Validation\n",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(duplicate_section)],
            "Duplicate section: Validation",
        )
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(duplicate_section), "--phase", "before"],
            "Duplicate section: Validation",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(duplicate_section_root), "--strict"],
            "Duplicate section: Validation",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(duplicate_section_root), "--last", "1"],
            "Cannot combine invalid papers",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(duplicate_section), "Research Ready"],
            "Duplicate section: Validation",
        )
        schema_root = project / "schema-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(schema_root),
                "--project-name",
                "Loop Paper Schema Edge",
                "--date",
                "2026-06-10",
            ]
        )
        missing_schema = create_edge_paper(schema_root, "Missing Schema Edge")
        missing_schema.write_text(
            missing_schema.read_text(encoding="utf-8").replace(
                "closed_loop_schema: paper_closed_loop.v1\n",
                "",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(missing_schema)],
            "Missing closed_loop_schema frontmatter",
        )
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(missing_schema), "--phase", "before"],
            "Missing closed_loop_schema frontmatter",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(schema_root), "--strict"],
            "Missing closed_loop_schema frontmatter",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(schema_root), "--last", "1"],
            "Cannot combine invalid papers",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(missing_schema), "Research Ready"],
            "Missing closed_loop_schema frontmatter",
        )
        invalid_schema_root = project / "invalid-schema-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(invalid_schema_root),
                "--project-name",
                "Loop Paper Invalid Schema Edge",
                "--date",
                "2026-06-10",
            ]
        )
        invalid_schema = create_edge_paper(invalid_schema_root, "Invalid Schema Edge")
        invalid_schema.write_text(
            invalid_schema.read_text(encoding="utf-8").replace(
                "closed_loop_schema: paper_closed_loop.v1",
                "closed_loop_schema: paper_closed_loop.v0",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(invalid_schema)],
            "Invalid closed_loop_schema: paper_closed_loop.v0",
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
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(malformed_numeric_filename_root),
                "--title",
                "After Malformed Filename",
                "--hypothesis",
                "Creation should reject malformed existing filenames",
                "--finding",
                "ID allocation depends on canonical filenames",
                "--reference",
                "scripts/edge_case_test.py",
                "--date",
                "2026-06-10",
            ],
            "Existing paper filename is not canonical: PAPER-0001bad.md",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(malformed_numeric_filename_root),
                "--title",
                "Review After Malformed Filename",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
                "--date",
                "2026-06-10",
            ],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        malformed_slug_filename_root = project / "malformed-slug-filename-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(malformed_slug_filename_root),
                "--project-name",
                "Loop Paper Malformed Slug Filename Edge",
                "--date",
                "2026-06-10",
            ]
        )
        malformed_slug_filename = create_edge_paper(
            malformed_slug_filename_root,
            "Malformed Slug Filename Edge",
        )
        renamed_malformed_slug_filename = malformed_slug_filename.with_name("PAPER-0001-bad--slug.md")
        malformed_slug_filename.rename(renamed_malformed_slug_filename)
        run_fail(
            [sys.executable, script("check_paper.py"), str(renamed_malformed_slug_filename)],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(malformed_slug_filename_root), "--strict"],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(malformed_slug_filename_root),
                "--title",
                "After Malformed Slug Filename",
                "--hypothesis",
                "Creation should reject malformed existing slug filenames",
                "--finding",
                "ID allocation depends on canonical filenames",
                "--reference",
                "scripts/edge_case_test.py",
                "--date",
                "2026-06-10",
            ],
            "Existing paper filename is not canonical: PAPER-0001-bad--slug.md",
        )
        missing_relationship_root = project / "missing-relationship-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(missing_relationship_root),
                "--project-name",
                "Loop Paper Missing Relationship Edge",
                "--date",
                "2026-06-10",
            ]
        )
        missing_relationship = create_edge_paper(
            missing_relationship_root,
            "Missing Relationship Edge",
        )
        missing_relationship.write_text(
            missing_relationship.read_text(encoding="utf-8").replace(
                "Extends: None\n",
                "",
                1,
            ),
            encoding="utf-8",
        )
        for command in [
            [sys.executable, script("check_paper.py"), str(missing_relationship)],
            [sys.executable, script("check_paper.py"), str(missing_relationship_root)],
            [sys.executable, script("pipeline.py"), str(missing_relationship_root), "--strict"],
            [sys.executable, script("combine_papers.py"), str(missing_relationship_root), "--last", "1"],
            [sys.executable, script("index_references.py"), str(missing_relationship_root)],
            [sys.executable, script("render_dashboard.py"), str(missing_relationship_root)],
        ]:
            run_fail(command, "Missing relationship line: Extends")
        empty_relationship_root = project / "empty-relationship-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(empty_relationship_root),
                "--project-name",
                "Loop Paper Empty Relationship Edge",
                "--date",
                "2026-06-10",
            ]
        )
        empty_relationship = create_edge_paper(empty_relationship_root, "Empty Relationship Edge")
        empty_relationship.write_text(
            empty_relationship.read_text(encoding="utf-8").replace(
                "Extends: None",
                "Extends:",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(empty_relationship)],
            "Empty relationship line: Extends",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(empty_relationship_root), "--strict"],
            "Empty relationship line: Extends",
        )
        placeholder_relationship_root = project / "placeholder-relationship-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(placeholder_relationship_root),
                "--project-name",
                "Loop Paper Placeholder Relationship Edge",
                "--date",
                "2026-06-10",
            ]
        )
        placeholder_relationship = create_edge_paper(
            placeholder_relationship_root,
            "Placeholder Relationship Edge",
        )
        placeholder_relationship.write_text(
            placeholder_relationship.read_text(encoding="utf-8").replace(
                "Extends: None",
                "Extends: TBD",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(placeholder_relationship)],
            "Invalid relationship value: Extends -> TBD",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(placeholder_relationship_root), "--last", "1"],
            "Invalid relationship value: Extends -> TBD",
        )
        mixed_none_relationship_root = project / "mixed-none-relationship-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(mixed_none_relationship_root),
                "--project-name",
                "Loop Paper Mixed None Relationship Edge",
                "--date",
                "2026-06-10",
            ]
        )
        mixed_none_relationship = create_edge_paper(
            mixed_none_relationship_root,
            "Mixed None Relationship Source",
        )
        create_edge_paper(mixed_none_relationship_root, "Mixed None Relationship Target")
        mixed_none_relationship.write_text(
            mixed_none_relationship.read_text(encoding="utf-8").replace(
                "References: None",
                "References: None, PAPER-0002",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(mixed_none_relationship_root)],
            "Relationship line mixes None with targets: References",
        )
        run_fail(
            [sys.executable, script("index_references.py"), str(mixed_none_relationship_root)],
            "Relationship line mixes None with targets: References",
        )
        prose_relationship_root = project / "prose-relationship-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(prose_relationship_root),
                "--project-name",
                "Loop Paper Prose Relationship Edge",
                "--date",
                "2026-06-10",
            ]
        )
        prose_relationship = create_edge_paper(prose_relationship_root, "Prose Relationship Source")
        create_edge_paper(prose_relationship_root, "Prose Relationship Target")
        prose_relationship.write_text(
            prose_relationship.read_text(encoding="utf-8").replace(
                "References: None",
                "References: PAPER-0002 and background notes",
                1,
            ),
            encoding="utf-8",
        )
        for command in [
            [sys.executable, script("check_paper.py"), str(prose_relationship_root)],
            [sys.executable, script("pipeline.py"), str(prose_relationship_root), "--strict"],
            [sys.executable, script("combine_papers.py"), str(prose_relationship_root), "--last", "1"],
            [sys.executable, script("render_dashboard.py"), str(prose_relationship_root)],
        ]:
            run_fail(command, "Invalid relationship value: References -> PAPER-0002 and background notes")
        duplicate_relationship_target_root = project / "duplicate-relationship-target-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(duplicate_relationship_target_root),
                "--project-name",
                "Loop Paper Duplicate Relationship Target Edge",
                "--date",
                "2026-06-10",
            ]
        )
        duplicate_relationship_target = create_edge_paper(
            duplicate_relationship_target_root,
            "Duplicate Relationship Target Source",
        )
        create_edge_paper(duplicate_relationship_target_root, "Duplicate Relationship Target")
        duplicate_relationship_target.write_text(
            duplicate_relationship_target.read_text(encoding="utf-8").replace(
                "References: None",
                "References: PAPER-0002, PAPER-0002",
                1,
            ),
            encoding="utf-8",
        )
        for command in [
            [sys.executable, script("check_paper.py"), str(duplicate_relationship_target)],
            [sys.executable, script("pipeline.py"), str(duplicate_relationship_target_root), "--strict"],
            [sys.executable, script("index_references.py"), str(duplicate_relationship_target_root)],
        ]:
            run_fail(command, "Duplicate relationship target: References -> PAPER-0002")
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
        make_before_ready_with_uppercase_checks(dangling)
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
            [sys.executable, script("check_paper.py"), str(dangling)],
            "Dangling relationship target: References -> PAPER-9999",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(dangling_root), "--strict"],
            "Dangling relationship target: References -> PAPER-9999",
        )
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(dangling),
                "--phase",
                "before",
            ],
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
            [sys.executable, script("agent_review.py"), str(dangling)],
            "Dangling relationship target: References -> PAPER-9999",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(dangling)],
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
        malformed_relationship_root = project / "malformed-relationship-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(malformed_relationship_root),
                "--project-name",
                "Loop Paper Malformed Relationship Edge",
                "--date",
                "2026-06-10",
            ]
        )
        malformed_relationship = create_edge_paper(
            malformed_relationship_root,
            "Malformed Relationship Source",
        )
        create_edge_paper(malformed_relationship_root, "Malformed Relationship Target")
        malformed_relationship.write_text(
            malformed_relationship.read_text(encoding="utf-8").replace(
                "References: None",
                "References: PAPER-0002bad",
                1,
            ),
            encoding="utf-8",
        )
        for command in [
            [sys.executable, script("check_paper.py"), str(malformed_relationship_root)],
            [sys.executable, script("pipeline.py"), str(malformed_relationship_root), "--strict"],
            [sys.executable, script("combine_papers.py"), str(malformed_relationship_root), "--last", "1"],
            [sys.executable, script("index_references.py"), str(malformed_relationship_root)],
            [sys.executable, script("render_dashboard.py"), str(malformed_relationship_root)],
        ]:
            run_fail(command, "Invalid relationship target: References -> PAPER-0002bad")
        duplicate_relationship_line_root = project / "duplicate-relationship-line-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(duplicate_relationship_line_root),
                "--project-name",
                "Loop Paper Duplicate Relationship Line Edge",
                "--date",
                "2026-06-10",
            ]
        )
        duplicate_relationship_line = create_edge_paper(
            duplicate_relationship_line_root,
            "Duplicate Relationship Line Source",
        )
        create_edge_paper(duplicate_relationship_line_root, "Duplicate Relationship Line Target")
        duplicate_relationship_line.write_text(
            duplicate_relationship_line.read_text(encoding="utf-8").replace(
                "References: None",
                "References: None\nReferences: PAPER-0002",
                1,
            ),
            encoding="utf-8",
        )
        for command in [
            [sys.executable, script("check_paper.py"), str(duplicate_relationship_line_root)],
            [sys.executable, script("render_dashboard.py"), str(duplicate_relationship_line_root)],
            [sys.executable, script("index_references.py"), str(duplicate_relationship_line_root)],
        ]:
            run_fail(command, "Duplicate relationship line: References")
        self_relation_root = project / "self-relation-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(self_relation_root),
                "--project-name",
                "Loop Paper Self Relation Edge",
                "--date",
                "2026-06-10",
            ]
        )
        self_relation = create_edge_paper(self_relation_root, "Self Relation Edge")
        self_relation.write_text(
            self_relation.read_text(encoding="utf-8").replace(
                "Depends on: None",
                "Depends on: PAPER-0001",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(self_relation_root)],
            "Self relationship target: Depends on -> PAPER-0001",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(self_relation_root), "--strict"],
            "Self relationship target: Depends on -> PAPER-0001",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(self_relation_root), "--last", "1"],
            "Self relationship target: Depends on -> PAPER-0001",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(self_relation), "Research Ready"],
            "Self relationship target: Depends on -> PAPER-0001",
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
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--ids",
                "PAPER-0001",
                "PAPER-0001",
            ],
            "Duplicate paper IDs in --ids: PAPER-0001",
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
                "PAPER-1",
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
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--from",
                "PAPER-0001",
                "--to",
                "PAPER-9999",
            ],
            "Missing interval boundary paper IDs: PAPER-9999",
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
        for extra_args in [
            ["--target-paper", "PAPER-0001"],
            ["--query", "ignored reference terms"],
        ]:
            run_fail(
                [
                    sys.executable,
                    script("combine_papers.py"),
                    str(root),
                    "--last",
                    "1",
                    "--mode",
                    "summary",
                    *extra_args,
                ],
                "Reference ranking options require --mode references or --mode both",
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
        output_ancestor_file = root / "dashboard" / "output-ancestor-file"
        output_ancestor_file.write_text("file ancestor", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--last",
                "1",
                "--output",
                str(output_ancestor_file / "nested" / "combined.md"),
            ],
            f"Expected parent directory for output, got file: {output_ancestor_file}",
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
        for command in [
            [sys.executable, script("check_paper.py"), str(papers_file_root)],
            [sys.executable, script("index_references.py"), str(papers_file_root)],
            [sys.executable, script("score_impact.py"), str(papers_file_root)],
            [sys.executable, script("export_report.py"), str(papers_file_root)],
            [sys.executable, script("pipeline.py"), str(papers_file_root), "--strict"],
            [sys.executable, script("watch_pipeline.py"), str(papers_file_root), "--once"],
            [sys.executable, script("combine_papers.py"), str(papers_file_root), "--last", "1"],
        ]:
            run_fail(command, f"Expected papers directory, got file: {papers_file}")
        stray_markdown_root = project / "stray-markdown-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(stray_markdown_root),
                "--project-name",
                "Loop Paper Stray Markdown Edge",
                "--date",
                "2026-06-10",
            ]
        )
        create_edge_paper(stray_markdown_root, "Stray Markdown Edge")
        stray_markdown = stray_markdown_root / "papers" / "notes.md"
        stray_markdown.write_text("not a paper", encoding="utf-8")
        for command in [
            [sys.executable, script("check_paper.py"), str(stray_markdown_root)],
            [sys.executable, script("index_references.py"), str(stray_markdown_root)],
            [sys.executable, script("score_impact.py"), str(stray_markdown_root)],
            [sys.executable, script("export_report.py"), str(stray_markdown_root)],
            [sys.executable, script("render_dashboard.py"), str(stray_markdown_root)],
            [sys.executable, script("pipeline.py"), str(stray_markdown_root), "--strict"],
            [sys.executable, script("watch_pipeline.py"), str(stray_markdown_root), "--once"],
            [sys.executable, script("combine_papers.py"), str(stray_markdown_root), "--last", "1"],
        ]:
            run_fail(command, "Unexpected markdown file in papers directory: notes.md")
        missing_root = project / "missing-root"
        run_fail(
            [sys.executable, script("check_paper.py"), str(missing_root)],
            f"Missing papers directory: {missing_root / 'papers'}",
        )
        for command in [
            [sys.executable, script("update_paper_metadata.py"), str(missing_root)],
            [sys.executable, script("index_references.py"), str(missing_root)],
            [sys.executable, script("score_impact.py"), str(missing_root)],
            [sys.executable, script("export_report.py"), str(missing_root)],
            [sys.executable, script("render_dashboard.py"), str(missing_root)],
            [sys.executable, script("pipeline.py"), str(missing_root), "--strict"],
            [sys.executable, script("watch_pipeline.py"), str(missing_root), "--once"],
            [sys.executable, script("combine_papers.py"), str(missing_root), "--last", "1"],
        ]:
            run_fail(command, f"Missing papers directory: {missing_root / 'papers'}")
        if missing_root.exists():
            raise SystemExit("Stack reader created a missing root unexpectedly")
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
