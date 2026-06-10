#!/usr/bin/env python3
"""Shared deterministic helpers for Paper Stack scripts."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path


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


def today() -> str:
    return dt.date.today().isoformat()


def paper_paths(root: Path) -> list[Path]:
    return sorted((root / "papers").glob("PAPER-*.md"))


def require_paper_file(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Missing paper file: {path}")
    if not path.is_file():
        raise SystemExit(f"Expected paper file, got directory: {path}")


def write_text_output(path: Path, text: str, *, label: str = "output") -> None:
    if path.exists() and path.is_dir():
        raise SystemExit(f"Expected {label} file, got directory: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def find_ids(text: str) -> list[str]:
    return sorted(set(re.findall(r"PAPER-\d{4}", text)))


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    metadata: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
    return metadata, text[end + 4 :].lstrip("\n")


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


def split_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[start:end].strip()
    return sections


def paper_id_from_path(path: Path) -> str:
    match = re.search(r"PAPER-\d{4}", path.name)
    return match.group(0) if match else path.stem


def load_paper(path: Path) -> dict:
    require_paper_file(path)
    text = path.read_text(encoding="utf-8")
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
        for match in re.finditer(rf"^{re.escape(label)}:\s*(.*)$", text, flags=re.MULTILINE):
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


def validation_not_run(sections: dict[str, str]) -> bool:
    return "not run" in sections.get("Validation", "").lower()
