#!/usr/bin/env python3
"""Shared deterministic helpers for Paper Stack scripts."""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import re
from pathlib import Path


STATUSES = [
    "Draft",
    "Research Ready",
    "Plan Ready",
    "Implementing",
    "Implemented",
    "AI Validated",
    "Human Review Required",
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
    "AI Validated": {"Human Review Required", "Implemented", "Rejected", "Superseded"},
    "Human Review Required": {"Accepted", "AI Validated", "Rejected", "Superseded"},
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
    "Human Review",
    "Impact Score",
]

RELATION_LABELS = ["References", "Depends on", "Supersedes", "Contradicts", "Extends"]


def today() -> str:
    return dt.date.today().isoformat()


def paper_paths(root: Path) -> list[Path]:
    return sorted((root / "papers").glob("PAPER-*.md"))


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
    order = ["paper_id", "title", "status", "created", "updated", "owners", "reviewers", "impact_score"]
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


def has_explicit_human_acceptance(sections: dict[str, str]) -> bool:
    human = sections.get("Human Review", "")
    has_decision = bool(re.search(r"Decision:\s*(Accepted|Approved)", human, flags=re.IGNORECASE))
    has_reviewer = bool(re.search(r"Human reviewer:\s*\S+", human, flags=re.IGNORECASE))
    has_date = bool(re.search(r"Review date:\s*\d{4}-\d{2}-\d{2}", human, flags=re.IGNORECASE))
    has_checked_human = bool(re.search(r"- \[x\].*human", human, flags=re.IGNORECASE))
    has_verification = bool(re.search(r"Verification:\s*password-verified:[a-f0-9]{16}", human, flags=re.IGNORECASE))
    return has_decision and has_reviewer and has_date and has_checked_human and has_verification


def paper_root_from_path(path: Path) -> Path:
    if path.parent.name == "papers":
        return path.parent.parent
    return path.parent


def reviewers_path(root: Path) -> Path:
    return root / "config" / "reviewers.json"


def load_reviewers(root: Path) -> dict:
    path = reviewers_path(root)
    if not path.exists():
        return {"reviewers": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def password_hash(password: str, salt: str, iterations: int) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations)
    return digest.hex()


def verification_token(reviewer: str, paper_id: str, review_date: str, decision: str, stored_hash: str) -> str:
    payload = f"{reviewer}|{paper_id}|{review_date}|{decision.lower()}|{stored_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def human_review_fields(sections: dict[str, str]) -> dict[str, str]:
    human = sections.get("Human Review", "")
    fields = {}
    for key in ["Human reviewer", "Review date", "Decision", "Verification"]:
        match = re.search(rf"^{re.escape(key)}:\s*(.*?)\s*$", human, flags=re.IGNORECASE | re.MULTILINE)
        fields[key.lower().replace(" ", "_")] = match.group(1).strip() if match else ""
    return fields


def verify_human_review_password(root: Path, paper: dict) -> tuple[bool, str]:
    fields = human_review_fields(paper["sections"])
    reviewer = fields.get("human_reviewer", "")
    review_date = fields.get("review_date", "")
    decision = fields.get("decision", "")
    verification = fields.get("verification", "")
    if not reviewer or not review_date or not decision or not verification:
        return False, "Human review verification fields are incomplete."
    config = load_reviewers(root)
    reviewer_config = config.get("reviewers", {}).get(reviewer)
    if not reviewer_config:
        return False, f"Reviewer {reviewer!r} is not registered."
    token = verification_token(reviewer, paper["paper_id"], review_date, decision, reviewer_config["password_hash"])
    expected = f"password-verified:{token}"
    if not hmac.compare_digest(verification, expected):
        return False, "Human review verification token does not match registered reviewer password."
    return True, "Human review password verification passed."


def validation_not_run(sections: dict[str, str]) -> bool:
    return "not run" in sections.get("Validation", "").lower()
