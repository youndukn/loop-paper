#!/usr/bin/env python3
"""Validate the Loop Paper skill repository shape."""

from __future__ import annotations

import py_compile
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EXPECTED_SKILL_NAME = "loop-paper"
SKILL_RESOURCE_RE = re.compile(r"^- `([^`]+)`: ", flags=re.MULTILINE)


def fail(message: str) -> None:
    print(f"FAIL {message}")
    raise SystemExit(1)


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail(f"{path} missing YAML frontmatter")
    end = None
    offset = 4
    for line in text[offset:].splitlines(keepends=True):
        if line.strip() == "---":
            end = offset
            break
        offset += len(line)
    if end is None:
        fail(f"{path} has unterminated YAML frontmatter")
    metadata: dict[str, str] = {}
    for index, line in enumerate(text[4:end].splitlines(), start=1):
        if not line.strip():
            continue
        if ":" not in line:
            fail(f"{path} malformed frontmatter line {index}: missing ':'")
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            fail(f"{path} malformed frontmatter line {index}: empty key")
        if key in metadata:
            fail(f"{path} duplicate frontmatter key: {key}")
        metadata[key] = value.strip().strip('"')
    return metadata


def is_git_root() -> bool:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return False
    return Path(completed.stdout.strip()).resolve() == ROOT


def validate_skill_md() -> None:
    path = ROOT / "SKILL.md"
    if not path.exists():
        fail("missing SKILL.md")
    metadata = parse_frontmatter(path)
    if metadata.get("name") != EXPECTED_SKILL_NAME:
        fail(f"SKILL.md name must be {EXPECTED_SKILL_NAME!r}")
    if not metadata.get("description"):
        fail("SKILL.md description is required")


def validate_skill_resources() -> None:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"^## Resources\n(?P<body>.*?)(?:\n## |\Z)", text, flags=re.MULTILINE | re.DOTALL)
    if not match:
        fail("SKILL.md missing Resources section")

    resources = SKILL_RESOURCE_RE.findall(match.group("body"))
    if not resources:
        fail("SKILL.md Resources section does not list any bundled resources")

    for resource in resources:
        path = ROOT / resource
        if not path.exists():
            fail(f"SKILL.md references missing resource: {resource}")

    resource_set = set(resources)
    missing_scripts = [
        str(path.relative_to(ROOT))
        for path in sorted((ROOT / "scripts").glob("*.py"))
        if str(path.relative_to(ROOT)) not in resource_set
    ]
    if missing_scripts:
        fail("SKILL.md Resources missing shipped scripts: " + ", ".join(missing_scripts))


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
    for directory in ["agents", "assets", "docs", "references", "scripts"]:
        if not (ROOT / directory).is_dir():
            fail(f"missing {directory}/")
    if not (ROOT / "docs" / "install.md").exists():
        fail("missing docs/install.md")
    nested = [
        path
        for path in tracked_files()
        if path.name == "SKILL.md" and path != ROOT / "SKILL.md"
    ]
    if nested:
        fail("nested SKILL.md files are not allowed: " + ", ".join(str(path) for path in nested))


def tracked_files() -> list[Path]:
    if not is_git_root():
        return filesystem_payload_files()

    completed = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0:
        return [ROOT / line for line in completed.stdout.splitlines() if line]

    return filesystem_payload_files()


def filesystem_payload_files() -> list[Path]:
    ignored_parts = {".git", "__pycache__", ".paper-stack"}
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file() and not any(part in ignored_parts for part in path.relative_to(ROOT).parts)
    )


def validate_retired_review_gate_absent() -> None:
    retired_paths = [
        "scripts/" + "human" + "_review.py",
        "scripts/" + "set_review" + "_password.py",
        "scripts/" + "validate_human" + "_gate.py",
        "scripts/" + "new_paper.py",
        "assets/" + "paper-template.md",
    ]
    for retired_path in retired_paths:
        if (ROOT / retired_path).exists():
            fail(f"retired workflow file is present: {retired_path}")

    retired_terms = [
        "review" + "_required",
        "Human Review" + " Required",
        "human" + "_review",
        "set_review" + "_password",
        "validate_human" + "_gate",
        "review" + "_secret",
        "password-" + "verified",
        "human-" + "only",
        "mark_" + "important",
        "--" + "important",
        "## " + "Human Review",
        "has_explicit_" + "human_acceptance",
        "verify_human_" + "review_password",
        "PaperStack" + "ConfigError",
        "DEFAULT_" + "REVIEW_REQUIRED",
        "REVIEW_REQUIRED" + "_VALUES",
        "ensure_" + "review" + "_secret",
    ]
    for path in tracked_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(ROOT)
        for term in retired_terms:
            if term in text:
                fail(f"retired review-gate term {term!r} found in {relative}")


def validate_ci_runs_core_checks() -> None:
    path = ROOT / ".github" / "workflows" / "ci.yml"
    if not path.exists():
        if is_git_root():
            fail("missing .github/workflows/ci.yml")
        return

    text = path.read_text(encoding="utf-8")
    required = [
        "scripts/validate_skill_repo.py",
        "scripts/smoke_test.py",
        "scripts/edge_case_test.py",
        "scripts/install_skill.py --agent all",
    ]
    for item in required:
        if item not in text:
            fail(f"CI does not run required check: {item}")


def validate_docs_reference_smoke_test() -> None:
    path = ROOT / "docs" / "install.md"
    text = path.read_text(encoding="utf-8")
    if "scripts/smoke_test.py" not in text:
        fail("docs/install.md must document scripts/smoke_test.py validation")
    if "scripts/edge_case_test.py" not in text:
        fail("docs/install.md must document scripts/edge_case_test.py validation")


def validate_docs_describe_pipeline_gates() -> None:
    required = [
        (ROOT / "SKILL.md", ["phase gates", "`Plan Ready`, `Implementing`, or", "`AI Validated` or"]),
        (ROOT / "README.md", ["pipeline gate", "`Plan Ready` through `Implemented`", "`AI Validated`/`Accepted`"]),
        (ROOT / "references" / "paper-states.md", ["--phase before", "--phase after", "`pipeline.py` passes"]),
    ]
    for path, phrases in required:
        text = path.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase not in text:
                fail(f"{path.relative_to(ROOT)} must document pipeline gates with {phrase!r}")


def validate_docs_describe_combine_boundaries() -> None:
    required = [
        (ROOT / "SKILL.md", ["explicit `--from`/`--to`", "must both exist in the stack"]),
        (ROOT / "README.md", ["Explicit `--from`/`--to` boundaries", "must both exist in the stack"]),
    ]
    for path, phrases in required:
        text = path.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase not in text:
                fail(f"{path.relative_to(ROOT)} must document combine interval boundaries with {phrase!r}")


def validate_python_scripts() -> None:
    for path in sorted((ROOT / "scripts").glob("*.py")):
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as error:
            fail(f"python compile failed for {path}: {error.msg}")


def main() -> int:
    validate_skill_md()
    validate_skill_resources()
    validate_openai_yaml()
    validate_directories()
    validate_retired_review_gate_absent()
    validate_ci_runs_core_checks()
    validate_docs_reference_smoke_test()
    validate_docs_describe_pipeline_gates()
    validate_docs_describe_combine_boundaries()
    validate_python_scripts()
    print(f"OK {EXPECTED_SKILL_NAME} skill repository")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
