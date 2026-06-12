#!/usr/bin/env python3
"""Shared multiple-choice prompt rendering and answer loading.

Questions are dicts with: id, field, prompt, options, and optionally
target (review papers) and header (display label for AskUserQuestion).
"""

from __future__ import annotations

import json
from pathlib import Path


CLAUDE_LABEL_MAX = 64


def render_cli(questions: list[dict], kind: str) -> str:
    lines: list[str] = []
    for index, question in enumerate(questions, start=1):
        lines.append(f"[Q{index}] {question['prompt']}")
        lines.append(f"  answer_id: {question['id']}")
        for choice_index, option in enumerate(question["options"], start=1):
            lines.append(f"  {choice_index}) {option}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_json(questions: list[dict], kind: str) -> str:
    return json.dumps({"questions": questions}, indent=2) + "\n"


def claude_label(option: str) -> str:
    if len(option) <= CLAUDE_LABEL_MAX:
        return option
    return option[: CLAUDE_LABEL_MAX - 3] + "..."


def render_claude(questions: list[dict], kind: str) -> str:
    rendered = []
    for question in questions:
        entry = {
            "question": question["prompt"] + "?",
            "header": question.get("header") or question["field"][:12],
            "id": question["id"],
            "field": question["field"],
            "multiSelect": False,
            "options": [
                {"label": claude_label(option), "description": option}
                for option in question["options"]
            ],
        }
        if question.get("target") is not None:
            entry["target"] = question["target"]
        rendered.append(entry)
    return json.dumps({"questions": rendered}, indent=2) + "\n"


def render_codex(questions: list[dict], kind: str) -> str:
    lines = [f":::interactive {kind}"]
    for index, question in enumerate(questions, start=1):
        lines.append(f"[Q{index}] {question['prompt']} [answer_id: {question['id']}]")
        for choice_index, option in enumerate(question["options"], start=1):
            lines.append(f"  ({choice_index}) {option}")
    lines.append(":::end")
    return "\n".join(lines) + "\n"


def render_pi(questions: list[dict], kind: str) -> str:
    lines = [f"# {kind} prompts"]
    for question in questions:
        lines.append(f"- id: {question['id']}")
        lines.append(f"  field: {question['field']}")
        if question.get("target"):
            lines.append(f"  target: {question['target']}")
        lines.append(f"  prompt: {question['prompt']}")
        lines.append("  options:")
        for option in question["options"]:
            lines.append(f"    - {option}")
    return "\n".join(lines) + "\n"


RENDERERS = {
    "cli": render_cli,
    "json": render_json,
    "claude": render_claude,
    "codex": render_codex,
    "pi": render_pi,
}


def render_prompts(questions: list[dict], fmt: str, *, kind: str) -> str:
    return RENDERERS[fmt](questions, kind)


def collect_cli(questions: list[dict]) -> dict:
    answers: dict[str, str] = {}
    for index, question in enumerate(questions, start=1):
        print(f"[Q{index}] {question['prompt']}")
        for choice_index, option in enumerate(question["options"], start=1):
            print(f"  {choice_index}) {option}")
        while True:
            choice = input("Enter number: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(question["options"]):
                answers[question["id"]] = question["options"][int(choice) - 1]
                break
            print(f"Pick 1..{len(question['options'])}.")
        print()
    return answers


def load_answers(path: Path, questions: list[dict], *, extra_keys: tuple[str, ...] = ()) -> dict:
    if not path.exists():
        raise SystemExit(f"Missing answers JSON file: {path}")
    if not path.is_file():
        raise SystemExit(f"Expected answers JSON file, got directory: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"answers JSON is invalid: {error.msg}") from error
    if isinstance(raw, list):
        normalized = {}
        for item in raw:
            if not isinstance(item, dict) or "id" not in item or "answer" not in item:
                raise SystemExit("answers list items must be objects with id and answer")
            if item["id"] in normalized:
                raise SystemExit(f"duplicate answer id: {item['id']}")
            normalized[item["id"]] = item["answer"]
        raw = normalized
    if not isinstance(raw, dict):
        raise SystemExit("answers JSON must be an object or list of {id, answer}")
    expected_ids = {question["id"] for question in questions} | set(extra_keys)
    unknown_ids = sorted(str(answer_id) for answer_id in raw if answer_id not in expected_ids)
    if unknown_ids:
        raise SystemExit(f"answers contain unknown ids: {', '.join(unknown_ids)}")
    answers: dict[str, str] = {}
    for question in questions:
        if question["id"] not in raw:
            raise SystemExit(f"answers missing for {question['id']}")
        if raw[question["id"]] not in question["options"]:
            raise SystemExit(f"answer for {question['id']} not in options: {raw[question['id']]}")
        answers[question["id"]] = raw[question["id"]]
    for key in extra_keys:
        if isinstance(raw.get(key), str) and raw[key].strip():
            answers[key] = raw[key].strip()
    return answers
