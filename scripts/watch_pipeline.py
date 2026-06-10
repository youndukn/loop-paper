#!/usr/bin/env python3
"""Poll Paper Stack files and rerun the deterministic pipeline on changes."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE = SCRIPT_DIR / "pipeline.py"


def snapshot(root: Path) -> dict[str, int]:
    papers = root / "papers"
    if not papers.exists():
        return {}
    return {str(path): path.stat().st_mtime_ns for path in papers.glob("PAPER-*.md")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch Paper Stack papers and rerun pipeline.")
    parser.add_argument("root", nargs="?", default=".paper-stack", help="Paper Stack root")
    parser.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    root = Path(args.root)
    previous = None
    while True:
        current = snapshot(root)
        if previous != current:
            subprocess.run([sys.executable, str(PIPELINE), str(root)], check=False)
            previous = current
        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
