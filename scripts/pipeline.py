#!/usr/bin/env python3
"""Run the deterministic Paper Stack validation and dashboard pipeline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
CHECK = SCRIPT_DIR / "check_paper.py"
RENDER = SCRIPT_DIR / "render_dashboard.py"
METADATA = SCRIPT_DIR / "update_paper_metadata.py"
REFERENCES = SCRIPT_DIR / "index_references.py"
IMPACT = SCRIPT_DIR / "score_impact.py"
REPORT = SCRIPT_DIR / "export_report.py"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


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

    steps = [
        ("metadata_synced", [sys.executable, str(METADATA), str(root)]),
        ("references_indexed", [sys.executable, str(REFERENCES), str(root)]),
        ("impact_scored", [sys.executable, str(IMPACT), str(root)]),
        ("check_passed", [sys.executable, str(CHECK), str(root), "--json"]),
        ("dashboard_rendered", [sys.executable, str(RENDER), str(root)]),
        ("report_exported", [sys.executable, str(REPORT), str(root)]),
    ]

    results = {}
    for name, command in steps:
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
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
