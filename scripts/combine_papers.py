#!/usr/bin/env python3
"""Combine Paper Stack papers deterministically by numeric ID intervals."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from check_paper import check_paths
from paperstack_common import RELATION_LABELS, extract_relations, load_paper, paper_paths, relation_key, write_text_output


PAPER_ID_RE = re.compile(r"PAPER-(\d{4})", re.IGNORECASE)

STATUS_SCORE = {
    "Accepted": 70,
    "AI Validated": 45,
    "Implemented": 35,
    "Implementing": 25,
    "Plan Ready": 18,
    "Research Ready": 14,
    "Draft": 8,
    "Superseded": -8,
    "Rejected": -20,
}

RELATION_SCORE = {
    "depends_on": 120,
    "references": 95,
    "extends": 80,
    "supersedes": 45,
    "contradicts": 30,
}

STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "agent",
    "before",
    "between",
    "could",
    "from",
    "have",
    "into",
    "paper",
    "papers",
    "should",
    "that",
    "their",
    "there",
    "this",
    "through",
    "validation",
    "when",
    "where",
    "with",
    "would",
}


def normalize_paper_id(value: str) -> str:
    match = PAPER_ID_RE.fullmatch(value.strip())
    if not match or int(match.group(1)) <= 0:
        raise argparse.ArgumentTypeError(f"Expected PAPER-NNNN, got {value!r}")
    return f"PAPER-{int(match.group(1)):04d}"


def paper_number(paper_id: str) -> int:
    return int(normalize_paper_id(paper_id).split("-")[1])


def paper_sort_key(paper: dict) -> tuple[int, str]:
    return (paper_number(paper["paper_id"]), str(paper["path"]))


def clean_text(value: str) -> str:
    value = re.sub(r"```[\s\S]*?```", " ", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"^- \[[ xX]\]\s*", "", value, flags=re.MULTILINE)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def excerpt(value: str, limit: int = 320) -> str:
    text = clean_text(value)
    if not text:
        return "None recorded."
    if len(text) <= limit:
        return text
    cut = text.rfind(" ", 0, limit)
    if cut < int(limit * 0.65):
        cut = limit
    return text[:cut].rstrip() + "..."


def cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def searchable_text(paper: dict) -> str:
    sections = paper["sections"]
    return " ".join(
        [
            paper["paper_id"],
            paper["title"],
            sections.get("Abstract", ""),
            sections.get("Hypothesis", ""),
            sections.get("Prior Research", ""),
            sections.get("Validation", ""),
            sections.get("Impact Score", ""),
        ]
    )


def terms(value: str) -> set[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", value.lower())
    return {token for token in tokens if token not in STOPWORDS and not token.startswith("paper-")}


def status_counts(papers: list[dict]) -> Counter:
    return Counter(paper["status"] for paper in papers)


def relation_summary(paper: dict) -> str:
    relations = extract_relations(paper["text"], paper["paper_id"])
    parts = []
    for label in RELATION_LABELS:
        key = relation_key(label)
        if relations[key]:
            parts.append(f"{label}: {', '.join(relations[key])}")
    return "; ".join(parts) if parts else "None"


def load_all(root: Path) -> list[dict]:
    return sorted((load_paper(path) for path in paper_paths(root)), key=paper_sort_key)


def validate_stack(root: Path) -> None:
    failures = []
    for result in check_paths(paper_paths(root), validate_relationships=True):
        if not result["ok"]:
            details = []
            for key in ("missing_sections", "empty_sections", "warnings"):
                details.extend(result[key])
            failures.append(f"{result['paper_id']} {result['path']}: {'; '.join(details)}")
    if failures:
        raise SystemExit("Cannot combine invalid papers:\n" + "\n".join(failures))


def validate_reference_target(target_id: str | None, all_papers: list[dict]) -> None:
    if target_id is None:
        return
    known_ids = {paper["paper_id"] for paper in all_papers}
    if target_id not in known_ids:
        raise SystemExit(f"Missing target paper ID for reference ranking: {target_id}")


def selection_mode_count(args: argparse.Namespace) -> int:
    explicit_ids = bool(args.ids)
    interval = bool(args.from_id or args.to_id)
    recent = args.last is not None
    return sum([explicit_ids, interval, recent])


def select_papers(args: argparse.Namespace, papers: list[dict]) -> list[dict]:
    modes = selection_mode_count(args)
    if modes != 1:
        raise SystemExit("Choose exactly one selection mode: --from/--to, --ids, or --last.")

    by_id = {paper["paper_id"]: paper for paper in papers}
    if args.ids:
        duplicates = sorted(
            paper_id
            for paper_id, count in Counter(args.ids).items()
            if count > 1
        )
        if duplicates:
            raise SystemExit(f"Duplicate paper IDs in --ids: {', '.join(duplicates)}")
        missing = [paper_id for paper_id in args.ids if paper_id not in by_id]
        if missing:
            raise SystemExit(f"Missing paper IDs: {', '.join(missing)}")
        selected = [by_id[paper_id] for paper_id in sorted(args.ids, key=paper_number)]
    elif args.last is not None:
        if args.last < 1:
            raise SystemExit("--last must be greater than zero.")
        selected = papers[-args.last :]
    else:
        if not args.from_id or not args.to_id:
            raise SystemExit("Interval selection requires both --from and --to.")
        start = paper_number(args.from_id)
        end = paper_number(args.to_id)
        if start > end:
            raise SystemExit("--from must be less than or equal to --to.")
        missing_boundaries = [
            paper_id
            for paper_id in (args.from_id, args.to_id)
            if paper_id not in by_id
        ]
        if missing_boundaries:
            raise SystemExit(
                "Missing interval boundary paper IDs: " + ", ".join(missing_boundaries)
            )
        selected = [paper for paper in papers if start <= paper_number(paper["paper_id"]) <= end]

    if not selected:
        raise SystemExit("No papers matched the deterministic selection.")
    return sorted(selected, key=paper_sort_key)


def chunk_papers(papers: list[dict], interval_size: int) -> list[list[dict]]:
    if interval_size < 0:
        raise SystemExit("--interval-size cannot be negative.")
    if interval_size in (0, None):
        return [papers]
    if interval_size < 1:
        raise SystemExit("--interval-size must be zero or greater than zero.")
    return [papers[index : index + interval_size] for index in range(0, len(papers), interval_size)]


def build_graph(papers: list[dict]) -> tuple[Counter, dict[str, dict[str, list[str]]]]:
    inbound: Counter = Counter()
    outbound: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for paper in papers:
        relations = extract_relations(paper["text"], paper["paper_id"])
        for label in RELATION_LABELS:
            key = relation_key(label)
            for target in relations[key]:
                inbound[target] += 1
                outbound[paper["paper_id"]][target].append(key)
    return inbound, outbound


def rank_references(
    *,
    selected: list[dict],
    all_papers: list[dict],
    target_id: str | None,
    query: str,
    max_references: int,
) -> list[dict]:
    inbound, outbound = build_graph(all_papers)
    by_id = {paper["paper_id"]: paper for paper in all_papers}
    target_paper = by_id.get(target_id or "")
    target_num = paper_number(target_id) if target_id else None
    query_text = query
    if target_paper:
        query_text += " " + searchable_text(target_paper)
    query_terms = terms(query_text)

    ranked = []
    for paper in selected:
        paper_id = paper["paper_id"]
        if target_id and paper_id == target_id:
            continue

        score = 0
        reasons = []

        status_score = STATUS_SCORE.get(paper["status"], 0)
        score += status_score
        reasons.append(f"status={paper['status']} {status_score:+d}")

        inbound_score = min(40, inbound[paper_id] * 4)
        if inbound_score:
            score += inbound_score
            reasons.append(f"inbound={inbound[paper_id]} {inbound_score:+d}")

        if target_num is not None:
            distance = abs(paper_number(paper_id) - target_num)
            distance_score = max(0, 30 - distance)
            if distance_score:
                score += distance_score
                reasons.append(f"distance={distance} {distance_score:+d}")

        if target_id:
            for relation in outbound.get(target_id, {}).get(paper_id, []):
                relation_score = RELATION_SCORE.get(relation, 0)
                score += relation_score
                reasons.append(f"target->{relation} {relation_score:+d}")
            for relation in outbound.get(paper_id, {}).get(target_id, []):
                relation_score = int(RELATION_SCORE.get(relation, 0) * 0.6)
                score += relation_score
                reasons.append(f"candidate->{relation} {relation_score:+d}")

        if query_terms:
            overlap = len(query_terms & terms(searchable_text(paper)))
            overlap_score = min(35, overlap * 3)
            if overlap_score:
                score += overlap_score
                reasons.append(f"term_overlap={overlap} {overlap_score:+d}")

        ranked.append(
            {
                "paper_id": paper_id,
                "title": paper["title"],
                "status": paper["status"],
                "path": str(paper["path"]),
                "score": score,
                "reasons": reasons,
                "distance": abs(paper_number(paper_id) - target_num) if target_num is not None else 0,
            }
        )

    ranked.sort(key=lambda item: (-item["score"], item["distance"], paper_number(item["paper_id"]), item["title"]))
    return ranked[:max_references]


def render_summary(root: Path, selected: list[dict], chunks: list[list[dict]]) -> list[str]:
    first = selected[0]["paper_id"]
    last = selected[-1]["paper_id"]
    lines = [
        f"# Combined Paper Interval: {first}..{last}",
        "",
        "## Selection",
        "",
        f"- Root: `{root}`",
        f"- Paper count: {len(selected)}",
        f"- Numeric order: {', '.join(paper['paper_id'] for paper in selected)}",
        "",
        "## Status Counts",
        "",
        "| Status | Count |",
        "| --- | ---: |",
    ]
    for status, count in sorted(status_counts(selected).items()):
        lines.append(f"| {cell(status)} | {count} |")

    lines.extend(["", "## Deterministic Intervals", ""])
    for index, chunk in enumerate(chunks, start=1):
        counts = ", ".join(f"{status}: {count}" for status, count in sorted(status_counts(chunk).items()))
        lines.append(f"### Interval {index}: {chunk[0]['paper_id']}..{chunk[-1]['paper_id']}")
        lines.append("")
        lines.append(f"- Papers: {len(chunk)}")
        lines.append(f"- Statuses: {counts or 'None'}")
        lines.append("")

    lines.extend(["## Paper Summaries", ""])
    for paper in selected:
        sections = paper["sections"]
        lines.append(f"### {paper['paper_id']} {paper['title']}")
        lines.append("")
        lines.append(f"- Status: {paper['status']}")
        lines.append(f"- Path: `{paper['path']}`")
        lines.append(f"- Abstract: {excerpt(sections.get('Abstract', ''))}")
        lines.append(f"- Hypothesis: {excerpt(sections.get('Hypothesis', ''), 260)}")
        lines.append(f"- Validation: {excerpt(sections.get('Validation', ''), 260)}")
        lines.append(f"- Relations: {relation_summary(paper)}")
        lines.append("")
    return lines


def render_references(ranked: list[dict]) -> list[str]:
    lines = [
        "## Best Reference Candidates",
        "",
        "| Rank | Paper | Status | Score | Reasons |",
        "| ---: | --- | --- | ---: | --- |",
    ]
    for index, item in enumerate(ranked, start=1):
        paper_label = f"{item['paper_id']} {item['title']}"
        lines.append(
            f"| {index} | {cell(paper_label)} | {cell(item['status'])} | "
            f"{item['score']} | {cell('; '.join(item['reasons']))} |"
        )
    if not ranked:
        lines.append("| 0 | None | n/a | 0 | No reference candidates after target exclusion. |")

    lines.extend(
        [
            "",
            "## Relationship Lines",
            "",
            "```text",
            f"References: {', '.join(item['paper_id'] for item in ranked) if ranked else 'None'}",
            "Depends on: None",
            "Supersedes: None",
            "Contradicts: None",
            "Extends: None",
            "```",
            "",
        ]
    )
    return lines


def result_json(
    *,
    root: Path,
    selected: list[dict],
    chunks: list[list[dict]],
    references: list[dict],
) -> dict:
    return {
        "root": str(root),
        "selected": [
            {
                "paper_id": paper["paper_id"],
                "title": paper["title"],
                "status": paper["status"],
                "path": str(paper["path"]),
            }
            for paper in selected
        ],
        "intervals": [
            {
                "from": chunk[0]["paper_id"],
                "to": chunk[-1]["paper_id"],
                "paper_count": len(chunk),
                "status_counts": dict(sorted(status_counts(chunk).items())),
            }
            for chunk in chunks
        ],
        "references": references,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministically combine Paper Stack papers.")
    parser.add_argument("root", nargs="?", default=".paper-stack", help="Paper Stack root")
    parser.add_argument("--from", dest="from_id", type=normalize_paper_id, help="First paper ID, inclusive")
    parser.add_argument("--to", dest="to_id", type=normalize_paper_id, help="Last paper ID, inclusive")
    parser.add_argument("--ids", nargs="+", type=normalize_paper_id, help="Explicit paper IDs")
    parser.add_argument("--last", type=int, help="Select the last N papers by numeric paper ID")
    parser.add_argument("--interval-size", type=int, default=0, help="Stable summary chunk size; 0 means one interval")
    parser.add_argument("--mode", choices=("summary", "references", "both"), default="both")
    parser.add_argument("--target-paper", type=normalize_paper_id, help="Paper ID to rank references against")
    parser.add_argument("--query", default="", help="Additional deterministic term-overlap query")
    parser.add_argument("--max-references", type=int, default=10)
    parser.add_argument("--output", type=Path, help="Output path; stdout when omitted")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    return parser.parse_args()


def validate_mode_options(args: argparse.Namespace) -> None:
    if args.mode != "summary":
        return
    ignored = []
    if args.target_paper:
        ignored.append("--target-paper")
    if args.query:
        ignored.append("--query")
    if ignored:
        raise SystemExit(
            "Reference ranking options require --mode references or --mode both: "
            + ", ".join(ignored)
        )


def main() -> int:
    args = parse_args()
    validate_mode_options(args)
    if args.max_references < 1:
        raise SystemExit("--max-references must be greater than zero.")

    root = Path(args.root)
    validate_stack(root)
    all_papers = load_all(root)
    if not all_papers:
        raise SystemExit(f"No papers found under {root / 'papers'}")

    selected = select_papers(args, all_papers)
    chunks = chunk_papers(selected, args.interval_size)
    references = []
    if args.mode in {"references", "both"}:
        validate_reference_target(args.target_paper, all_papers)
        references = rank_references(
            selected=selected,
            all_papers=all_papers,
            target_id=args.target_paper,
            query=args.query,
            max_references=args.max_references,
        )

    if args.json:
        output = json.dumps(
            result_json(root=root, selected=selected, chunks=chunks, references=references),
            indent=2,
        )
    else:
        lines = []
        if args.mode in {"summary", "both"}:
            lines.extend(render_summary(root, selected, chunks))
        if args.mode in {"references", "both"}:
            if lines and lines[-1] != "":
                lines.append("")
            lines.extend(render_references(references))
        output = "\n".join(lines).rstrip() + "\n"

    if args.output:
        write_text_output(args.output, output)
        print(args.output)
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
