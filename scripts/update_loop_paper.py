#!/usr/bin/env python3
"""Update generated Loop Paper stack assets without touching papers."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from init_loop_paper import (
    DIRECTORIES,
    GENERATED_OUTPUTS,
    GUARD_HOOK_TEMPLATE,
    install_guard_hook,
    render_gitignore,
)
from paperstack_common import (
    MAX_PAPER_NUMBER,
    ensure_directory,
    file_ancestor,
    paper_number,
    write_text_output,
)


PAPER_ID_RE = re.compile(r"^(PAPER-\d{4})")


def read_json_object(path: Path) -> dict:
    if not path.exists():
        return {}
    if path.is_dir():
        raise SystemExit(f"Expected config file, got directory: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid project config JSON at {path}: {error.msg}") from error
    if not isinstance(payload, dict):
        raise SystemExit(f"Project config must be a JSON object: {path}")
    return payload


def merged_list(existing: object, additions: list[str], *, label: str) -> list[str]:
    if existing is None:
        current: list[str] = []
    elif isinstance(existing, list) and all(isinstance(item, str) for item in existing):
        current = list(existing)
    else:
        raise SystemExit(f"Project config field {label!r} must be a list of strings")
    seen = set(current)
    for item in additions:
        if item not in seen:
            current.append(item)
            seen.add(item)
    return current


def next_paper_id(root: Path) -> str:
    papers_dir = root / "papers"
    if papers_dir.exists() and not papers_dir.is_dir():
        raise SystemExit(f"Expected papers directory, got file: {papers_dir}")
    highest = 0
    if papers_dir.exists():
        for path in sorted([*papers_dir.glob("PAPER-*.md"), *papers_dir.glob("PAPER-*.html")]):
            match = PAPER_ID_RE.match(path.name)
            if not match:
                continue
            number = paper_number(match.group(1))
            if number is not None:
                highest = max(highest, number)
    if highest >= MAX_PAPER_NUMBER:
        raise SystemExit("Cannot choose proposal gate start after PAPER-9999")
    return f"PAPER-{highest + 1:04d}"


def validate_gate_start(value: str) -> str:
    cleaned = value.strip()
    if paper_number(cleaned) is None:
        raise argparse.ArgumentTypeError("--proposal-gate-required-from must be PAPER-NNNN")
    return cleaned


def ensure_stack_root(root: Path) -> None:
    if not root.exists():
        raise SystemExit(f"Missing existing paper stack root: {root}")
    if not root.is_dir():
        raise SystemExit(f"Expected paper stack root directory, got file: {root}")


def directory_plan(root: Path) -> list[str]:
    missing = []
    for name in DIRECTORIES:
        path = root / name
        if path.exists() and not path.is_dir():
            raise SystemExit(f"Expected {name} directory, got file: {path}")
        blocked = file_ancestor(path)
        if blocked:
            raise SystemExit(f"Expected parent directory for {name} directory, got file: {blocked}")
        if not path.exists():
            missing.append(name)
    return missing


def update_directories(root: Path, *, dry_run: bool) -> list[str]:
    missing = directory_plan(root)
    if not dry_run:
        for name in missing:
            ensure_directory(root / name, label=f"{name} directory")
    return missing


def update_config(
    root: Path,
    *,
    dry_run: bool,
    proposal_gate_required_from: str | None,
    no_proposal_gate: bool,
) -> dict:
    config_path = root / "config" / "loop-paper.json"
    payload = read_json_object(config_path)
    before = json.dumps(payload, sort_keys=True)

    payload.setdefault("schema", "loop_paper.project.v1")
    payload.setdefault("project_name", root.parent.name or root.name)
    payload.setdefault("paper_root", str(root))
    payload["directories"] = merged_list(
        payload.get("directories"), DIRECTORIES, label="directories"
    )
    payload.setdefault("paper_id_format", "PAPER-NNNN")
    payload.setdefault("run_id_format", "RUN-YYYY-MM-DD-PAPER-NNNN-short-name")
    payload.setdefault("fix_id_format", "FIX-YYYY-MM-DD-PAPER-NNNN-short-name")
    payload.setdefault("relationship_empty_value", "None")
    payload["generated_outputs"] = merged_list(
        payload.get("generated_outputs"), GENERATED_OUTPUTS, label="generated_outputs"
    )

    gate = payload.get("proposal_gate")
    if proposal_gate_required_from:
        payload["proposal_gate"] = {"required_from": proposal_gate_required_from}
    elif gate is None and not no_proposal_gate:
        payload["proposal_gate"] = {
            "required_from": proposal_gate_required_from or next_paper_id(root)
        }
    elif gate is not None:
        if not isinstance(gate, dict):
            raise SystemExit("proposal_gate must be a JSON object")
        required_from = gate.get("required_from")
        if required_from and paper_number(str(required_from)) is None:
            raise SystemExit(
                f"proposal_gate.required_from must be PAPER-NNNN, got {required_from!r}"
            )

    after = json.dumps(payload, sort_keys=True)
    changed = before != after
    if changed and not dry_run:
        write_text_output(
            config_path,
            json.dumps(payload, indent=2) + "\n",
            label="project config",
        )
    return {
        "path": str(config_path),
        "updated": changed and not dry_run,
        "would_update": changed and dry_run,
        "proposal_gate": payload.get("proposal_gate"),
    }


def update_gitignore(root: Path, *, dry_run: bool) -> dict:
    path = root / ".gitignore"
    required_lines = [line for line in render_gitignore().splitlines() if line]
    if path.exists() and path.is_dir():
        raise SystemExit(f"Expected .gitignore file, got directory: {path}")
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    additions = [line for line in required_lines if line not in existing.splitlines()]
    changed = bool(additions) or not path.exists()
    if changed and not dry_run:
        if existing and not existing.endswith("\n"):
            existing += "\n"
        write_text_output(path, existing + "\n".join(additions) + "\n", label=".gitignore")
    return {
        "path": str(path),
        "updated": changed and not dry_run,
        "would_update": changed and dry_run,
    }


def hook_plan(root: Path) -> dict:
    hook_path = root / "hooks" / "guard_paper_loop.py"
    template = GUARD_HOOK_TEMPLATE.read_text(encoding="utf-8")
    current = hook_path.read_text(encoding="utf-8") if hook_path.is_file() else None
    return {
        "script": str(hook_path),
        "would_refresh_script": current != template,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update generated assets in an existing Loop Paper stack."
    )
    parser.add_argument("--root", type=Path, default=Path(".paper-stack"))
    parser.add_argument(
        "--project-dir",
        type=Path,
        help="Claude project directory for hook registration; defaults to git toplevel or root parent",
    )
    parser.add_argument(
        "--proposal-gate-required-from",
        type=validate_gate_start,
        help="Set proposal_gate.required_from explicitly, overriding any existing value",
    )
    parser.add_argument(
        "--no-proposal-gate",
        action="store_true",
        help="Do not add proposal_gate when it is missing",
    )
    parser.add_argument(
        "--no-claude-hook",
        action="store_true",
        help="Skip refreshing the project-local Claude Code guard hook",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.no_proposal_gate and args.proposal_gate_required_from:
        raise SystemExit("--no-proposal-gate conflicts with --proposal-gate-required-from")

    root = args.root
    ensure_stack_root(root)
    created_directories = update_directories(root, dry_run=args.dry_run)
    config = update_config(
        root,
        dry_run=args.dry_run,
        proposal_gate_required_from=args.proposal_gate_required_from,
        no_proposal_gate=args.no_proposal_gate,
    )
    gitignore = update_gitignore(root, dry_run=args.dry_run)
    if args.no_claude_hook:
        claude_hook = None
    elif args.dry_run:
        claude_hook = hook_plan(root)
    else:
        claude_hook = install_guard_hook(root, overwrite=True, project_dir=args.project_dir)

    print(
        json.dumps(
            {
                "root": str(root),
                "dry_run": args.dry_run,
                "created_directories": created_directories,
                "config": config,
                "gitignore": gitignore,
                "claude_hook": claude_hook,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
