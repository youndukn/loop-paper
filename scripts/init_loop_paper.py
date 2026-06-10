#!/usr/bin/env python3
"""Initialize a generalizable Loop Paper project structure."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from paperstack_common import ensure_directory, validate_iso_date, write_text_output


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
STRUCTURE_TEMPLATE = SKILL_DIR / "assets" / "structure-template.md"
NEW_CLOSED_LOOP = SCRIPT_DIR / "new_closed_loop_paper.py"

DIRECTORIES = [
    "papers",
    "runs",
    "fixes",
    "references",
    "inbox",
    "dashboard",
    "config",
    "archive",
]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "loop-paper-project"


def project_name_from_root(root: Path) -> str:
    if root.name == ".paper-stack" and root.parent.name:
        return root.parent.name.replace("-", " ").replace("_", " ").title()
    return root.name.replace("-", " ").replace("_", " ").title()


def write_once(path: Path, text: str, overwrite: bool) -> bool:
    if path.exists() and path.is_dir():
        raise SystemExit(f"Expected generated file, got directory: {path}")
    if path.exists() and not overwrite:
        return False
    write_text_output(path, text, label="generated file")
    return True


def render_config(root: Path, project_name: str, today: str) -> str:
    payload = {
        "schema": "loop_paper.project.v1",
        "project_name": project_name,
        "created": today,
        "paper_root": str(root),
        "directories": DIRECTORIES,
        "paper_id_format": "PAPER-NNNN",
        "run_id_format": "RUN-YYYY-MM-DD-PAPER-NNNN-short-name",
        "fix_id_format": "FIX-YYYY-MM-DD-PAPER-NNNN-short-name",
        "relationship_empty_value": "None",
        "generated_outputs": ["dashboard/data.json", "dashboard/index.html", "dashboard/report.md"],
    }
    return json.dumps(payload, indent=2) + "\n"


def render_gitignore() -> str:
    return "\n".join(
        [
            "# Loop Paper generated/runtime files",
            "dashboard/*.tmp",
            "dashboard/watch-state.json",
            "",
        ]
    )


def create_seed_paper(args: argparse.Namespace, root: Path) -> str | None:
    if not args.seed_paper:
        return None
    command = [
        sys.executable,
        str(NEW_CLOSED_LOOP),
        "--root",
        str(root),
        "--title",
        args.seed_title or f"Initialize {args.project_name} Loop Paper",
        "--hypothesis",
        args.seed_hypothesis or "A project-local paper structure will make work loops auditable and reusable.",
        "--finding",
        "Loop Paper initialization created the project-local paper structure.",
        "--reference",
        str(root / "structure.md"),
        "--min-hypotheses",
        "1",
        "--date",
        args.date,
    ]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.strip() or completed.stdout.strip())
    return completed.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a Loop Paper project structure.")
    parser.add_argument("--root", type=Path, default=Path(".paper-stack"), help="Paper stack root to create")
    parser.add_argument("--project-name", help="Project display name for config and structure")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite generated structure/config files")
    parser.add_argument("--seed-paper", action="store_true", help="Create the first closed-loop paper")
    parser.add_argument("--seed-title", help="Title for the optional seed paper")
    parser.add_argument("--seed-hypothesis", help="Hypothesis for the optional seed paper")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    args.date = validate_iso_date(args.date)

    root = args.root
    args.project_name = args.project_name or project_name_from_root(root)
    ensure_directory(root, label="paper stack root")

    created_dirs = []
    for name in DIRECTORIES:
        path = root / name
        ensure_directory(path, label=f"{name} directory")
        created_dirs.append(str(path))

    structure_text = STRUCTURE_TEMPLATE.read_text(encoding="utf-8")
    structure_text = structure_text.replace(
        "# Loop Paper Structure",
        f"# Loop Paper Structure: {args.project_name}",
        1,
    )

    wrote = {
        "structure": write_once(root / "structure.md", structure_text, args.overwrite),
        "config": write_once(root / "config" / "loop-paper.json", render_config(root, args.project_name, args.date), args.overwrite),
        "gitignore": write_once(root / ".gitignore", render_gitignore(), args.overwrite),
    }
    seed_path = create_seed_paper(args, root)

    summary = {
        "root": str(root),
        "project_name": args.project_name,
        "directories": created_dirs,
        "written": wrote,
        "seed_paper": seed_path,
        "next_steps": [
            f"python3 {NEW_CLOSED_LOOP} --root {root} --title 'Short Work Unit Title' --hypothesis 'Falsifiable claim'",
            f"python3 {SCRIPT_DIR / 'pipeline.py'} {root}",
        ],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
