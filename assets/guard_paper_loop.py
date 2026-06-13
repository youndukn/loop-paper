#!/usr/bin/env python3
"""Claude Code PreToolUse hook: block file edits unless a paper loop is open.

Installed by init_loop_paper.py into <stack>/hooks/ and registered in the
project's .claude/settings.json. Reads the PreToolUse JSON payload on stdin.
Exit 0 allows the tool call; exit 2 blocks it and feeds stderr back to the
agent. Self-contained on purpose: no imports from the skill's scripts/.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

ACTIVE_STATUSES = {"Draft", "Research Ready", "Plan Ready", "Implementing"}
STATUS_RE = re.compile(r"^status:[ \t]*(.+?)[ \t]*$", flags=re.MULTILINE)
PYTHON_OPEN_WRITE_RE = re.compile(
    r"open\(\s*['\"]([^'\"]+)['\"].{0,120}?['\"](?:w|a|x)",
    flags=re.DOTALL,
)


def stack_root() -> Path:
    return Path(__file__).resolve().parent.parent


def has_active_paper(root: Path) -> bool:
    papers = root / "papers"
    if not papers.is_dir():
        return False
    for path in sorted([*papers.glob("PAPER-*.md"), *papers.glob("PAPER-*.html")]):
        match = STATUS_RE.search(path.read_text(encoding="utf-8", errors="replace"))
        if match and match.group(1) in ACTIVE_STATUSES:
            return True
    return False


def project_root(root: Path) -> Path:
    raw = None
    try:
        import os

        raw = os.environ.get("CLAUDE_PROJECT_DIR")
    except Exception:
        raw = None
    if raw:
        return Path(raw).expanduser().resolve(strict=False)
    return root.parent.resolve(strict=False)


def resolve_target(raw: str, project_dir: Path) -> Path:
    target = Path(raw.strip().strip("\"'")).expanduser()
    if not target.is_absolute():
        target = project_dir / target
    return target.resolve(strict=False)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def is_protected_stack_artifact(root: Path, target: Path) -> bool:
    try:
        relative = target.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    parts = relative.parts
    if len(parts) == 2 and parts[0] == "config" and parts[1] == "loop-paper.json":
        return True
    if len(parts) == 2 and parts[0] == "proposals" and parts[1].endswith(".json"):
        return True
    if len(parts) == 2 and parts[0] == "runs" and parts[1].endswith(".md"):
        return True
    if len(parts) == 2 and parts[0] == "papers" and re.fullmatch(
        r"PAPER-\d{4}(?:-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)?\.(?:md|html)",
        parts[1],
    ):
        return True
    return False


def block(root: Path, reason: str) -> int:
    print(
        f"Blocked by loop-paper: {reason} in {root}. Use the loop-paper skill: "
        "research findings, then scripts/propose_paper.py for human selection, "
        "before editing code.",
        file=sys.stderr,
    )
    return 2


def path_decision(root: Path, project_dir: Path, target: Path, *, active: bool) -> int:
    if is_relative_to(target, root):
        if is_protected_stack_artifact(root, target) and not active:
            return block(root, "protected paper-stack artifact edit while no paper is open")
        return 0
    if is_relative_to(target, project_dir):
        if active:
            return 0
        return block(root, "no paper is open (Draft/Research Ready/Plan Ready/Implementing)")
    return 0


def bash_write_targets(command: str) -> list[str]:
    targets: list[str] = []
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    for index, token in enumerate(tokens):
        if token in {">", ">>"} and index + 1 < len(tokens):
            targets.append(tokens[index + 1])
        elif token.startswith(">>") and len(token) > 2:
            targets.append(token[2:])
        elif token.startswith(">") and len(token) > 1:
            targets.append(token[1:])
        elif token in {"tee", "/usr/bin/tee"}:
            for candidate in tokens[index + 1 :]:
                if not candidate.startswith("-"):
                    targets.append(candidate)
                    break
        elif Path(token).name in {"cp", "mv"} and len(tokens) > index + 2:
            targets.append(tokens[-1])
        elif Path(token).name == "sed" and any(item.startswith("-i") for item in tokens[index + 1 :]):
            for candidate in reversed(tokens[index + 1 :]):
                if not candidate.startswith("-"):
                    targets.append(candidate)
                    break
    targets.extend(match.group(1) for match in PYTHON_OPEN_WRITE_RE.finditer(command))
    return [target for target in targets if target and target not in {"/dev/null", "NUL"}]


def main() -> int:
    payload = json.load(sys.stdin)
    tool_input = payload.get("tool_input") or {}
    root = stack_root()
    project_dir = project_root(root)
    active = has_active_paper(root)

    raw_target = tool_input.get("file_path") or tool_input.get("notebook_path")
    if raw_target:
        return path_decision(root, project_dir, resolve_target(str(raw_target), project_dir), active=active)

    command = tool_input.get("command")
    if command:
        for raw in bash_write_targets(str(command)):
            decision = path_decision(root, project_dir, resolve_target(raw, project_dir), active=active)
            if decision != 0:
                return decision
        return 0
    return 0


def fail_closed_main() -> int:
    try:
        return main()
    except Exception as error:
        root = stack_root()
        print(
            f"Blocked by loop-paper: guard hook failed closed in {root}: "
            f"{type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(fail_closed_main())
