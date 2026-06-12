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

from paperstack_common import (
    PAPER_FILENAME_RE,
    ensure_directory,
    paper_paths,
    validate_iso_date,
    validate_title,
    write_text_output,
)


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
STRUCTURE_TEMPLATE = SKILL_DIR / "assets" / "structure-template.md"
GUARD_HOOK_TEMPLATE = SKILL_DIR / "assets" / "guard_paper_loop.py"
NEW_CLOSED_LOOP = SCRIPT_DIR / "new_closed_loop_paper.py"
GUARD_HOOK_MARKER = "guard_paper_loop.py"

DIRECTORIES = [
    "papers",
    "proposals",
    "runs",
    "fixes",
    "references",
    "inbox",
    "dashboard",
    "config",
    "archive",
]
UNSAFE_PROJECT_NAME_CHARS = re.compile(r"[\n\r]|---")


def project_name_from_root(root: Path) -> str:
    if root.name == ".paper-stack":
        parent = root.parent
        if str(parent) in {"", "."}:
            parent = root.resolve().parent
        if parent.name:
            return parent.name.replace("-", " ").replace("_", " ").title()
    return root.name.replace("-", " ").replace("_", " ").title()


def validate_project_name(project_name: str) -> str:
    cleaned = project_name.strip()
    if not cleaned:
        raise SystemExit("--project-name must not be empty")
    if UNSAFE_PROJECT_NAME_CHARS.search(cleaned):
        raise SystemExit("--project-name must not contain newlines or '---'")
    return cleaned


def validate_seed_title(seed_title: str) -> str:
    return validate_title(seed_title, label="--seed-title")


def seed_title_from_project_name(project_name: str) -> str:
    safe_name = re.sub(r"\s+", " ", project_name.replace(":", " - ")).strip()
    return validate_seed_title(f"Initialize {safe_name} Loop Paper")


def write_once(path: Path, text: str, overwrite: bool) -> bool:
    if path.exists() and path.is_dir():
        raise SystemExit(f"Expected generated file, got directory: {path}")
    if path.exists() and not overwrite:
        return False
    write_text_output(path, text, label="generated file")
    return True


def render_config(root: Path, project_name: str, today: str, *, seed_paper: bool = False) -> str:
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
        "proposal_gate": {"required_from": "PAPER-0002" if seed_paper else "PAPER-0001"},
        "generated_outputs": [
            "dashboard/data.json",
            "dashboard/index.html",
            "dashboard/references.json",
            "dashboard/impact-scores.json",
            "dashboard/report.md",
            "dashboard/pipeline-summary.json",
        ],
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


def install_guard_hook(root: Path, overwrite: bool) -> dict:
    hook_path = root / "hooks" / "guard_paper_loop.py"
    ensure_directory(root / "hooks", label="hooks directory")
    wrote_script = write_once(hook_path, GUARD_HOOK_TEMPLATE.read_text(encoding="utf-8"), overwrite)

    project_dir = root.parent
    settings_path = project_dir / ".claude" / "settings.json"
    command = f'python3 "$CLAUDE_PROJECT_DIR/{root.name}/hooks/guard_paper_loop.py"'

    settings: dict = {}
    if settings_path.is_file():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raise SystemExit(f"Cannot merge hook into invalid JSON: {settings_path}")
        if not isinstance(settings, dict):
            raise SystemExit(f"Expected a JSON object in {settings_path}")
    hooks = settings.setdefault("hooks", {})
    pre_tool_use = hooks.setdefault("PreToolUse", [])
    already = any(
        GUARD_HOOK_MARKER in hook.get("command", "")
        for entry in pre_tool_use
        for hook in entry.get("hooks", [])
        if isinstance(hook, dict)
    )
    if not already:
        pre_tool_use.append(
            {
                "matcher": "Write|Edit|MultiEdit|NotebookEdit",
                "hooks": [{"type": "command", "command": command}],
            }
        )
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return {
        "script": str(hook_path),
        "script_written": wrote_script,
        "settings": str(settings_path),
        "registered": not already,
    }


def create_seed_paper(args: argparse.Namespace, root: Path) -> str | None:
    if not args.seed_paper:
        return None
    existing_papers = paper_paths(root)
    noncanonical = [
        path.name for path in existing_papers if not PAPER_FILENAME_RE.fullmatch(path.name)
    ]
    if noncanonical:
        raise SystemExit(f"Existing paper filename is not canonical: {noncanonical[0]}")
    if existing_papers:
        return None
    command = [
        sys.executable,
        str(NEW_CLOSED_LOOP),
        "--root",
        str(root),
        "--title",
        args.seed_title or seed_title_from_project_name(args.project_name),
        "--hypothesis",
        args.seed_hypothesis or "A project-local paper structure will make work loops auditable and reusable.",
        "--hypothesis",
        "Initialization that fails on collisions, malformed roots, or non-canonical filenames prevents partial paper stacks from accumulating.",
        "--finding",
        "Loop Paper initialization created the project-local paper structure.",
        "--reference",
        str(root / "structure.md"),
        "--min-hypotheses",
        "2",
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
    parser.add_argument(
        "--no-claude-hook",
        action="store_true",
        help="Skip installing the Claude Code PreToolUse guard hook",
    )
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    args.date = validate_iso_date(args.date)

    root = args.root
    args.project_name = validate_project_name(args.project_name or project_name_from_root(root))
    if args.seed_title is not None:
        args.seed_title = validate_seed_title(args.seed_title)
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
        "config": write_once(root / "config" / "loop-paper.json", render_config(root, args.project_name, args.date, seed_paper=args.seed_paper), args.overwrite),
        "gitignore": write_once(root / ".gitignore", render_gitignore(), args.overwrite),
    }
    guard_hook = None if args.no_claude_hook else install_guard_hook(root, args.overwrite)
    seed_path = create_seed_paper(args, root)
    seed_skipped = bool(args.seed_paper and seed_path is None)

    summary = {
        "root": str(root),
        "project_name": args.project_name,
        "directories": created_dirs,
        "written": wrote,
        "seed_paper": seed_path,
        "seed_paper_skipped": seed_skipped,
        "claude_hook": guard_hook,
        "next_steps": [
            f"python3 {NEW_CLOSED_LOOP} --root {root} --title 'Short Work Unit Title' --hypothesis 'Falsifiable claim'",
            f"python3 {SCRIPT_DIR / 'pipeline.py'} {root}",
        ],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
