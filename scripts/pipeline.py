#!/usr/bin/env python3
"""Run the deterministic Paper Stack validation and dashboard pipeline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from check_closed_loop_paper import validate_paper
from paperstack_common import load_paper, paper_paths, write_text_output


SCRIPT_DIR = Path(__file__).resolve().parent
CHECK = SCRIPT_DIR / "check_paper.py"
RENDER = SCRIPT_DIR / "render_dashboard.py"
METADATA = SCRIPT_DIR / "update_paper_metadata.py"
REFERENCES = SCRIPT_DIR / "index_references.py"
IMPACT = SCRIPT_DIR / "score_impact.py"
REPORT = SCRIPT_DIR / "export_report.py"
BEFORE_PHASE_STATUSES = {"Plan Ready", "Implementing", "Implemented"}
AFTER_PHASE_STATUSES = {"AI Validated", "Accepted"}


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def phase_for_status(status: str) -> str | None:
    if status in BEFORE_PHASE_STATUSES:
        return "before"
    if status in AFTER_PHASE_STATUSES:
        return "after"
    return None


def check_closed_loop_phases(root: Path) -> tuple[bool, str, str]:
    stdout: list[str] = []
    stderr: list[str] = []
    for path in paper_paths(root):
        paper = load_paper(path)
        phase = phase_for_status(paper["status"])
        if phase is None:
            continue
        errors = validate_paper(path, phase)
        if errors:
            stderr.append(f"FAIL {paper['paper_id']} phase={phase}")
            stderr.extend(f"  - {error}" for error in errors)
        else:
            stdout.append(f"OK {paper['paper_id']} phase={phase}")
    if not stdout and not stderr:
        stdout.append("OK no advanced closed-loop phase checks required")
    return not stderr, "\n".join(stdout), "\n".join(stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Paper Stack check + dashboard pipeline.")
    parser.add_argument("root", nargs="?", default=".paper-stack", help="Paper Stack root directory")
    parser.add_argument("--strict", action="store_true", help="Fail when there are no papers")
    args = parser.parse_args()

    root = Path(args.root)
    papers_dir = root / "papers"
    paper_count = len(list(papers_dir.glob("PAPER-*.md"))) if papers_dir.exists() else 0
    if args.strict and paper_count == 0:
        print(f"FAIL no papers found in {papers_dir}", file=sys.stderr)
        return 1

    pre_steps = [
        ("metadata_synced", [sys.executable, str(METADATA), str(root)]),
        ("references_indexed", [sys.executable, str(REFERENCES), str(root)]),
        ("impact_scored", [sys.executable, str(IMPACT), str(root)]),
        ("check_passed", [sys.executable, str(CHECK), str(root), "--json"]),
    ]
    post_steps = [
        ("dashboard_rendered", [sys.executable, str(RENDER), str(root)]),
        ("report_exported", [sys.executable, str(REPORT), str(root)]),
    ]

    results = {}
    for name, command in pre_steps:
        completed = run(command)
        results[name] = completed.returncode == 0
        if completed.stdout:
            print(completed.stdout.strip())
        if completed.stderr:
            print(completed.stderr.strip(), file=sys.stderr)

    closed_loop_ok, closed_loop_stdout, closed_loop_stderr = check_closed_loop_phases(root)
    results["closed_loop_checked"] = closed_loop_ok
    if closed_loop_stdout:
        print(closed_loop_stdout)
    if closed_loop_stderr:
        print(closed_loop_stderr, file=sys.stderr)

    for name, command in post_steps:
        completed = run(command)
        results[name] = completed.returncode == 0
        if completed.stdout:
            print(completed.stdout.strip())
        if completed.stderr:
            print(completed.stderr.strip(), file=sys.stderr)

    summary = {
        "root": str(root),
        "paper_count": paper_count,
        **results,
        "dashboard": str(root / "dashboard" / "index.html"),
        "report": str(root / "dashboard" / "report.md"),
        "references": str(root / "dashboard" / "references.json"),
        "impact_scores": str(root / "dashboard" / "impact-scores.json"),
    }
    summary_path = root / "dashboard" / "pipeline-summary.json"
    if summary_path.parent.exists():
        write_text_output(summary_path, json.dumps(summary, indent=2), label="pipeline summary")

    print(json.dumps(summary, indent=2))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
