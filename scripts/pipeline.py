#!/usr/bin/env python3
"""Run the deterministic Paper Stack validation and dashboard pipeline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from check_closed_loop_paper import validate_paper
from paperstack_common import (
    ensure_directory,
    extract_relations,
    load_paper,
    paper_paths,
    write_text_output,
)


SCRIPT_DIR = Path(__file__).resolve().parent
CHECK = SCRIPT_DIR / "check_paper.py"
RENDER = SCRIPT_DIR / "render_dashboard.py"
METADATA = SCRIPT_DIR / "update_paper_metadata.py"
REFERENCES = SCRIPT_DIR / "index_references.py"
IMPACT = SCRIPT_DIR / "score_impact.py"
REPORT = SCRIPT_DIR / "export_report.py"
STRUCTURAL_PHASE_STATUSES = {"Draft", "Research Ready"}
BEFORE_PHASE_STATUSES = {"Plan Ready", "Implementing", "Implemented"}
AFTER_PHASE_STATUSES = {"AI Validated", "Accepted"}
GENERATED_OUTPUTS = [
    "dashboard/data.json",
    "dashboard/index.html",
    "dashboard/references.json",
    "dashboard/impact-scores.json",
    "dashboard/report.md",
]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def phase_for_status(status: str) -> str | None:
    if status in STRUCTURAL_PHASE_STATUSES:
        return "structural"
    if status in BEFORE_PHASE_STATUSES:
        return "before"
    if status in AFTER_PHASE_STATUSES:
        return "after"
    if status == "Rejected":
        return "rejected"
    return None


def generated_output_paths(root: Path) -> list[Path]:
    return [root / output for output in GENERATED_OUTPUTS]


def remove_generated_outputs(root: Path) -> None:
    for path in generated_output_paths(root):
        if path.exists() and path.is_file():
            path.unlink()


def check_closed_loop_phases(root: Path) -> tuple[bool, str, str]:
    stdout: list[str] = []
    stderr: list[str] = []
    papers = [load_paper(path) for path in paper_paths(root)]
    superseded_targets: set[str] = set()
    for paper in papers:
        superseded_targets.update(
            extract_relations(paper["text"], paper["paper_id"])["supersedes"]
        )
    for paper in papers:
        path = Path(paper["path"])
        if paper["status"] == "Superseded" and paper["paper_id"] not in superseded_targets:
            stderr.append(f"FAIL {paper['paper_id']} phase=superseded")
            stderr.append(
                f"  - Superseded without any paper declaring Supersedes: {paper['paper_id']}"
            )
            continue
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
    parser.add_argument(
        "--open",
        nargs="?",
        const="",
        default=None,
        metavar="PAPER-NNNN",
        help="Open the dashboard in a browser after a green run; optional paper ID jumps to its entry.",
    )
    args = parser.parse_args()

    root = Path(args.root)
    papers_dir = root / "papers"
    paper_count = len(paper_paths(root))
    if args.strict and paper_count == 0:
        print(f"FAIL no papers found in {papers_dir}", file=sys.stderr)
        remove_generated_outputs(root)
        summary = {
            "root": str(root),
            "paper_count": paper_count,
            "metadata_synced": False,
            "check_passed": False,
            "closed_loop_checked": False,
            "references_indexed": False,
            "impact_scored": False,
            "dashboard_rendered": False,
            "report_exported": False,
            "dashboard": str(root / "dashboard" / "index.html"),
            "report": str(root / "dashboard" / "report.md"),
            "references": str(root / "dashboard" / "references.json"),
            "impact_scores": str(root / "dashboard" / "impact-scores.json"),
        }
        summary_path = root / "dashboard" / "pipeline-summary.json"
        ensure_directory(summary_path.parent, label="dashboard directory")
        write_text_output(summary_path, json.dumps(summary, indent=2), label="pipeline summary")
        print(json.dumps(summary, indent=2))
        return 1

    gate_steps = [
        ("metadata_synced", [sys.executable, str(METADATA), str(root)]),
        ("check_passed", [sys.executable, str(CHECK), str(root), "--json"]),
    ]
    output_steps = [
        ("references_indexed", [sys.executable, str(REFERENCES), str(root)]),
        ("impact_scored", [sys.executable, str(IMPACT), str(root)]),
        ("dashboard_rendered", [sys.executable, str(RENDER), str(root)]),
        ("report_exported", [sys.executable, str(REPORT), str(root)]),
    ]

    results = {name: False for name, _command in [*gate_steps, *output_steps]}
    for name, command in gate_steps:
        completed = run(command)
        results[name] = completed.returncode == 0
        if completed.stdout:
            print(completed.stdout.strip())
        if completed.stderr:
            print(completed.stderr.strip(), file=sys.stderr)

    if all(results[name] for name, _command in gate_steps):
        closed_loop_ok, closed_loop_stdout, closed_loop_stderr = check_closed_loop_phases(root)
        results["closed_loop_checked"] = closed_loop_ok
        if closed_loop_stdout:
            print(closed_loop_stdout)
        if closed_loop_stderr:
            print(closed_loop_stderr, file=sys.stderr)
    else:
        results["closed_loop_checked"] = False
        print("SKIP closed_loop_checked: structural gate failed", file=sys.stderr)

    if results["closed_loop_checked"]:
        remove_generated_outputs(root)
        for name, command in output_steps:
            completed = run(command)
            results[name] = completed.returncode == 0
            if completed.stdout:
                print(completed.stdout.strip())
            if completed.stderr:
                print(completed.stderr.strip(), file=sys.stderr)
        if not all(results[name] for name, _command in output_steps):
            remove_generated_outputs(root)
    else:
        remove_generated_outputs(root)
        skipped = ", ".join(name for name, _command in output_steps)
        print(f"SKIP generated outputs: {skipped}", file=sys.stderr)

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
    ensure_directory(summary_path.parent, label="dashboard directory")
    write_text_output(summary_path, json.dumps(summary, indent=2), label="pipeline summary")

    print(json.dumps(summary, indent=2))
    ok = all(results.values())
    if ok and args.open is not None:
        import webbrowser

        anchor = f"#{args.open}" if args.open else ""
        webbrowser.open((root / "dashboard" / "index.html").resolve().as_uri() + anchor)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
