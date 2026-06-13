#!/usr/bin/env python3
"""Shared deterministic helpers for Paper Stack scripts."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import time
import unicodedata
from contextlib import contextmanager
from pathlib import Path

from paper_html import (  # noqa: F401 (re-exported)
    extract_paper_source,
    read_paper_text,
    wrap_paper_source,
    write_paper_text,
)


STATUSES = [
    "Draft",
    "Research Ready",
    "Plan Ready",
    "Implementing",
    "Implemented",
    "AI Validated",
    "Accepted",
    "Rejected",
    "Superseded",
]

TERMINAL_STATUSES = {"Rejected", "Superseded"}

ALLOWED_TRANSITIONS = {
    "Draft": {"Research Ready", "Rejected", "Superseded"},
    "Research Ready": {"Plan Ready", "Draft", "Rejected", "Superseded"},
    "Plan Ready": {"Implementing", "Research Ready", "Rejected", "Superseded"},
    "Implementing": {"Implemented", "Plan Ready", "Rejected", "Superseded"},
    "Implemented": {"AI Validated", "Implementing", "Rejected", "Superseded"},
    "AI Validated": {"Accepted", "Implemented", "Rejected", "Superseded"},
    "Accepted": {"Superseded"},
    "Rejected": {"Draft", "Superseded"},
    "Superseded": set(),
}

REQUIRED_SECTIONS = [
    "Abstract",
    "Hypothesis",
    "Prior Research",
    "References",
    "Implementation Plan",
    "Validation Plan",
    "Validation",
    "Agent Review",
    "Impact Score",
]

RELATION_LABELS = ["References", "Depends on", "Supersedes", "Contradicts", "Extends"]
UNSAFE_TITLE_CHARS = re.compile(r"[:\n\r]|---")
SLUG_RE = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")
PAPER_FILENAME_RE = re.compile(r"^(PAPER-\d{4})(?:-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)?\.(?:md|html)$")
PAPER_ID_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_-])PAPER-\d{4}(?![A-Za-z0-9_-])")
MAX_PAPER_NUMBER = 9999


def today() -> str:
    return dt.date.today().isoformat()


def validate_iso_date(value: str, *, label: str = "--date") -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise SystemExit(f"{label} must be YYYY-MM-DD")
    try:
        dt.date.fromisoformat(value)
    except ValueError as error:
        raise SystemExit(f"{label} must be a valid calendar date") from error
    return value


def slugify(value: str, *, fallback: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return slug or fallback


def validate_title(title: str, *, label: str = "--title") -> str:
    cleaned = title.strip()
    if not cleaned:
        raise SystemExit(f"{label} must not be empty")
    if UNSAFE_TITLE_CHARS.search(cleaned):
        raise SystemExit(
            f"{label} must not contain ':', newlines, or '---' (would break YAML frontmatter)"
        )
    return cleaned


def validate_slug(slug: str) -> str:
    cleaned = slug.strip()
    if not SLUG_RE.fullmatch(cleaned):
        raise SystemExit("--slug must contain only ASCII letters, numbers, and single hyphens")
    return cleaned.lower()


def paper_paths(root: Path) -> list[Path]:
    papers_dir = root / "papers"
    if not papers_dir.exists():
        raise SystemExit(f"Missing papers directory: {papers_dir}")
    if papers_dir.exists() and not papers_dir.is_dir():
        raise SystemExit(f"Expected papers directory, got file: {papers_dir}")
    unexpected = [
        path.name
        for pattern in ("*.md", "*.html")
        for path in sorted(papers_dir.glob(pattern))
        if not path.name.startswith("PAPER-")
    ]
    if unexpected:
        raise SystemExit(
            "Unexpected paper file in papers directory: " + ", ".join(sorted(unexpected))
        )
    return sorted([*papers_dir.glob("PAPER-*.md"), *papers_dir.glob("PAPER-*.html")])


@contextmanager
def paper_id_lock(papers_dir: Path, *, timeout_seconds: float = 10.0):
    lock_path = papers_dir.parent / ".paper-id.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    fd: int | None = None
    while fd is None:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("ascii"))
        except FileExistsError:
            if time.monotonic() - started >= timeout_seconds:
                raise SystemExit(f"Timed out waiting for paper ID allocation lock: {lock_path}")
            time.sleep(0.05)
    try:
        yield
    finally:
        os.close(fd)
        lock_path.unlink(missing_ok=True)


def require_paper_file(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Missing paper file: {path}")
    if not path.is_file():
        raise SystemExit(f"Expected paper file, got directory: {path}")


def file_ancestor(path: Path) -> Path | None:
    for parent in reversed(path.parents):
        if parent.exists() and not parent.is_dir():
            return parent
    return None


def ensure_directory(path: Path, *, label: str = "directory") -> None:
    if path.exists() and not path.is_dir():
        raise SystemExit(f"Expected {label}, got file: {path}")
    blocked = file_ancestor(path)
    if blocked:
        raise SystemExit(f"Expected parent directory for {label}, got file: {blocked}")
    path.mkdir(parents=True, exist_ok=True)


def write_text_output(path: Path, text: str, *, label: str = "output") -> None:
    if path.exists() and path.is_dir():
        raise SystemExit(f"Expected {label} file, got directory: {path}")
    parent = path.parent
    if parent.exists() and not parent.is_dir():
        raise SystemExit(f"Expected parent directory for {label}, got file: {parent}")
    blocked = file_ancestor(parent)
    if blocked:
        raise SystemExit(f"Expected parent directory for {label}, got file: {blocked}")
    parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def refuse_papers_directory_output(root: Path, path: Path, *, label: str = "output") -> None:
    destination = path.expanduser().resolve(strict=False)
    papers_dir = (root / "papers").expanduser().resolve(strict=False)
    if destination == papers_dir or destination.is_relative_to(papers_dir):
        raise SystemExit(f"Refusing to write {label} inside papers directory: {path}")


def markdown_inline(value: object) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def markdown_table_cell(value: object) -> str:
    return markdown_inline(value).replace("|", "\\|")


def find_ids(text: str) -> list[str]:
    return sorted(set(PAPER_ID_TOKEN_RE.findall(text)))


def frontmatter_bounds(text: str) -> tuple[int, int] | None:
    if not text.startswith("---\n"):
        return None
    offset = 4
    for line in text[offset:].splitlines(keepends=True):
        line_end = offset + len(line)
        if line.strip() == "---":
            return 4, offset
        offset = line_end
    return None


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    bounds = frontmatter_bounds(text)
    if bounds is None:
        return {}, text
    start, end = bounds
    metadata: dict[str, str] = {}
    for line in text[start:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
    close_end = text.find("\n", end)
    if close_end == -1:
        return metadata, ""
    return metadata, text[close_end + 1 :].lstrip("\n")


def format_frontmatter(metadata: dict[str, str]) -> str:
    order = [
        "paper_id",
        "title",
        "status",
        "created",
        "updated",
        "owners",
        "reviewers",
        "impact_score",
        "paper_kind",
        "review_targets",
        "closed_loop_schema",
    ]
    lines = ["---"]
    seen = set()
    for key in order:
        if key in metadata:
            lines.append(f"{key}: {metadata[key]}")
            seen.add(key)
    for key in sorted(metadata):
        if key not in seen:
            lines.append(f"{key}: {metadata[key]}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def replace_frontmatter(text: str, metadata: dict[str, str]) -> str:
    _, body = parse_frontmatter(text)
    return format_frontmatter(metadata) + body


def markdown_heading_matches(text: str, level: int) -> list[tuple[str, int, int]]:
    matches: list[tuple[str, int, int]] = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    offset = 0
    heading = "#" * level
    for line in text.splitlines(keepends=True):
        line_text = line.rstrip("\r\n")
        fence_match = re.match(r"^[ \t]*(```+|~~~+)", line_text)
        if fence_match:
            marker = fence_match.group(1)
            if not in_fence:
                in_fence = True
                fence_char = marker[0]
                fence_len = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_len:
                in_fence = False
            offset += len(line)
            continue
        if not in_fence:
            match = re.match(rf"^{re.escape(heading)}\s+(.+?)\s*$", line_text)
            if match:
                matches.append(
                    (match.group(1).strip(), offset + match.start(), offset + match.end())
                )
        offset += len(line)
    return matches


def split_sections(text: str) -> dict[str, str]:
    matches = markdown_heading_matches(text, 2)
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        name, _heading_start, heading_end = match
        start = heading_end
        end = matches[index + 1][1] if index + 1 < len(matches) else len(text)
        sections[name] = text[start:end].strip()
    return sections


def paper_id_from_path(path: Path) -> str:
    match = PAPER_FILENAME_RE.fullmatch(path.name)
    return match.group(1) if match else path.stem


def next_paper_id(papers_dir: Path) -> str:
    max_id = 0
    for path in sorted([*papers_dir.glob("PAPER-*.md"), *papers_dir.glob("PAPER-*.html")]):
        match = PAPER_FILENAME_RE.fullmatch(path.name)
        if not match:
            raise SystemExit(f"Existing paper filename is not canonical: {path.name}")
        max_id = max(max_id, int(match.group(1).split("-")[1]))
    if max_id >= MAX_PAPER_NUMBER:
        raise SystemExit("Cannot allocate next paper ID beyond PAPER-9999")
    return f"PAPER-{max_id + 1:04d}"


def load_paper(path: Path) -> dict:
    require_paper_file(path)
    text = read_paper_text(path)
    metadata, body = parse_frontmatter(text)
    sections = split_sections(text)
    paper_id = metadata.get("paper_id") or paper_id_from_path(path)
    title = metadata.get("title") or path.stem
    return {
        "path": path,
        "text": text,
        "body": body,
        "metadata": metadata,
        "sections": sections,
        "paper_id": paper_id,
        "title": title,
        "status": metadata.get("status", "Draft"),
    }


def relation_key(label: str) -> str:
    return label.lower().replace(" ", "_")


def extract_relations(text: str, paper_id: str = "") -> dict[str, list[str]]:
    relations: dict[str, list[str]] = {}
    for label in RELATION_LABELS:
        ids: list[str] = []
        for match in re.finditer(rf"^{re.escape(label)}:[ \t]*(.*)$", text, flags=re.MULTILINE):
            ids.extend(find_ids(match.group(1)))
        relations[relation_key(label)] = sorted({item for item in ids if item != paper_id})
    return relations


def checked_count(text: str) -> int:
    return len(re.findall(r"- \[x\]", text, flags=re.IGNORECASE))


def unchecked_count(text: str) -> int:
    return len(re.findall(r"- \[ \]", text))


def section_has_checked(section_text: str) -> bool:
    return bool(re.search(r"- \[x\]", section_text, flags=re.IGNORECASE))


def section_has_unchecked(section_text: str) -> bool:
    return bool(re.search(r"- \[ \]", section_text))


def paper_root_from_path(path: Path) -> Path:
    if path.parent.name == "papers":
        return path.parent.parent
    return path.parent


def project_config(root: Path) -> dict:
    path = root / "config" / "loop-paper.json"
    if not path.is_file():
        return {}
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid project config JSON at {path}: {error.msg}") from error
    if not isinstance(config, dict):
        raise SystemExit(f"Project config must be a JSON object: {path}")
    return config


def paper_number(paper_id: str) -> int | None:
    match = re.fullmatch(r"PAPER-(\d{4})", paper_id)
    return int(match.group(1)) if match else None


def proposal_gate_start(root: Path) -> int | None:
    gate = project_config(root).get("proposal_gate")
    if gate is None:
        return None
    if not isinstance(gate, dict):
        raise SystemExit("proposal_gate must be a JSON object")
    required_from = gate.get("required_from")
    if not required_from:
        return None
    number = paper_number(str(required_from))
    if number is None:
        raise SystemExit(
            f"proposal_gate.required_from must be PAPER-NNNN, got {required_from!r}"
        )
    return number


def proposal_gate_applies(root: Path, paper_id: str) -> bool:
    start = proposal_gate_start(root)
    number = paper_number(paper_id)
    return start is not None and number is not None and number >= start


def validation_not_run(sections: dict[str, str]) -> bool:
    return bool(
        re.search(
            r"\bnot[-\s]+run\b",
            sections.get("Validation", ""),
            flags=re.IGNORECASE,
        )
    )
