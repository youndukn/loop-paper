#!/usr/bin/env python3
"""Run a validation command and write an attested Paper Stack run record.

The executor — not the reporting agent — runs the command and records the
exact command, exit code, and a sha256 digest of the stored output, so the
checker can verify the evidence was produced by execution rather than
hand-authored. Papers with closed_loop_schema v3 require every after-evidence
bullet to cite a record written by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
from datetime import date
from pathlib import Path

from paperstack_common import paper_paths, paper_id_from_path, validate_iso_date


ATTESTATION_SCHEMA = "loop_paper.run_attestation.v1"
OUTPUT_FENCE = "````"
LABEL_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PAPER_ID_RE = re.compile(r"^PAPER-\d{4}$")


def render_record(
    *,
    name: str,
    paper_id: str,
    run_date: str,
    command: str,
    exit_code: int,
    output: str,
    truncated: bool,
) -> str:
    digest = hashlib.sha256(output.encode("utf-8")).hexdigest()
    truncated_note = " (truncated)" if truncated else ""
    return f"""# {name}

attestation: {ATTESTATION_SCHEMA}
command: {command}
exit_code: {exit_code}
output_sha256: {digest}

- Date: {run_date}
- Related paper: {paper_id}

## Output{truncated_note}

{OUTPUT_FENCE}text
{output}
{OUTPUT_FENCE}
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute a validation command and write an attested run record."
    )
    parser.add_argument("--root", type=Path, default=Path(".paper-stack"))
    parser.add_argument("--paper", required=True, help="Related paper ID (PAPER-NNNN)")
    parser.add_argument("--label", required=True, help="Short lowercase record label")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument(
        "--max-output-bytes",
        type=int,
        default=20000,
        help="Stored output is truncated to this many bytes; the digest covers the stored text.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to execute, after `--`.",
    )
    args = parser.parse_args()
    args.date = validate_iso_date(args.date)
    if not PAPER_ID_RE.fullmatch(args.paper):
        raise SystemExit(f"--paper must be PAPER-NNNN, got {args.paper!r}")
    if not LABEL_RE.fullmatch(args.label):
        raise SystemExit("--label must contain only lowercase letters, numbers, and single hyphens")
    command = [item for item in args.command if item != "--"] if args.command else []
    if not command:
        raise SystemExit("Provide the command to execute after `--`")
    known_ids = {paper_id_from_path(path) for path in paper_paths(args.root)}
    if args.paper not in known_ids:
        raise SystemExit(f"Unknown paper in stack: {args.paper}")

    name = f"RUN-{args.date}-{args.paper}-{args.label}"
    record_path = args.root / "runs" / f"{name}.md"
    if record_path.exists():
        raise SystemExit(f"Refusing to overwrite existing run record: {record_path}")

    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    output = (completed.stdout or "") + (completed.stderr or "")
    encoded = output.encode("utf-8")
    truncated = len(encoded) > args.max_output_bytes
    if truncated:
        output = encoded[: args.max_output_bytes].decode("utf-8", errors="ignore")
    output = output.rstrip("\n")
    if OUTPUT_FENCE in output:
        output = output.replace(OUTPUT_FENCE, "`` ``")

    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(
        render_record(
            name=name,
            paper_id=args.paper,
            run_date=args.date,
            command=" ".join(command),
            exit_code=completed.returncode,
            output=output,
            truncated=truncated,
        ),
        encoding="utf-8",
    )
    print(record_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
