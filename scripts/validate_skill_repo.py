#!/usr/bin/env python3
"""Validate the Loop Paper skill repository shape."""

from __future__ import annotations

import py_compile
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EXPECTED_SKILL_NAME = "loop-paper"


def fail(message: str) -> None:
    print(f"FAIL {message}")
    raise SystemExit(1)


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail(f"{path} missing YAML frontmatter")
    end = text.find("\n---", 4)
    if end == -1:
        fail(f"{path} has unterminated YAML frontmatter")
    metadata: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"')
    return metadata


def validate_skill_md() -> None:
    path = ROOT / "SKILL.md"
    if not path.exists():
        fail("missing SKILL.md")
    metadata = parse_frontmatter(path)
    if metadata.get("name") != EXPECTED_SKILL_NAME:
        fail(f"SKILL.md name must be {EXPECTED_SKILL_NAME!r}")
    if not metadata.get("description"):
        fail("SKILL.md description is required")


def validate_openai_yaml() -> None:
    path = ROOT / "agents" / "openai.yaml"
    if not path.exists():
        fail("missing agents/openai.yaml")
    text = path.read_text(encoding="utf-8")
    required = ["display_name", "short_description", "default_prompt"]
    for key in required:
        if not re.search(rf"^\s*{re.escape(key)}\s*:", text, flags=re.MULTILINE):
            fail(f"agents/openai.yaml missing {key}")


def validate_directories() -> None:
    for directory in ["agents", "assets", "references", "scripts"]:
        if not (ROOT / directory).is_dir():
            fail(f"missing {directory}/")
    nested = [
        path
        for path in ROOT.rglob("SKILL.md")
        if path != ROOT / "SKILL.md" and ".git" not in path.parts
    ]
    if nested:
        fail("nested SKILL.md files are not allowed: " + ", ".join(str(path) for path in nested))


def validate_python_scripts() -> None:
    for path in sorted((ROOT / "scripts").glob("*.py")):
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as error:
            fail(f"python compile failed for {path}: {error.msg}")


def main() -> int:
    validate_skill_md()
    validate_openai_yaml()
    validate_directories()
    validate_python_scripts()
    print(f"OK {EXPECTED_SKILL_NAME} skill repository")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
