#!/usr/bin/env python3
"""Deterministically convert markdown papers to the HTML paper container."""

from __future__ import annotations

import argparse
from pathlib import Path

from paper_html import read_paper_text, write_paper_text
from paperstack_common import paper_paths


def read_raw_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def refresh(root: Path) -> int:
    for path in paper_paths(root):
        if path.suffix != ".html":
            continue
        source = read_paper_text(path)
        write_paper_text(path, source)
        if read_paper_text(path) != source:
            raise SystemExit(f"Lossless refresh failed for {path.name}; aborting")
        print(f"refreshed {path.name}")
    return 0


def convert(root: Path, *, dry_run: bool) -> int:
    converted = 0
    for path in paper_paths(root):
        if path.suffix != ".md":
            continue
        target = path.with_suffix(".html")
        if target.exists():
            raise SystemExit(f"Refusing to overwrite existing paper: {target}")
        source = read_raw_text(path)
        if dry_run:
            print(f"would-convert {path.name} -> {target.name}")
            converted += 1
            continue
        write_paper_text(target, source)
        if read_paper_text(target) != source:
            target.unlink()
            raise SystemExit(f"Lossless roundtrip failed for {path.name}; aborting")
        path.unlink()
        print(f"converted {path.name} -> {target.name}")
        converted += 1
    if converted == 0:
        print("OK nothing to convert")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert markdown papers to HTML containers.")
    parser.add_argument("root", nargs="?", default=".paper-stack", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="Rewrap existing HTML papers with the current renderer")
    args = parser.parse_args()
    if args.refresh:
        return refresh(args.root)
    return convert(args.root, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
