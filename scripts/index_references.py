#!/usr/bin/env python3
"""Build a deterministic Paper Stack citation and dependency graph."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_paper import require_valid_stack
from paperstack_common import RELATION_LABELS, extract_relations, load_paper, paper_paths, relation_key, write_text_output


def build_graph(root: Path) -> dict:
    require_valid_stack(root)
    papers = [load_paper(path) for path in paper_paths(root)]
    nodes = [
        {
            "id": paper["paper_id"],
            "title": paper["title"],
            "status": paper["status"],
            "path": str(paper["path"]),
        }
        for paper in papers
    ]
    edges = []
    for paper in papers:
        relations = extract_relations(paper["text"], paper["paper_id"])
        for label in RELATION_LABELS:
            key = relation_key(label)
            for target in relations[key]:
                edges.append({"source": paper["paper_id"], "target": target, "type": key})

    inbound: dict[str, int] = {node["id"]: 0 for node in nodes}
    for edge in edges:
        inbound[edge["target"]] = inbound.get(edge["target"], 0) + 1
    return {"nodes": nodes, "edges": edges, "inbound_counts": inbound}


def main() -> int:
    parser = argparse.ArgumentParser(description="Index Paper Stack references.")
    parser.add_argument("root", nargs="?", default=".paper-stack", help="Paper Stack root")
    parser.add_argument("--output", help="Output JSON path")
    args = parser.parse_args()

    root = Path(args.root)
    graph = build_graph(root)
    output = Path(args.output) if args.output else root / "dashboard" / "references.json"
    write_text_output(output, json.dumps(graph, indent=2))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
