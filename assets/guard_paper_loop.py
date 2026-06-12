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
import sys
from pathlib import Path

ACTIVE_STATUSES = {"Draft", "Research Ready", "Plan Ready", "Implementing"}
STATUS_RE = re.compile(r"^status:[ \t]*(.+?)[ \t]*$", flags=re.MULTILINE)


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


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    file_path = (payload.get("tool_input") or {}).get("file_path")
    if not file_path:
        return 0
    root = stack_root()
    target = Path(file_path)
    try:
        target.resolve().relative_to(root.resolve())
        return 0  # edits inside the paper stack are always allowed
    except ValueError:
        pass
    if has_active_paper(root):
        return 0
    print(
        "Blocked by loop-paper: no paper is open (Draft/Research Ready/"
        "Plan Ready/Implementing) in "
        f"{root}. Use the loop-paper skill: research findings, then "
        "scripts/propose_paper.py for human selection, before editing code.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
