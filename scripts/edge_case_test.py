#!/usr/bin/env python3
"""Exercise Loop Paper CLI rejection paths that protect workflow determinism."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent


def script(name: str) -> str:
    return str(SCRIPT_DIR / name)


def run_ok(command: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        print("$ " + " ".join(command), file=sys.stderr)
        if completed.stdout:
            print(completed.stdout, file=sys.stderr, end="")
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")
        raise SystemExit(completed.returncode)
    return completed


def run_ok_cwd(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        print("$ " + " ".join(command), file=sys.stderr)
        if completed.stdout:
            print(completed.stdout, file=sys.stderr, end="")
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")
        raise SystemExit(completed.returncode)
    return completed


def run_fail(command: list[str], expected: str) -> None:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    output = completed.stdout + completed.stderr
    if completed.returncode == 0:
        print("$ " + " ".join(command), file=sys.stderr)
        print("Expected command to fail, but it succeeded.", file=sys.stderr)
        raise SystemExit(1)
    if expected not in output:
        print("$ " + " ".join(command), file=sys.stderr)
        print(output, file=sys.stderr, end="")
        print(f"Expected failure output to contain: {expected!r}", file=sys.stderr)
        raise SystemExit(1)


def write_answers(path: Path, *, evidence: str = "Strong", coherence: str = "Coherent") -> None:
    answers = {
        "verdict.PAPER-0001": "Supported",
        "evidence.PAPER-0001": evidence,
        "production.PAPER-0001": "Ready",
        "action.PAPER-0001": "Accept",
        "coherence": coherence,
        "direction": "Continue same line",
    }
    path.write_text(json.dumps(answers, indent=2), encoding="utf-8")


def mark_checkboxes(text: str, labels: list[str]) -> str:
    for label in labels:
        text = text.replace(f"- [ ] {label}", f"- [x] {label}")
    return text


def normalize_prior_research_options(text: str) -> str:
    return text.replace(
        "Prior Research Status: Recorded: Present/Missing/Retrospective",
        "Prior Research Status: Present",
    ).replace(
        "Risk: Recorded: Low/Medium/High",
        "Risk: Low",
    )


def normalize_agent_review_fields(text: str) -> str:
    return text.replace(
        "Agent reviewer:",
        "Agent reviewer: edge-test",
        1,
    ).replace(
        "Review date:",
        "Review date: 2026-06-10",
        1,
    ).replace(
        "Decision: Recorded: Draft/Plan Ready/Implemented/AI Validated/Rejected",
        "Decision: AI Validated",
        1,
    )


def resolve_hypothesis_ledger_verdicts(text: str) -> str:
    return re.sub(r"(?m)^(\| H\d+ \|.*\| )Open( \|)$", r"\1Supported\2", text)


BEFORE_READY_CHECKBOXES = [
    "Hypothesis is specific",
    "Hypothesis can be validated or rejected",
    "Baseline evidence is recorded before implementation",
    "Prior work is cited, or missing prior work is explicitly acknowledged",
    "Implementation plan is concrete",
    "Dependencies are named",
    "Risks are named",
    "Recorded: test/verifier/check to run",
]
AFTER_READY_CHECKBOXES = BEFORE_READY_CHECKBOXES + [
    "AI validation evidence recorded",
    "Agent reviewed paper structure",
    "Agent confirmed evidence backs the recorded verdict",
    "Impact score is based on evidence, not agent guesswork",
]


def before_ready_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = text.replace("BEFORE_REQUIRED:", "Recorded:")
    return normalize_prior_research_options(text)


def attested_edge_record(path: Path) -> str:
    paper_id = re.match(r"(PAPER-\d{4})", path.name).group(1)
    root = path.parent.parent
    name = f"RUN-2026-06-10-{paper_id}-edge"
    if not (root / "runs" / f"{name}.md").exists():
        run_ok(
            [
                sys.executable,
                script("execute_run.py"),
                "--root",
                str(root),
                "--paper",
                paper_id,
                "--label",
                "edge",
                "--date",
                "2026-06-10",
                "--",
                sys.executable,
                "-c",
                "print('edge ok')",
            ]
        )
    return name


def after_ready_text(path: Path) -> str:
    record_name = attested_edge_record(path)
    text = before_ready_text(path).replace("AFTER_REQUIRED:", "Recorded:")
    text = re.sub(
        r"(?m)^- \[ \] (Recorded: (?:first|second) implementation step)",
        r"- [x] \1",
        text,
    )
    text = text.replace(
        "- Recorded: exact post-change output or inspected evidence",
        f"- 2026-06-10 Attested evidence: {record_name}",
        1,
    )
    text = normalize_agent_review_fields(text)
    return resolve_hypothesis_ledger_verdicts(text)


RECORDED_VERDICT_INSTRUCTION = (
    "- Recorded: mark each hypothesis Supported, Failed, Inconclusive, or\n"
    "  Superseded in both the Hypothesis Ledger Verdict column and this block,\n"
    "  with the evidence reason."
)


def make_before_ready_with_uppercase_checks(path: Path) -> None:
    text = before_ready_text(path)
    text = mark_checkboxes(
        text,
        BEFORE_READY_CHECKBOXES,
    )
    text = text.replace("- [x]", "- [X]")
    path.write_text(text, encoding="utf-8")


def make_before_ready_except_prior_research(path: Path) -> None:
    text = before_ready_text(path)
    text = mark_checkboxes(
        text,
        [
            "Hypothesis is specific",
            "Hypothesis can be validated or rejected",
            "Baseline evidence is recorded before implementation",
            "Implementation plan is concrete",
            "Dependencies are named",
            "Risks are named",
            "Recorded: test/verifier/check to run",
        ],
    )
    path.write_text(text, encoding="utf-8")


def make_before_ready_except_validation_plan(path: Path) -> None:
    text = before_ready_text(path)
    text = mark_checkboxes(
        text,
        [
            "Hypothesis is specific",
            "Hypothesis can be validated or rejected",
            "Baseline evidence is recorded before implementation",
            "Prior work is cited, or missing prior work is explicitly acknowledged",
            "Implementation plan is concrete",
            "Dependencies are named",
            "Risks are named",
        ],
    )
    path.write_text(text, encoding="utf-8")


def make_before_ready_with_unrelated_validation_plan_check(path: Path) -> None:
    text = before_ready_text(path)
    text = mark_checkboxes(
        text,
        [
            "Hypothesis is specific",
            "Hypothesis can be validated or rejected",
            "Baseline evidence is recorded before implementation",
            "Prior work is cited, or missing prior work is explicitly acknowledged",
            "Implementation plan is concrete",
            "Dependencies are named",
            "Risks are named",
        ],
    )
    text = text.replace(
        "After-change evidence to collect:\n\n- AFTER_REQUIRED: command, artifact, metric, screenshot, or inspection",
        "After-change evidence to collect:\n\n"
        "- AFTER_REQUIRED: command, artifact, metric, screenshot, or inspection\n"
        "- [x] unrelated validation-plan checkbox",
        1,
    )
    path.write_text(text, encoding="utf-8")


def make_before_ready_with_empty_hypothesis_claim(path: Path) -> None:
    text = before_ready_text(path)
    text = mark_checkboxes(
        text,
        BEFORE_READY_CHECKBOXES,
    )
    text = re.sub(
        r"^\| H1 \| [^|]+ \|",
        "| H1 |  |",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    path.write_text(text, encoding="utf-8")


def make_before_ready_with_empty_prior_finding(path: Path) -> None:
    text = before_ready_text(path)
    text = mark_checkboxes(
        text,
        BEFORE_READY_CHECKBOXES,
    )
    text = re.sub(
        r"^(\| \d{4}-\d{2}-\d{2} \| )[^|]+(\|)",
        r"\1 \2",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    path.write_text(text, encoding="utf-8")


def make_before_ready_with_empty_implementation_risks(path: Path) -> None:
    text = before_ready_text(path)
    text = mark_checkboxes(
        text,
        BEFORE_READY_CHECKBOXES,
    )
    text = re.sub(
        r"(?ms)^Risks:\n\n- .+?\n\nRollback/undo:",
        "Risks:\n\nRollback/undo:",
        text,
        count=1,
    )
    path.write_text(text, encoding="utf-8")


def make_before_ready_with_empty_validation_baseline(path: Path) -> None:
    text = before_ready_text(path)
    text = mark_checkboxes(
        text,
        BEFORE_READY_CHECKBOXES,
    )
    text = re.sub(
        r"(?ms)^Before-change evidence:\n\n- .+?\n\nAfter-change evidence to collect:",
        "Before-change evidence:\n\nAfter-change evidence to collect:",
        text,
        count=1,
    )
    path.write_text(text, encoding="utf-8")


def make_before_ready_with_unrelated_hypothesis_checks(path: Path) -> None:
    text = before_ready_text(path)
    text = mark_checkboxes(
        text,
        [
            "Prior work is cited, or missing prior work is explicitly acknowledged",
            "Implementation plan is concrete",
            "Dependencies are named",
            "Risks are named",
            "Recorded: test/verifier/check to run",
        ],
    )
    text = text.replace(
        "- [ ] Baseline evidence is recorded before implementation\n\n## Prior Research",
        "- [ ] Baseline evidence is recorded before implementation\n"
        "- [x] unrelated hypothesis checkbox one\n"
        "- [x] unrelated hypothesis checkbox two\n"
        "- [x] unrelated hypothesis checkbox three\n\n"
        "## Prior Research",
        1,
    )
    path.write_text(text, encoding="utf-8")


def make_after_ready_except_validation_evidence(path: Path) -> None:
    text = after_ready_text(path)
    text = mark_checkboxes(
        text,
        [
            "Hypothesis is specific",
            "Hypothesis can be validated or rejected",
            "Baseline evidence is recorded before implementation",
            "Prior work is cited, or missing prior work is explicitly acknowledged",
            "Implementation plan is concrete",
            "Dependencies are named",
            "Risks are named",
            "Recorded: test/verifier/check to run",
            "Agent reviewed paper structure",
            "Agent confirmed evidence backs the recorded verdict",
            "Impact score is based on evidence, not agent guesswork",
        ],
    )
    text = text.replace(RECORDED_VERDICT_INSTRUCTION, "- Supported: edge-case verdict recorded with evidence pending.")
    path.write_text(text, encoding="utf-8")


def make_after_ready(path: Path) -> None:
    make_after_ready_except_validation_evidence(path)
    text = path.read_text(encoding="utf-8")
    text = mark_checkboxes(text, ["AI validation evidence recorded"])
    path.write_text(text, encoding="utf-8")


def make_after_ready_with_unrelated_agent_checks(path: Path) -> None:
    text = after_ready_text(path)
    text = mark_checkboxes(
        text,
        [
            "Hypothesis is specific",
            "Hypothesis can be validated or rejected",
            "Baseline evidence is recorded before implementation",
            "Prior work is cited, or missing prior work is explicitly acknowledged",
            "Implementation plan is concrete",
            "Dependencies are named",
            "Risks are named",
            "Recorded: test/verifier/check to run",
            "AI validation evidence recorded",
            "Impact score is based on evidence, not agent guesswork",
        ],
    )
    text = text.replace(RECORDED_VERDICT_INSTRUCTION, "- Supported: edge-case verdict recorded.")
    text = text.replace(
        "- [ ] Agent confirmed evidence backs the recorded verdict\n\n## Impact Score",
        "- [ ] Agent confirmed evidence backs the recorded verdict\n"
        "- [x] unrelated agent checkbox one\n"
        "- [x] unrelated agent checkbox two\n\n"
        "## Impact Score",
        1,
    )
    path.write_text(text, encoding="utf-8")


def make_after_ready_with_instruction_verdict(path: Path) -> None:
    text = after_ready_text(path)
    text = mark_checkboxes(
        text,
        AFTER_READY_CHECKBOXES,
    )
    path.write_text(text, encoding="utf-8")


def make_after_ready_with_empty_validation_after(path: Path) -> None:
    text = after_ready_text(path)
    text = mark_checkboxes(
        text,
        AFTER_READY_CHECKBOXES,
    )
    text = text.replace(RECORDED_VERDICT_INSTRUCTION, "- Supported: edge-case verdict recorded.")
    text = re.sub(
        r"(?ms)^After:\n\n- .+?\n\nVerdict:",
        "After:\n\nVerdict:",
        text,
        count=1,
    )
    path.write_text(text, encoding="utf-8")


def make_after_ready_with_missing_agent_reviewer(path: Path) -> None:
    text = after_ready_text(path)
    text = mark_checkboxes(
        text,
        AFTER_READY_CHECKBOXES,
    )
    text = text.replace(RECORDED_VERDICT_INSTRUCTION, "- Supported: edge-case verdict recorded.")
    text = text.replace("Agent reviewer: edge-test", "Agent reviewer:", 1)
    path.write_text(text, encoding="utf-8")


def make_after_ready_with_invalid_agent_decision(path: Path) -> None:
    text = after_ready_text(path)
    text = mark_checkboxes(
        text,
        AFTER_READY_CHECKBOXES,
    )
    text = text.replace(RECORDED_VERDICT_INSTRUCTION, "- Supported: edge-case verdict recorded.")
    text = text.replace("Decision: AI Validated", "Decision: Agent Reviewed", 1)
    path.write_text(text, encoding="utf-8")


def make_after_ready_with_duplicate_agent_decision(path: Path) -> None:
    text = after_ready_text(path)
    text = mark_checkboxes(
        text,
        AFTER_READY_CHECKBOXES,
    )
    text = text.replace(RECORDED_VERDICT_INSTRUCTION, "- Supported: edge-case verdict recorded.")
    text = text.replace("Decision: AI Validated", "Decision: AI Validated\nDecision: Accepted", 1)
    path.write_text(text, encoding="utf-8")


def make_after_ready_with_empty_impact_basis(path: Path) -> None:
    text = after_ready_text(path)
    text = mark_checkboxes(
        text,
        AFTER_READY_CHECKBOXES,
    )
    text = text.replace(RECORDED_VERDICT_INSTRUCTION, "- Supported: edge-case verdict recorded.")
    text = re.sub(
        r"^- Measured outcome: .+$",
        "- Measured outcome:",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    path.write_text(text, encoding="utf-8")


def make_after_ready_with_duplicate_impact_fields(path: Path) -> None:
    text = after_ready_text(path)
    text = mark_checkboxes(
        text,
        AFTER_READY_CHECKBOXES,
    )
    text = text.replace(RECORDED_VERDICT_INSTRUCTION, "- Supported: edge-case verdict recorded.")
    text = text.replace("Impact score: TBD", "Impact score: TBD\nImpact score: 10", 1)
    text = text.replace(
        "- Validation strength: Recorded: TBD until validation runs",
        "- Validation strength: Recorded: TBD until validation runs\n- Validation strength: duplicate value",
        1,
    )
    path.write_text(text, encoding="utf-8")


def make_after_ready_with_invalid_impact_score(path: Path) -> None:
    text = after_ready_text(path)
    text = mark_checkboxes(
        text,
        AFTER_READY_CHECKBOXES,
    )
    text = text.replace(RECORDED_VERDICT_INSTRUCTION, "- Supported: edge-case verdict recorded.")
    text = text.replace("Impact score: TBD", "Impact score: significant", 1)
    path.write_text(text, encoding="utf-8")


def make_after_ready_with_empty_run_records(path: Path) -> None:
    text = after_ready_text(path)
    text = mark_checkboxes(
        text,
        AFTER_READY_CHECKBOXES,
    )
    text = text.replace(RECORDED_VERDICT_INSTRUCTION, "- Supported: edge-case verdict recorded.")
    text = re.sub(
        r"(?ms)^Run records:\n\n- .+?\n\nFix records:",
        "Run records:\n\nFix records:",
        text,
        count=1,
    )
    path.write_text(text, encoding="utf-8")


def set_status(path: Path, status: str) -> None:
    text = path.read_text(encoding="utf-8")
    if "status: Draft" not in text:
        raise SystemExit(f"Expected draft status in {path}")
    path.write_text(text.replace("status: Draft", f"status: {status}", 1), encoding="utf-8")


def set_paper_id(path: Path, paper_id: str) -> None:
    text = path.read_text(encoding="utf-8")
    current = path.name.split("-", 2)
    if len(current) < 2:
        raise SystemExit(f"Cannot infer paper id from {path}")
    filename_id = "-".join(current[:2])
    if f"paper_id: {filename_id}" not in text:
        raise SystemExit(f"Expected paper_id {filename_id} in {path}")
    path.write_text(text.replace(f"paper_id: {filename_id}", f"paper_id: {paper_id}", 1), encoding="utf-8")


def disable_proposal_gate(root: Path) -> None:
    config = root / "config" / "loop-paper.json"
    if not config.is_file():
        return
    payload = json.loads(config.read_text(encoding="utf-8"))
    if payload.pop("proposal_gate", None) is not None:
        config.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def create_edge_paper(root: Path, title: str) -> Path:
    disable_proposal_gate(root)
    return Path(
        run_ok(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(root),
                "--title",
                title,
                "--hypothesis",
                f"{title} can exercise a checker edge case",
                "--finding",
                "Edge tests need a generated paper",
                "--reference",
                "scripts/edge_case_test.py",
                "--date",
                "2026-06-10",
            ]
        ).stdout.strip()
    )


def ensure_artifact_integrity_roundtrips() -> None:
    from paper_html import read_paper_text, write_paper_text

    with tempfile.TemporaryDirectory(prefix="loop-paper-artifact-") as tmp:
        root = Path(tmp) / ".paper-stack"
        papers = root / "papers"
        papers.mkdir(parents=True)
        source = (
            "# PAPER-0001 Marker Quote\n\n"
            "```html\n"
            '<script type="text/markdown" id="paper-source">\n'
            "hello\n"
            "</script>\n"
            "```\n\n"
            "IMPORTANT TAIL CONTENT THAT MUST SURVIVE\n"
        )
        markdown_path = papers / "PAPER-0001-marker-quote.md"
        markdown_path.write_text(source, encoding="utf-8")
        run_ok([sys.executable, script("convert_papers.py"), str(root)])
        converted = markdown_path.with_suffix(".html")
        if markdown_path.exists():
            raise SystemExit("convert_papers.py left the markdown source after a successful conversion")
        if read_paper_text(converted) != source:
            raise SystemExit("convert_papers.py did not preserve markdown that quotes paper-source markers")
        run_ok([sys.executable, script("convert_papers.py"), str(root), "--refresh"])
        if read_paper_text(converted) != source:
            raise SystemExit("convert_papers.py --refresh changed canonical source")

        sentinel_source = (
            "# PAPER-0002 <Sentinel> & Title\n\n"
            "```js\n"
            "const s = \"<\\/script>\";\n"
            "```\n"
        )
        sentinel_path = papers / "PAPER-0002-sentinel.html"
        write_paper_text(sentinel_path, sentinel_source)
        if read_paper_text(sentinel_path) != sentinel_source:
            raise SystemExit("paper_html.py did not preserve literal escaped script sentinels")
        write_paper_text(sentinel_path, read_paper_text(sentinel_path))
        if read_paper_text(sentinel_path) != sentinel_source:
            raise SystemExit("paper_html.py metadata-style rewrite changed canonical source")
        html_text = sentinel_path.read_text(encoding="utf-8")
        if "<title>PAPER-0002 &lt;Sentinel&gt; &amp; Title</title>" not in html_text:
            raise SystemExit("paper_html.py did not escape HTML-sensitive paper titles")


def ensure_workflow_docs_are_current() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    structure = (ROOT / "assets" / "structure-template.md").read_text(encoding="utf-8")
    init_script = (SCRIPT_DIR / "init_loop_paper.py").read_text(encoding="utf-8")
    required_readme = [
        "Python 3.10+",
        "npx skills add youndukn/loop-paper",
        "--no-claude-hook",
        "workflow guardrail, not a security sandbox",
        "answers JSON",
        "not cryptographic proof of human origin",
        "transition_paper.py",
        "`- Supported: ...`",
        "## Execution Records",
        "self-consistency",
    ]
    for needle in required_readme:
        if needle not in readme:
            raise SystemExit(f"README.md missing workflow documentation: {needle}")
    required_skill = [
        "not a security sandbox",
        "Answers JSON",
        "not cryptographically prove human origin",
        "transition_paper.py",
        "- Supported: evidence reason",
        "## Execution Records",
        "self-consistency",
    ]
    for needle in required_skill:
        if needle not in skill:
            raise SystemExit(f"SKILL.md missing workflow documentation: {needle}")
    forbidden = ["produced by execution rather than hand-authored", "not hand-authored"]
    for needle in forbidden:
        if needle in readme or needle in skill or needle in (SCRIPT_DIR / "execute_run.py").read_text(encoding="utf-8"):
            raise SystemExit(f"Documentation still overclaims run attestation: {needle}")
    if "PAPER-NNNN-title.html" not in structure or "PAPER-NNNN-title.md" in structure:
        raise SystemExit("structure-template.md closeout path does not use HTML paper paths")
    if "propose_paper.py" not in init_script or "--candidate-abstract" not in init_script:
        raise SystemExit("init_loop_paper.py next_steps do not point to propose_paper.py")


def ensure_validator_ignores_local_paper_stack() -> None:
    local_skill = ROOT / ".paper-stack" / "validator-ignore" / "SKILL.md"
    local_skill.parent.mkdir(parents=True, exist_ok=True)
    local_skill.write_text(
        "---\nname: local-artifact\ndescription: ignored local test artifact\n---\n",
        encoding="utf-8",
    )
    try:
        run_ok([sys.executable, script("validate_skill_repo.py")])
    finally:
        local_skill.unlink(missing_ok=True)
        try:
            local_skill.parent.rmdir()
        except OSError:
            pass


def ensure_validator_rejects_malformed_skill_frontmatter() -> None:
    skill = ROOT / "SKILL.md"
    original = skill.read_text(encoding="utf-8")
    try:
        skill.write_text(
            original.replace("name: loop-paper", "name: loop-paper\nname: duplicate-loop-paper", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("validate_skill_repo.py")],
            "duplicate frontmatter key: name",
        )
        skill.write_text(
            original.replace("description:", "description", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("validate_skill_repo.py")],
            "malformed frontmatter line",
        )
    finally:
        skill.write_text(original, encoding="utf-8")


def ensure_validator_handles_missing_git() -> None:
    completed = subprocess.run(
        [sys.executable, script("validate_skill_repo.py")],
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PATH": ""},
    )
    if completed.returncode != 0 or "OK loop-paper skill repository" not in completed.stdout:
        raise SystemExit("validate_skill_repo.py did not fall back cleanly when git is unavailable")


def ensure_installed_payload_validates() -> None:
    with tempfile.TemporaryDirectory(prefix="loop-paper-installed-") as tmp:
        tmp_path = Path(tmp)
        destination = tmp_path / "loop-paper"
        run_ok(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "codex",
                "--dest",
                str(destination),
            ]
        )
        run_ok([sys.executable, str(destination / "scripts" / "validate_skill_repo.py")])
        run_ok([sys.executable, str(destination / "scripts" / "smoke_test.py")])

        home = tmp_path / "home"
        run_ok(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "all",
                "--home",
                str(home),
            ]
        )
        expected_user_installs = {
            "agents": home / ".agents" / "skills" / "loop-paper",
            "claude": home / ".claude" / "skills" / "loop-paper",
            "codex": home / ".codex" / "skills" / "loop-paper",
            "hermes": home / ".hermes" / "skills" / "loop-paper",
            "openclaw": home / ".openclaw" / "skills" / "loop-paper",
            "pimo": home / ".pimo" / "skills" / "loop-paper",
        }
        for agent, install_root in expected_user_installs.items():
            if not (install_root / "SKILL.md").exists():
                raise SystemExit(f"Missing installed SKILL.md for {agent}: {install_root}")
            run_ok([sys.executable, str(install_root / "scripts" / "validate_skill_repo.py")])
        run_ok([sys.executable, str(expected_user_installs["codex"] / "scripts" / "smoke_test.py")])

        project_root = tmp_path / "project"
        project_install = run_ok(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "all",
                "--scope",
                "project",
                "--project-root",
                str(project_root),
            ]
        )
        if "hermes+openclaw" not in project_install.stdout:
            raise SystemExit("Project-scope all-agent install did not merge shared skills/ target")
        expected_project_installs = {
            "agents": project_root / ".agents" / "skills" / "loop-paper",
            "claude": project_root / ".claude" / "skills" / "loop-paper",
            "codex": project_root / ".codex" / "skills" / "loop-paper",
            "shared": project_root / "skills" / "loop-paper",
        }
        for agent, install_root in expected_project_installs.items():
            if not (install_root / "SKILL.md").exists():
                raise SystemExit(f"Missing project installed SKILL.md for {agent}: {install_root}")
            run_ok([sys.executable, str(install_root / "scripts" / "validate_skill_repo.py")])


def ensure_installer_rejects_recursive_destinations() -> None:
    run_fail(
        [
            sys.executable,
            script("install_skill.py"),
            "--agent",
            "codex",
            "--dest",
            str(ROOT / "scripts" / "nested-install"),
        ],
        "Refusing to install inside the source checkout",
    )
    run_fail(
        [
            sys.executable,
            script("install_skill.py"),
            "--agent",
            "codex",
            "--dest",
            str(ROOT.parent),
            "--force",
            "--dry-run",
        ],
        "Refusing to install over a parent of the source checkout",
    )


def ensure_installer_rejects_file_parent() -> None:
    with tempfile.TemporaryDirectory(prefix="loop-paper-install-parent-") as tmp:
        parent_file = Path(tmp) / "not-a-directory"
        parent_file.write_text("file parent", encoding="utf-8")
        destination = parent_file / "loop-paper"
        run_fail(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "codex",
                "--dest",
                str(destination),
            ],
            f"Expected install parent directory, got file: {parent_file}",
        )
        run_fail(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "codex",
                "--dest",
                str(destination),
                "--dry-run",
            ],
            f"Expected install parent directory, got file: {parent_file}",
        )
        nested_destination = parent_file / "nested" / "loop-paper"
        run_fail(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "codex",
                "--dest",
                str(nested_destination),
            ],
            f"Expected install parent directory, got file: {parent_file}",
        )
        run_fail(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "codex",
                "--dest",
                str(nested_destination),
                "--dry-run",
            ],
            f"Expected install parent directory, got file: {parent_file}",
        )


def ensure_installer_replaces_broken_symlink() -> None:
    with tempfile.TemporaryDirectory(prefix="loop-paper-install-broken-link-") as tmp:
        destination = Path(tmp) / "loop-paper"
        missing_target = Path(tmp) / "missing-target"
        destination.symlink_to(missing_target, target_is_directory=True)
        dry_run = run_ok(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "codex",
                "--dest",
                str(destination),
                "--dry-run",
            ]
        )
        if "would-replace-broken-symlink" not in dry_run.stdout:
            raise SystemExit("Installer dry run did not report broken symlink replacement")
        if not destination.is_symlink():
            raise SystemExit("Installer dry run modified a broken symlink destination")

        run_ok(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "codex",
                "--dest",
                str(destination),
            ]
        )
        if destination.is_symlink():
            raise SystemExit("Installer left broken symlink in place")
        if not (destination / "SKILL.md").exists():
            raise SystemExit("Installer did not replace broken symlink with skill payload")
        run_ok([sys.executable, str(destination / "scripts" / "validate_skill_repo.py")])


def ensure_installer_force_copy_replaces_source_symlink() -> None:
    with tempfile.TemporaryDirectory(prefix="loop-paper-install-mode-switch-") as tmp:
        destination = Path(tmp) / "loop-paper"
        run_ok(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "codex",
                "--dest",
                str(destination),
                "--mode",
                "symlink",
            ]
        )
        if not destination.is_symlink():
            raise SystemExit("Installer did not create an initial symlink install")
        run_fail(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "codex",
                "--dest",
                str(destination),
                "--mode",
                "copy",
            ],
            "Refusing to overwrite existing destination",
        )
        dry_run = run_ok(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "codex",
                "--dest",
                str(destination),
                "--mode",
                "copy",
                "--force",
                "--dry-run",
            ]
        )
        if "would-replace" not in dry_run.stdout:
            raise SystemExit("Installer dry run did not report symlink-to-copy replacement")
        if not destination.is_symlink():
            raise SystemExit("Installer dry run modified the source symlink install")
        run_ok(
            [
                sys.executable,
                script("install_skill.py"),
                "--agent",
                "codex",
                "--dest",
                str(destination),
                "--mode",
                "copy",
                "--force",
            ]
        )
        if destination.is_symlink():
            raise SystemExit("Installer did not replace source symlink with copied payload")
        if not (destination / "SKILL.md").exists():
            raise SystemExit("Installer copy replacement did not include SKILL.md")
        run_ok([sys.executable, str(destination / "scripts" / "validate_skill_repo.py")])


def ensure_proposal_gate_enforcement() -> None:
    with tempfile.TemporaryDirectory(prefix="loop-paper-gate-") as tmp:
        project = Path(tmp)
        root = project / ".paper-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(root),
                "--project-name",
                "Proposal Gate Edge",
                "--date",
                "2026-06-10",
            ]
        )
        config = json.loads((root / "config" / "loop-paper.json").read_text(encoding="utf-8"))
        if config.get("proposal_gate") != {"required_from": "PAPER-0001"}:
            raise SystemExit("init did not enable the proposal gate from PAPER-0001 by default")
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(root),
                "--title",
                "Ungated Paper",
                "--hypothesis",
                "a",
                "--hypothesis",
                "b",
                "--finding",
                "f",
                "--date",
                "2026-06-10",
            ],
            "requires a human-gated proposal",
        )
        # A paper written around the creator must still fail the checker.
        paper = create_edge_paper(root, "Bypass Paper")  # disables the gate to create
        gate_config = root / "config" / "loop-paper.json"
        payload = json.loads(gate_config.read_text(encoding="utf-8"))
        payload["proposal_gate"] = {"required_from": "PAPER-0001"}
        gate_config.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(paper),
                "--phase",
                "structural",
            ],
            "missing proposal_record",
        )
        # Seeded stacks exempt only the seed paper.
        seeded_root = project / "seeded" / ".paper-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(seeded_root),
                "--project-name",
                "Seeded Gate Edge",
                "--seed-paper",
                "--date",
                "2026-06-10",
            ]
        )
        seeded_config = json.loads(
            (seeded_root / "config" / "loop-paper.json").read_text(encoding="utf-8")
        )
        if seeded_config.get("proposal_gate") != {"required_from": "PAPER-0002"}:
            raise SystemExit("seeded init did not gate from PAPER-0002")


def ensure_deterministic_gate_hardening() -> None:
    def init(root: Path, name: str) -> None:
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(root),
                "--project-name",
                name,
                "--date",
                "2026-06-10",
            ]
        )

    def proposal_answers(path: Path, abstract: str, hypotheses: list[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "abstract": abstract,
                    "hypothesis_set": " | ".join(hypotheses),
                    "gate": "Implement now",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def propose_command(root: Path, title: str, abstract: str, hypotheses: list[str], answers: Path) -> list[str]:
        return [
            sys.executable,
            script("propose_paper.py"),
            "--root",
            str(root),
            "--title",
            title,
            "--candidate-abstract",
            abstract,
            "--candidate-abstract",
            f"Alternate framing for {title}",
            "--candidate-set",
            "||".join(hypotheses),
            "--candidate-set",
            "Alternate first claim||Alternate second claim",
            "--finding",
            "Deterministic gate hardening regression coverage",
            "--reference",
            "scripts/edge_case_test.py",
            "--date",
            "2026-06-10",
            "--answers",
            str(answers),
        ]

    with tempfile.TemporaryDirectory(prefix="loop-paper-deterministic-gate-") as tmp:
        project = Path(tmp)

        invalid_config_root = project / "invalid-config" / ".paper-stack"
        init(invalid_config_root, "Invalid Config Gate")
        (invalid_config_root / "config" / "loop-paper.json").write_text("{\n", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(invalid_config_root),
                "--title",
                "Invalid Config Paper",
                "--hypothesis",
                "a",
                "--hypothesis",
                "b",
                "--finding",
                "f",
                "--date",
                "2026-06-10",
            ],
            "Invalid project config JSON",
        )

        bad_required_root = project / "bad-required" / ".paper-stack"
        init(bad_required_root, "Bad Required Gate")
        payload = json.loads((bad_required_root / "config" / "loop-paper.json").read_text(encoding="utf-8"))
        payload["proposal_gate"] = {"required_from": "PAPER-1"}
        (bad_required_root / "config" / "loop-paper.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(bad_required_root),
                "--title",
                "Bad Required Paper",
                "--hypothesis",
                "a",
                "--hypothesis",
                "b",
                "--finding",
                "f",
                "--date",
                "2026-06-10",
            ],
            "proposal_gate.required_from must be PAPER-NNNN",
        )

        reuse_root = project / "reuse-record" / ".paper-stack"
        init(reuse_root, "Reuse Record Gate")
        reuse_answers = reuse_root / "inbox" / "answers.json"
        reuse_abstract = "Approved framing for one paper only."
        reuse_hypotheses = ["Approved first claim", "Approved second claim"]
        proposal_answers(reuse_answers, reuse_abstract, reuse_hypotheses)
        approved = Path(
            run_ok(
                propose_command(
                    reuse_root,
                    "Approved Paper",
                    reuse_abstract,
                    reuse_hypotheses,
                    reuse_answers,
                )
            ).stdout.strip()
        )
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(reuse_root),
                "--title",
                "Unapproved Reuse Paper",
                "--hypothesis",
                reuse_hypotheses[0],
                "--hypothesis",
                reuse_hypotheses[1],
                "--finding",
                "Attempt to reuse a proposal record",
                "--abstract",
                reuse_abstract,
                "--proposal-record",
                "proposals/PROPOSAL-PAPER-0001.json",
                "--date",
                "2026-06-10",
            ],
            "Proposal record paper_id mismatch",
        )
        record = reuse_root / "proposals" / "PROPOSAL-PAPER-0001.json"
        record_payload = json.loads(record.read_text(encoding="utf-8"))
        record_payload["title"] = "Tampered Title"
        record.write_text(json.dumps(record_payload, indent=2) + "\n", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(approved),
                "--phase",
                "structural",
            ],
            "proposal record title mismatch",
        )

        table_root = project / "table-record" / ".paper-stack"
        init(table_root, "Table Gate")
        table_answers = table_root / "inbox" / "answers.json"
        table_abstract = "Valid escaped table claims should survive the proposal checker."
        table_hypotheses = ["claim one --- with dashes", "claim with a | pipe char"]
        proposal_answers(table_answers, table_abstract, table_hypotheses)
        table_paper = Path(
            run_ok(
                propose_command(
                    table_root,
                    "Escaped Table Paper",
                    table_abstract,
                    table_hypotheses,
                    table_answers,
                )
            ).stdout.strip()
        )
        run_ok([sys.executable, script("check_closed_loop_paper.py"), str(table_paper), "--phase", "draft"])
        run_ok([sys.executable, script("pipeline.py"), str(table_root), "--strict"])
        run_ok([sys.executable, script("combine_papers.py"), str(table_root), "--last", "1"])

        schema_root = project / "schema-gate" / ".paper-stack"
        init(schema_root, "Schema Gate")
        schema_paper = create_edge_paper(schema_root, "Schema Gate Bypass")
        schema_config = schema_root / "config" / "loop-paper.json"
        schema_payload = json.loads(schema_config.read_text(encoding="utf-8"))
        schema_payload["proposal_gate"] = {"required_from": "PAPER-0001"}
        schema_config.write_text(json.dumps(schema_payload, indent=2) + "\n", encoding="utf-8")
        schema_paper.write_text(
            schema_paper.read_text(encoding="utf-8")
            .replace("paper_kind: closed_loop", "paper_kind: review\nreview_targets: PAPER-0001", 1),
            encoding="utf-8",
        )
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(schema_paper),
                "--phase",
                "structural",
            ],
            "missing proposal_record",
        )

        force_root = project / "force-gate" / ".paper-stack"
        init(force_root, "Force Gate")
        force_paper = create_edge_paper(force_root, "Force Accepted Bypass")
        run_fail(
            [
                sys.executable,
                script("transition_paper.py"),
                str(force_paper),
                "Accepted",
                "--force",
            ],
            "--force cannot bypass gates into Accepted",
        )

        race_root = project / "race-gate" / ".paper-stack"
        init(race_root, "Race Gate")
        first_answers = race_root / "inbox" / "race-one.json"
        second_answers = race_root / "inbox" / "race-two.json"
        proposal_answers(first_answers, "Race one framing.", ["Race one first", "Race one second"])
        proposal_answers(second_answers, "Race two framing.", ["Race two first", "Race two second"])
        commands = [
            propose_command(
                race_root,
                "Race One",
                "Race one framing.",
                ["Race one first", "Race one second"],
                first_answers,
            ),
            propose_command(
                race_root,
                "Race Two",
                "Race two framing.",
                ["Race two first", "Race two second"],
                second_answers,
            ),
        ]
        processes = [
            subprocess.Popen(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for command in commands
        ]
        outputs = [process.communicate(timeout=20) + (process.returncode,) for process in processes]
        for stdout, stderr, returncode in outputs:
            if returncode != 0:
                raise SystemExit(f"Concurrent proposal failed:\n{stdout}{stderr}")
        paper_ids = sorted(path.name.split("-", 2)[1] for path in race_root.glob("papers/PAPER-*.html"))
        if paper_ids != ["0001", "0002"]:
            raise SystemExit(f"Concurrent proposal allocation did not produce unique IDs: {paper_ids}")
        proposal_ids = sorted(path.name.removeprefix("PROPOSAL-PAPER-").removesuffix(".json") for path in race_root.glob("proposals/PROPOSAL-PAPER-*.json"))
        if proposal_ids != ["0001", "0002"]:
            raise SystemExit(f"Concurrent proposal records did not preserve unique IDs: {proposal_ids}")


def ensure_guard_hook() -> None:
    with tempfile.TemporaryDirectory(prefix="loop-paper-hook-") as tmp:
        project = Path(tmp)
        root = project / ".paper-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(root),
                "--project-name",
                "Guard Hook Edge",
                "--date",
                "2026-06-10",
            ]
        )
        hook = root / "hooks" / "guard_paper_loop.py"
        if not hook.is_file():
            raise SystemExit("init did not install the guard hook script")
        settings = json.loads((project / ".claude" / "settings.json").read_text(encoding="utf-8"))
        commands = [
            entry["command"]
            for matcher in settings.get("hooks", {}).get("PreToolUse", [])
            for entry in matcher.get("hooks", [])
        ]
        if not any("guard_paper_loop.py" in command for command in commands):
            raise SystemExit("init did not register the guard hook in .claude/settings.json")
        if sys.executable not in " ".join(commands):
            raise SystemExit("guard hook registration did not use the current Python executable")
        if not any("Bash" in entry.get("matcher", "") for entry in settings.get("hooks", {}).get("PreToolUse", [])):
            raise SystemExit("guard hook registration did not include Bash in the matcher")

        def guard_payload(tool_input: dict, tool_name: str = "Write") -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [sys.executable, str(hook)],
                input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
                text=True,
                capture_output=True,
                check=False,
                env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)},
            )

        def guard(file_path: Path) -> subprocess.CompletedProcess[str]:
            return guard_payload({"file_path": str(file_path)})

        blocked = guard(project / "src" / "app.py")
        if blocked.returncode != 2 or "Blocked by loop-paper" not in blocked.stderr:
            raise SystemExit("guard hook did not block edits without an open paper")
        protected = guard(root / "papers" / "PAPER-0001-x.html")
        if protected.returncode != 2 or "protected paper-stack artifact" not in protected.stderr:
            raise SystemExit("guard hook did not block protected stack artifact edits without an open paper")
        if guard(root / "inbox" / "note.txt").returncode != 0:
            raise SystemExit("guard hook blocked a non-protected edit inside the paper stack")
        notebook = guard_payload({"notebook_path": str(project / "notebooks" / "analysis.ipynb")}, "NotebookEdit")
        if notebook.returncode != 2:
            raise SystemExit("guard hook did not block NotebookEdit without an open paper")
        bash = guard_payload({"command": "echo hacked > src/app.py"}, "Bash")
        if bash.returncode != 2:
            raise SystemExit("guard hook did not block an obvious Bash write without an open paper")
        bash_read = guard_payload({"command": "python3 -m pytest --version"}, "Bash")
        if bash_read.returncode != 0:
            raise SystemExit("guard hook blocked a Bash command with no obvious write target")
        disable_proposal_gate(root)
        create_edge_paper(root, "Open Paper")
        if guard(project / "src" / "app.py").returncode != 0:
            raise SystemExit("guard hook blocked edits while a paper is open")
        if guard_payload({"command": "echo ok > src/app.py"}, "Bash").returncode != 0:
            raise SystemExit("guard hook blocked Bash writes while a paper is open")
        # Re-running init must not duplicate the hook registration.
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(root),
                "--project-name",
                "Guard Hook Edge",
                "--date",
                "2026-06-10",
            ]
        )
        settings = json.loads((project / ".claude" / "settings.json").read_text(encoding="utf-8"))
        commands = [
            entry["command"]
            for matcher in settings.get("hooks", {}).get("PreToolUse", [])
            for entry in matcher.get("hooks", [])
        ]
        if sum("guard_paper_loop.py" in command for command in commands) != 1:
            raise SystemExit("re-running init duplicated the guard hook registration")
        nested_project = project / "nested-project"
        nested_root = nested_project / "sub" / "workspace" / ".paper-stack"
        nested_project.mkdir()
        run_ok_cwd(["git", "init"], nested_project)
        run_ok_cwd(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(nested_root),
                "--project-name",
                "Nested Guard Hook Edge",
                "--date",
                "2026-06-10",
            ],
            nested_project,
        )
        nested_settings = nested_project / ".claude" / "settings.json"
        misplaced_settings = nested_root.parent / ".claude" / "settings.json"
        if not nested_settings.is_file() or misplaced_settings.exists():
            raise SystemExit("nested root hook registration did not target the git project root")
        nested_payload = json.loads(nested_settings.read_text(encoding="utf-8"))
        nested_commands = [
            entry["command"]
            for matcher in nested_payload.get("hooks", {}).get("PreToolUse", [])
            for entry in matcher.get("hooks", [])
        ]
        if not any("sub/workspace/.paper-stack/hooks/guard_paper_loop.py" in command for command in nested_commands):
            raise SystemExit("nested root hook command is not project-relative")
        invalid_settings_project = project / "invalid-settings"
        invalid_root = invalid_settings_project / ".paper-stack"
        (invalid_settings_project / ".claude").mkdir(parents=True)
        (invalid_settings_project / ".claude" / "settings.json").write_text(
            json.dumps({"hooks": {"PreToolUse": {"not": "a list"}}}) + "\n",
            encoding="utf-8",
        )
        run_fail(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(invalid_root),
                "--project-name",
                "Invalid Settings Hook Edge",
                "--date",
                "2026-06-10",
            ],
            "Expected hooks.PreToolUse to be a JSON array",
        )


def ensure_propose_paper_rejections() -> None:
    with tempfile.TemporaryDirectory(prefix="loop-paper-propose-") as tmp:
        root = Path(tmp) / ".paper-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(root),
                "--project-name",
                "Loop Paper Propose Edge",
                "--date",
                "2026-06-10",
            ]
        )
        base = [
            sys.executable,
            script("propose_paper.py"),
            "--root",
            str(root),
            "--title",
            "Propose Edge",
            "--date",
            "2026-06-10",
        ]
        abstracts = [
            "--candidate-abstract",
            "Framing A",
            "--candidate-abstract",
            "Framing B",
        ]
        sets = [
            "--candidate-set",
            "Claim one||Claim two",
            "--candidate-set",
            "Alt one||Alt two",
        ]
        run_fail(
            base + ["--candidate-abstract", "Only framing"] + sets + ["--format", "json"],
            "Need at least 2 --candidate-abstract values",
        )
        run_fail(
            base
            + ["--candidate-abstract", "Same", "--candidate-abstract", "Same"]
            + sets
            + ["--format", "json"],
            "--candidate-abstract values must be unique",
        )
        run_fail(
            base + abstracts + ["--candidate-set", "Claim one||Claim two", "--format", "json"],
            "Need at least 2 --candidate-set values",
        )
        run_fail(
            base
            + abstracts
            + ["--candidate-set", "Lone claim", "--candidate-set", "Claim one||Claim two"]
            + ["--format", "json"],
            "must have >= 2 hypotheses",
        )
        run_fail(
            base
            + abstracts
            + ["--candidate-set", "a | b||c d", "--candidate-set", "a||b | c d"]
            + ["--format", "json"],
            "must render unique option labels",
        )
        run_fail(
            base + abstracts + sets + ["--format", "json"],
            "Need at least 1 --finding",
        )
        finding = ["--finding", "Edge research finding with captured baseline"]
        answers = root / "inbox" / "answers.json"
        answers.write_text(
            json.dumps(
                {
                    "abstract": "Framing C",
                    "hypothesis_set": "Claim one | Claim two",
                    "gate": "Implement now",
                }
            ),
            encoding="utf-8",
        )
        run_fail(
            base + abstracts + sets + finding + ["--answers", str(answers)],
            "answer for abstract not in options",
        )
        if list((root / "proposals").glob("*.json")):
            raise SystemExit("Rejected proposal answers still wrote a proposal record")
        answers.write_text(
            json.dumps(
                {
                    "abstract": "Framing A",
                    "hypothesis_set": "Claim one | Claim two",
                    "gate": "Implement now",
                }
            ),
            encoding="utf-8",
        )
        proposed = Path(
            run_ok(base + abstracts + sets + finding + ["--answers", str(answers)]).stdout.strip()
        )
        proposed.write_text(
            proposed.read_text(encoding="utf-8").replace("Framing A", "Rewritten framing", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(root)],
            "abstract drifted",
        )


def ensure_failure_proof_gates() -> None:
    with tempfile.TemporaryDirectory(prefix="loop-paper-failure-") as tmp:
        root = Path(tmp) / ".paper-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(root),
                "--project-name",
                "Loop Paper Failure Proof Edge",
                "--date",
                "2026-06-10",
            ]
        )
        failed = create_edge_paper(root, "Failed Hypothesis Target")
        run_fail(
            [sys.executable, script("transition_paper.py"), str(failed), "Rejected"],
            "rejected phase incomplete",
        )
        text = failed.read_text(encoding="utf-8")
        text = re.sub(r"(?m)^(\| H\d+ \|.*\| )Open( \|)$", r"\1Failed\2", text)
        text = text.replace(
            "- BEFORE_REQUIRED: exact baseline output or inspected evidence",
            "- Baseline output captured before the attempt",
        )
        text = text.replace(
            "- AFTER_REQUIRED: exact post-change output or inspected evidence",
            "- Attempt output captured: change produced no measurable effect",
        )
        text = text.replace(
            "- AFTER_REQUIRED: mark each hypothesis Supported, Failed, Inconclusive, or\n"
            "  Superseded in both the Hypothesis Ledger Verdict column and this block,\n"
            "  with the evidence reason.",
            "- Failed: the attempt output shows no measurable effect.",
        )
        failed.write_text(text, encoding="utf-8")
        run_ok([sys.executable, script("transition_paper.py"), str(failed), "Rejected"])
        run_ok([sys.executable, script("pipeline.py"), str(root)])

        superseding = create_edge_paper(root, "Superseding Source")
        run_fail(
            [sys.executable, script("transition_paper.py"), str(superseding), "Superseded"],
            "Superseded requires another paper declaring Supersedes",
        )
        superseding.write_text(
            superseding.read_text(encoding="utf-8").replace(
                "Supersedes: None", "Supersedes: PAPER-0001", 1
            ),
            encoding="utf-8",
        )
        run_ok([sys.executable, script("transition_paper.py"), str(failed), "Superseded"])
        run_ok([sys.executable, script("pipeline.py"), str(root)])
        superseding.write_text(
            superseding.read_text(encoding="utf-8").replace(
                "Supersedes: PAPER-0001", "Supersedes: None", 1
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(root)],
            "Superseded without any paper declaring Supersedes",
        )


def ensure_attestation_gates() -> None:
    with tempfile.TemporaryDirectory(prefix="loop-paper-attest-") as tmp:
        root = Path(tmp) / ".paper-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(root),
                "--project-name",
                "Loop Paper Attestation Edge",
                "--date",
                "2026-06-10",
            ]
        )
        paper = create_edge_paper(root, "Attestation Target")
        text = after_ready_text(paper)
        text = mark_checkboxes(
            text,
            AFTER_READY_CHECKBOXES,
        )
        text = text.replace(RECORDED_VERDICT_INSTRUCTION, "- Supported: attested evidence recorded.")
        text = text.replace(
            "Recorded: state the work unit, why it matters, and what completion would prove. If this is retrospective, say so explicitly.",
            "Attestation gate target. Verdict: Supported. Next step: none.",
            1,
        )
        paper.write_text(text, encoding="utf-8")
        run_ok([sys.executable, script("check_closed_loop_paper.py"), str(paper), "--phase", "after"])

        edge_record = root / "runs" / "RUN-2026-06-10-PAPER-0001-edge.md"
        edge_record_text = edge_record.read_text(encoding="utf-8")
        if "attestation: loop_paper.run_attestation.v2" not in edge_record_text:
            raise SystemExit("execute_run.py did not write a v2 run attestation")
        edge_record.write_text(
            re.sub(r"^command: .*$", "command: fabricated", edge_record_text, count=1, flags=re.MULTILINE),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(paper), "--phase", "after"],
            "attestation digest mismatch in run record RUN-2026-06-10-PAPER-0001-edge",
        )
        edge_record.write_text(edge_record_text, encoding="utf-8")

        run_ok(
            [
                sys.executable,
                script("execute_run.py"),
                "--root",
                str(root),
                "--paper",
                "PAPER-0001",
                "--label",
                "failing",
                "--date",
                "2026-06-10",
                "--",
                sys.executable,
                "-c",
                "print('failing run'); raise SystemExit(3)",
            ]
        )
        paper.write_text(
            text.replace(
                "- 2026-06-10 Attested evidence: RUN-2026-06-10-PAPER-0001-edge",
                "- 2026-06-10 Failing evidence: RUN-2026-06-10-PAPER-0001-failing",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(paper), "--phase", "after"],
            "run record RUN-2026-06-10-PAPER-0001-failing has nonzero exit_code: 3",
        )
        paper.write_text(text, encoding="utf-8")

        run_ok(
            [
                sys.executable,
                script("execute_run.py"),
                "--root",
                str(root),
                "--paper",
                "PAPER-0001",
                "--label",
                "separator",
                "--date",
                "2026-06-10",
                "--",
                sys.executable,
                "-c",
                "import sys; print(sys.argv[1:])",
                "--",
                "kept",
            ]
        )
        separator_text = (root / "runs" / "RUN-2026-06-10-PAPER-0001-separator.md").read_text(encoding="utf-8")
        if " -- kept" not in separator_text or "['--', 'kept']" not in separator_text:
            raise SystemExit("execute_run.py did not preserve command separator arguments")

        run_ok(
            [
                sys.executable,
                script("execute_run.py"),
                "--root",
                str(root),
                "--paper",
                "PAPER-0001",
                "--label",
                "binary",
                "--date",
                "2026-06-10",
                "--",
                sys.executable,
                "-c",
                "import sys; sys.stdout.buffer.write(b'\\xff')",
            ]
        )
        binary_text = (root / "runs" / "RUN-2026-06-10-PAPER-0001-binary.md").read_text(encoding="utf-8")
        if "\ufffd" not in binary_text:
            raise SystemExit("execute_run.py did not replacement-decode non-UTF-8 output")

        unchecked_todo = text.replace(
            "- [x] Recorded: first implementation step tied to a hypothesis",
            "- [ ] Recorded: first implementation step tied to a hypothesis",
            1,
        )
        paper.write_text(unchecked_todo, encoding="utf-8")
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(paper), "--phase", "after"],
            "implementation TODO items are not all checked",
        )
        paper.write_text(text, encoding="utf-8")

        bare = text.replace(
            "- 2026-06-10 Attested evidence: RUN-2026-06-10-PAPER-0001-edge",
            "- All tests pass, trust me",
            1,
        )
        paper.write_text(bare, encoding="utf-8")
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(paper), "--phase", "after"],
            "must reference an attested RUN-* record",
        )

        forged = root / "runs" / "RUN-2026-06-10-PAPER-0001-forged.md"
        forged.write_text(
            "# RUN-2026-06-10-PAPER-0001-forged\n\n"
            "attestation: loop_paper.run_attestation.v1\n"
            "command: fabricated\n"
            "exit_code: 0\n"
            "output_sha256: " + "0" * 64 + "\n\n"
            "- Date: 2026-06-10\n"
            "- Related paper: PAPER-0001\n\n"
            "## Output\n\n````text\nAll 9999 tests passed.\n````\n",
            encoding="utf-8",
        )
        paper.write_text(
            text.replace(
                "- 2026-06-10 Attested evidence: RUN-2026-06-10-PAPER-0001-edge",
                "- 2026-06-10 Fabricated evidence: RUN-2026-06-10-PAPER-0001-forged",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(paper), "--phase", "after"],
            "attestation digest mismatch in run record RUN-2026-06-10-PAPER-0001-forged",
        )

        unattested = root / "runs" / "RUN-2026-06-10-PAPER-0001-handwritten.md"
        unattested.write_text("# RUN handwritten\n\nAll tests passed.\n", encoding="utf-8")
        paper.write_text(
            text.replace(
                "- 2026-06-10 Attested evidence: RUN-2026-06-10-PAPER-0001-edge",
                "- 2026-06-10 Hand-written evidence: RUN-2026-06-10-PAPER-0001-handwritten",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(paper), "--phase", "after"],
            "run record RUN-2026-06-10-PAPER-0001-handwritten is not attested",
        )

        run_fail(
            [
                sys.executable,
                script("execute_run.py"),
                "--root",
                str(root),
                "--paper",
                "PAPER-0001",
                "--label",
                "Bad_Label",
                "--date",
                "2026-06-10",
                "--",
                sys.executable,
                "-c",
                "print('x')",
            ],
            "--label must contain only lowercase letters",
        )
        run_fail(
            [
                sys.executable,
                script("execute_run.py"),
                "--root",
                str(root),
                "--paper",
                "PAPER-0009",
                "--label",
                "ghost",
                "--date",
                "2026-06-10",
                "--",
                sys.executable,
                "-c",
                "print('x')",
            ],
            "Unknown paper in stack: PAPER-0009",
        )
        run_fail(
            [
                sys.executable,
                script("execute_run.py"),
                "--root",
                str(root),
                "--paper",
                "PAPER-0001",
                "--label",
                "edge",
                "--date",
                "2026-06-10",
                "--",
                sys.executable,
                "-c",
                "print('x')",
            ],
            "Refusing to overwrite existing run record",
        )


def ensure_interaction_review_gate() -> None:
    with tempfile.TemporaryDirectory(prefix="loop-paper-interact-") as tmp:
        root = Path(tmp) / ".paper-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(root),
                "--project-name",
                "Loop Paper Interaction Edge",
                "--date",
                "2026-06-10",
            ]
        )
        paper = create_edge_paper(root, "Interactive Target")
        text = paper.read_text(encoding="utf-8")
        paper.write_text(
            text.replace(
                "## Prior Research",
                "### Diagram\n\n```html\n<svg width=\"10\" height=\"10\"></svg>\n```\n\n## Prior Research",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(root),
                "--title",
                "Blocked Next Paper",
                "--hypothesis",
                "a",
                "--hypothesis",
                "b",
                "--finding",
                "f",
                "--date",
                "2026-06-10",
            ],
            "Interactive papers pending human review: PAPER-0001",
        )
        run_fail(
            [
                sys.executable,
                script("ack_interaction.py"),
                "--root",
                str(root),
                "--paper",
                "PAPER-0002",
                "--status",
                "reviewed",
                "--date",
                "2026-06-10",
            ],
            "Unknown paper in stack: PAPER-0002",
        )
        run_ok(
            [
                sys.executable,
                script("ack_interaction.py"),
                "--root",
                str(root),
                "--paper",
                "PAPER-0001",
                "--status",
                "reviewed",
                "--date",
                "2026-06-10",
            ]
        )
        if "interaction_review: reviewed 2026-06-10" not in paper.read_text(encoding="utf-8"):
            raise SystemExit("Interaction review was not recorded in frontmatter")
        run_ok(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(root),
                "--title",
                "Unblocked Next Paper",
                "--hypothesis",
                "a",
                "--hypothesis",
                "b",
                "--finding",
                "f",
                "--date",
                "2026-06-10",
            ]
        )


def main() -> int:
    ensure_artifact_integrity_roundtrips()
    ensure_workflow_docs_are_current()
    ensure_proposal_gate_enforcement()
    ensure_deterministic_gate_hardening()
    ensure_guard_hook()
    ensure_propose_paper_rejections()
    ensure_interaction_review_gate()
    ensure_attestation_gates()
    ensure_failure_proof_gates()
    ensure_validator_ignores_local_paper_stack()
    ensure_validator_rejects_malformed_skill_frontmatter()
    ensure_validator_handles_missing_git()
    ensure_installed_payload_validates()
    ensure_installer_rejects_recursive_destinations()
    ensure_installer_rejects_file_parent()
    ensure_installer_replaces_broken_symlink()
    ensure_installer_force_copy_replaces_source_symlink()

    with tempfile.TemporaryDirectory(prefix="loop-paper-edge-") as tmp:
        project = Path(tmp)
        root = project / ".paper-stack"
        root_file = project / "paper-stack-file"
        root_file.write_text("not a directory", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(root_file),
                "--project-name",
                "Root File Stack",
                "--date",
                "2026-06-10",
            ],
            f"Expected paper stack root, got file: {root_file}",
        )
        root_parent_file = project / "root-parent-file"
        root_parent_file.write_text("not a directory", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(root_parent_file / "nested-stack"),
                "--project-name",
                "Nested Root File Stack",
                "--date",
                "2026-06-10",
            ],
            f"Expected parent directory for paper stack root, got file: {root_parent_file}",
        )
        run_fail(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(project / "bad-date-stack"),
                "--project-name",
                "Bad Date Stack",
                "--date",
                "2026-02-30",
            ],
            "--date must be a valid calendar date",
        )
        bad_project_name_root = project / "bad-project-name-stack"
        run_fail(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(bad_project_name_root),
                "--project-name",
                "Bad\nName",
                "--date",
                "2026-06-10",
            ],
            "--project-name must not contain newlines or '---'",
        )
        if bad_project_name_root.exists():
            raise SystemExit("Invalid project name created a partial paper stack root")
        bad_seed_title_root = project / "bad-seed-title-stack"
        run_fail(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(bad_seed_title_root),
                "--project-name",
                "Bad Seed Title Stack",
                "--seed-paper",
                "--seed-title",
                "Bad: Title",
                "--date",
                "2026-06-10",
            ],
            "--seed-title must not contain ':', newlines, or '---'",
        )
        if bad_seed_title_root.exists():
            raise SystemExit("Invalid seed title created a partial paper stack root")
        colon_seed_root = project / "colon-seed-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(colon_seed_root),
                "--project-name",
                "Colon: Name",
                "--seed-paper",
                "--date",
                "2026-06-10",
            ]
        )
        colon_seed_papers = sorted((colon_seed_root / "papers").glob("PAPER-*.html"))
        if len(colon_seed_papers) != 1:
            raise SystemExit("Colon project seed initialization did not create exactly one paper")
        colon_seed_text = colon_seed_papers[0].read_text(encoding="utf-8")
        if "title: Initialize Colon - Name Loop Paper" not in colon_seed_text:
            raise SystemExit("Colon project seed title was not sanitized in frontmatter")
        if "# PAPER-0001 Initialize Colon - Name Loop Paper" not in colon_seed_text:
            raise SystemExit("Colon project seed title was not sanitized in heading")
        run_ok([sys.executable, script("check_paper.py"), str(colon_seed_root)])
        seed_idempotent_root = project / "seed-idempotent-stack"
        first_seed = run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(seed_idempotent_root),
                "--project-name",
                "Seed Idempotent Stack",
                "--seed-paper",
                "--date",
                "2026-06-10",
            ]
        )
        first_seed_summary = json.loads(first_seed.stdout)
        if first_seed_summary.get("seed_paper_skipped"):
            raise SystemExit("First seed initialization was incorrectly skipped")
        second_seed = run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(seed_idempotent_root),
                "--project-name",
                "Seed Idempotent Stack",
                "--seed-paper",
                "--date",
                "2026-06-10",
            ]
        )
        second_seed_summary = json.loads(second_seed.stdout)
        if second_seed_summary.get("seed_paper") is not None:
            raise SystemExit("Repeated seed initialization created a duplicate paper")
        if second_seed_summary.get("seed_paper_skipped") is not True:
            raise SystemExit("Repeated seed initialization did not report skipped seed paper")
        seed_idempotent_papers = sorted((seed_idempotent_root / "papers").glob("PAPER-*.html"))
        if [path.name for path in seed_idempotent_papers] != [
            "PAPER-0001-initialize-seed-idempotent-stack-loop-paper.html"
        ]:
            raise SystemExit("Repeated seed initialization changed the paper set")
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(root),
                "--project-name",
                "Loop Paper Edge Cases",
                "--date",
                "2026-06-10",
            ]
        )
        config = json.loads((root / "config" / "loop-paper.json").read_text(encoding="utf-8"))
        expected_generated_outputs = {
            "dashboard/data.json",
            "dashboard/index.html",
            "dashboard/references.json",
            "dashboard/impact-scores.json",
            "dashboard/report.md",
            "dashboard/pipeline-summary.json",
        }
        actual_generated_outputs = set(config.get("generated_outputs", []))
        if actual_generated_outputs != expected_generated_outputs:
            raise SystemExit(
                "Initialized generated_outputs mismatch: "
                + ", ".join(sorted(actual_generated_outputs))
            )
        relative_name_project = project / "relative-name-project"
        relative_name_project.mkdir()
        run_ok_cwd(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                ".paper-stack",
                "--date",
                "2026-06-10",
            ],
            cwd=relative_name_project,
        )
        relative_config = json.loads(
            (relative_name_project / ".paper-stack" / "config" / "loop-paper.json").read_text(
                encoding="utf-8"
            )
        )
        if relative_config.get("project_name") != "Relative Name Project":
            raise SystemExit(
                "Relative .paper-stack default project_name mismatch: "
                + str(relative_config.get("project_name"))
            )
        empty_strict_root = project / "empty-strict-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(empty_strict_root),
                "--project-name",
                "Loop Paper Empty Strict Edge",
                "--date",
                "2026-06-10",
            ]
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(empty_strict_root), "--strict"],
            "FAIL no papers found",
        )
        empty_summary = empty_strict_root / "dashboard" / "pipeline-summary.json"
        if not empty_summary.exists():
            raise SystemExit("Strict empty pipeline did not write failure summary")
        empty_summary_payload = json.loads(empty_summary.read_text(encoding="utf-8"))
        if empty_summary_payload.get("paper_count") != 0:
            raise SystemExit("Strict empty pipeline summary did not record paper_count=0")
        if empty_summary_payload.get("check_passed") is not False:
            raise SystemExit("Strict empty pipeline summary did not record check_passed=false")
        empty_blocked_outputs = [
            empty_strict_root / "dashboard" / "references.json",
            empty_strict_root / "dashboard" / "impact-scores.json",
            empty_strict_root / "dashboard" / "index.html",
            empty_strict_root / "dashboard" / "report.md",
        ]
        empty_written = [str(path) for path in empty_blocked_outputs if path.exists()]
        if empty_written:
            raise SystemExit("Strict empty pipeline wrote generated outputs: " + ", ".join(empty_written))
        papers_file_root = project / "creator-papers-file-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(papers_file_root),
                "--project-name",
                "Loop Paper Creator Papers File Edge",
                "--date",
                "2026-06-10",
            ]
        )
        creator_papers_file = papers_file_root / "papers"
        creator_papers_file.rmdir()
        creator_papers_file.write_text("not a directory", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(papers_file_root),
                "--title",
                "Papers File Paper",
                "--hypothesis",
                "Papers path should be a directory",
                "--finding",
                "Creation needs deterministic directory errors",
                "--reference",
                "scripts/edge_case_test.py",
                "--date",
                "2026-06-10",
            ],
            f"Expected papers directory, got file: {creator_papers_file}",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(papers_file_root),
                "--title",
                "Papers File Review",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
                "--date",
                "2026-06-10",
            ],
            f"Expected papers directory, got file: {creator_papers_file}",
        )
        missing_review_root = project / "missing-review-root"
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(missing_review_root),
                "--title",
                "Missing Root Review",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
                "--date",
                "2026-06-10",
            ],
            f"Missing papers directory: {missing_review_root / 'papers'}",
        )
        if missing_review_root.exists():
            raise SystemExit("Review paper creation initialized a missing root unexpectedly")
        missing_closed_loop_root = project / "missing-closed-loop-root"
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(missing_closed_loop_root),
                "--title",
                "Missing Root Paper",
                "--hypothesis",
                "Closed-loop creation should require initialization",
                "--finding",
                "Partial paper-stack roots omit generated structure",
                "--reference",
                "scripts/edge_case_test.py",
                "--date",
                "2026-06-10",
            ],
            f"Missing papers directory: {missing_closed_loop_root / 'papers'}",
        )
        if missing_closed_loop_root.exists():
            raise SystemExit("Closed-loop paper creation initialized a missing root unexpectedly")
        disable_proposal_gate(root)
        created = Path(
            run_ok(
                [
                    sys.executable,
                    script("new_closed_loop_paper.py"),
                    "--root",
                    str(root),
                    "--title",
                    "Edge Target",
                    "--hypothesis",
                    "Edge tests can target a paper",
                    "--finding",
                    "Edge tests need at least one paper",
                    "--reference",
                    "scripts/edge_case_test.py",
                    "--date",
                    "2026-06-10",
                ]
            ).stdout.strip()
        )
        if "paper_kind: closed_loop" not in created.read_text(encoding="utf-8"):
            raise SystemExit("Closed-loop paper did not declare paper_kind: closed_loop")
        linked = Path(
            run_ok(
                [
                    sys.executable,
                    script("new_closed_loop_paper.py"),
                    "--root",
                    str(root),
                    "--title",
                    "Referenced Edge Target",
                    "--hypothesis",
                    "Paper ID references should become graph edges",
                    "--finding",
                    "Reference relationship lines drive graph and impact scoring",
                    "--reference",
                    "PAPER-0001",
                    "--date",
                    "2026-06-10",
                ]
            ).stdout.strip()
        )
        if "References: PAPER-0001" not in linked.read_text(encoding="utf-8"):
            raise SystemExit("Closed-loop paper did not mirror PAPER reference into relationship lines")
        run_ok([sys.executable, script("check_paper.py"), str(root)])
        before_unknown_reference_count = len(list((root / "papers").glob("PAPER-*.html")))
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(root),
                "--title",
                "Unknown Reference Target",
                "--hypothesis",
                "Unknown paper references should be rejected before writes",
                "--finding",
                "Dangling relationship lines break deterministic graph outputs",
                "--reference",
                "PAPER-9999",
                "--date",
                "2026-06-10",
            ],
            "Reference list contains unknown paper IDs: PAPER-9999",
        )
        if len(list((root / "papers").glob("PAPER-*.html"))) != before_unknown_reference_count:
            raise SystemExit("Unknown paper reference created a partial paper")
        standalone = project / "PAPER-0001-standalone.md"
        standalone.write_text(created.read_text(encoding="utf-8"), encoding="utf-8")
        run_ok([sys.executable, script("check_paper.py"), str(standalone)])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(standalone), "Rejected"],
            "rejected phase incomplete",
        )
        run_ok([sys.executable, script("transition_paper.py"), str(standalone), "Rejected", "--force"])
        if "status: Rejected" not in standalone.read_text(encoding="utf-8"):
            raise SystemExit("Standalone transition did not update status frontmatter")
        escaped = Path(
            run_ok(
                [
                    sys.executable,
                    script("new_closed_loop_paper.py"),
                    "--root",
                    str(root),
                    "--title",
                    "Pipe | Title",
                    "--hypothesis",
                    "Pipe | claim\nwith newline",
                    "--finding",
                    "Finding | data\nsecond line",
                    "--reference",
                    "docs/reference | one\nsecond",
                    "--date",
                    "2026-06-10",
                ]
            ).stdout.strip()
        )
        from paper_html import read_paper_text

        escaped_text = read_paper_text(escaped)
        if "| H1 | Pipe \\| claim with newline |" not in escaped_text:
            raise SystemExit("Generated hypothesis table did not escape pipe/newline input")
        if "| 2026-06-10 | Finding \\| data second line |" not in escaped_text:
            raise SystemExit("Generated findings table did not escape pipe/newline input")
        if "- docs/reference | one second" not in escaped_text:
            raise SystemExit("Generated reference list did not collapse newline input")
        fenced_heading = create_edge_paper(root, "Fenced Heading Edge")
        fenced_heading.write_text(
            fenced_heading.read_text(encoding="utf-8").replace(
                "Record actual evidence only after execution or inspection.",
                "Record actual evidence only after execution or inspection.\n\n"
                "```md\n"
                "## Impact Score\n"
                "# PAPER-9999 Not A Real Heading\n"
                "```\n",
                1,
            ),
            encoding="utf-8",
        )
        run_ok([sys.executable, script("check_paper.py"), str(fenced_heading)])
        run_ok([sys.executable, script("check_paper.py"), str(root)])
        script_title = Path(
            run_ok(
                [
                    sys.executable,
                    script("new_closed_loop_paper.py"),
                    "--root",
                    str(root),
                    "--title",
                    "Script </script> Edge",
                    "--hypothesis",
                    "Dashboard JSON should not close inline scripts",
                    "--finding",
                    "Generated dashboards embed paper metadata in JavaScript",
                    "--reference",
                    "scripts/edge_case_test.py",
                    "--date",
                    "2026-06-10",
                ]
            ).stdout.strip()
        )
        run_ok([sys.executable, script("render_dashboard.py"), str(root)])
        dashboard_html = (root / "dashboard" / "index.html").read_text(encoding="utf-8")
        if "Script </script> Edge" in dashboard_html:
            raise SystemExit("Dashboard embedded an unescaped script-closing title")
        if "Script <\\/script> Edge" not in dashboard_html:
            raise SystemExit("Dashboard did not preserve escaped script-closing title")
        if not script_title.exists():
            raise SystemExit("Script-title paper was not created")
        report_output = root / "dashboard" / "pipe-report.md"
        run_ok(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ]
        )
        report_text = report_output.read_text(encoding="utf-8")
        if "Pipe \\| Title" not in report_text:
            raise SystemExit("Exported report table did not escape title pipe")
        impact_scores = root / "dashboard" / "impact-scores.json"
        run_ok([sys.executable, script("score_impact.py"), str(root)])
        impact_payload = json.loads(impact_scores.read_text(encoding="utf-8"))
        script_title_id = re.match(r"(PAPER-\d{4})", script_title.name).group(1)
        script_title_score = next(
            item for item in impact_payload["papers"] if item["paper_id"] == script_title_id
        )
        if script_title_score.get("deterministic_score") != "TBD":
            raise SystemExit("Impact scorer fabricated a full score with missing measured outcome")
        if script_title_score.get("deterministic_partial_score") != 0.99:
            raise SystemExit("Impact scorer did not use weighted partial formula")
        relation_impact_root = project / "relation-impact-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(relation_impact_root),
                "--project-name",
                "Loop Paper Relation Impact Edge",
                "--date",
                "2026-06-10",
            ]
        )
        create_edge_paper(relation_impact_root, "Contradicted Impact Target")
        contradicting_source = create_edge_paper(relation_impact_root, "Contradicting Impact Source")
        contradicting_source.write_text(
            contradicting_source.read_text(encoding="utf-8").replace(
                "Contradicts: None",
                "Contradicts: PAPER-0001",
                1,
            ),
            encoding="utf-8",
        )
        run_ok([sys.executable, script("score_impact.py"), str(relation_impact_root)])
        relation_payload = json.loads(
            (relation_impact_root / "dashboard" / "impact-scores.json").read_text(encoding="utf-8")
        )
        contradicted_score = next(
            item for item in relation_payload["papers"] if item["paper_id"] == "PAPER-0001"
        )
        if contradicted_score["components"].get("downstream_reference_score") != 0:
            raise SystemExit("Impact scorer treated Contradicts as positive downstream impact")
        reference_impact_root = project / "reference-impact-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(reference_impact_root),
                "--project-name",
                "Loop Paper Reference Impact Edge",
                "--date",
                "2026-06-10",
            ]
        )
        create_edge_paper(reference_impact_root, "Referenced Impact Target")
        referencing_source = create_edge_paper(reference_impact_root, "Referencing Impact Source")
        referencing_source.write_text(
            referencing_source.read_text(encoding="utf-8").replace(
                "References: None",
                "References: PAPER-0001",
                1,
            ),
            encoding="utf-8",
        )
        run_ok([sys.executable, script("score_impact.py"), str(reference_impact_root)])
        reference_payload = json.loads(
            (reference_impact_root / "dashboard" / "impact-scores.json").read_text(encoding="utf-8")
        )
        referenced_score = next(
            item for item in reference_payload["papers"] if item["paper_id"] == "PAPER-0001"
        )
        if referenced_score["components"].get("downstream_reference_score") != 3:
            raise SystemExit("Impact scorer did not count References as positive downstream impact")
        measured_score_root = project / "measured-score-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(measured_score_root),
                "--project-name",
                "Loop Paper Measured Score Edge",
                "--date",
                "2026-06-10",
            ]
        )
        measured_score_paper = create_edge_paper(measured_score_root, "Measured Score Edge")
        measured_score_paper.write_text(
            measured_score_paper.read_text(encoding="utf-8").replace(
                "- Measured outcome: AFTER_REQUIRED: before/after delta or failed result",
                "- Measured outcome: score=8/10; latency dropped from 400ms to 250ms",
                1,
            ),
            encoding="utf-8",
        )
        run_ok([sys.executable, script("score_impact.py"), str(measured_score_root)])
        measured_payload = json.loads(
            (measured_score_root / "dashboard" / "impact-scores.json").read_text(
                encoding="utf-8"
            )
        )
        measured_item = measured_payload["papers"][0]
        if measured_item["components"].get("measured_outcome_score") != 8:
            raise SystemExit("Impact scorer did not parse explicit measured outcome score")
        if measured_item.get("deterministic_score") != 3.71:
            raise SystemExit("Impact scorer did not complete weighted measured outcome formula")
        if "explicit 0-10" not in measured_item.get("reason", ""):
            raise SystemExit("Impact scorer did not explain explicit measured outcome parsing")
        run_ok(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ]
        )
        report_text = report_output.read_text(encoding="utf-8")
        if "TBD (partial 0.99)" not in report_text:
            raise SystemExit("Exported report did not distinguish full impact from partial score")
        impact_scores.unlink()
        impact_scores.mkdir()
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            f"Expected impact scores JSON file, got directory: {impact_scores}",
        )
        impact_scores.rmdir()
        impact_scores.write_text("{", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "impact scores JSON is invalid",
        )
        impact_scores.write_text(json.dumps([]), encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "impact scores JSON must be an object",
        )
        impact_scores.write_text(json.dumps({"papers": {}}), encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "impact scores JSON field 'papers' must be a list",
        )
        impact_scores.write_text(json.dumps({"papers": [{}]}), encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "impact score paper item 1 missing paper_id",
        )
        impact_scores.write_text(json.dumps({"papers": [{"paper_id": "PAPER-1"}]}), encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "impact score paper item 1 has invalid paper_id: PAPER-1",
        )
        impact_scores.write_text(json.dumps({"papers": [{"paper_id": "PAPER-9999"}]}), encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "impact score references unknown paper_id: PAPER-9999",
        )
        impact_scores.write_text(
            json.dumps(
                {
                    "papers": [
                        {
                            "paper_id": "PAPER-0001",
                            "deterministic_score": "TBD",
                            "deterministic_partial_score": 0.99,
                        },
                        {
                            "paper_id": "PAPER-0001",
                            "deterministic_score": "TBD",
                            "deterministic_partial_score": 0.99,
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "duplicate impact score paper_id: PAPER-0001",
        )
        impact_scores.write_text(
            json.dumps(
                {
                    "papers": [
                        {
                            "paper_id": "PAPER-0001",
                            "deterministic_score": "TBD",
                            "deterministic_partial_score": 0.99,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "impact scores missing current paper_id",
        )
        current_score_items = []
        for path in sorted((root / "papers").glob("PAPER-*.html")):
            paper_id = "-".join(path.name.split("-", 2)[:2])
            current_score_items.append(
                {
                    "paper_id": paper_id,
                }
            )
        impact_scores.write_text(
            json.dumps(
                {
                    "papers": current_score_items
                }
            ),
            encoding="utf-8",
        )
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "impact score paper item 1 missing deterministic_score",
        )
        current_score_items[0]["deterministic_score"] = "A | B"
        current_score_items[0]["deterministic_partial_score"] = 0.99
        impact_scores.write_text(json.dumps({"papers": current_score_items}), encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "impact score paper item 1 deterministic_score must be TBD or a number from 0 to 10",
        )
        current_score_items[0]["deterministic_score"] = "TBD"
        current_score_items[0]["deterministic_partial_score"] = "A | B"
        impact_scores.write_text(json.dumps({"papers": current_score_items}), encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ],
            "impact score paper item 1 deterministic_partial_score must be a number from 0 to 10",
        )
        for item in current_score_items:
            item["deterministic_score"] = "TBD"
            item["deterministic_partial_score"] = 0.99
        impact_scores.write_text(json.dumps({"papers": current_score_items}), encoding="utf-8")
        run_ok(
            [
                sys.executable,
                script("export_report.py"),
                str(root),
                "--output",
                str(report_output),
            ]
        )
        if "TBD (partial 0.99)" not in report_output.read_text(encoding="utf-8"):
            raise SystemExit("Exported report did not render valid canonical score payload")
        impact_scores.unlink()
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(root),
                "--title",
                "Bad Date Paper",
                "--hypothesis",
                "Bad date should fail",
                "--finding",
                "Generated frontmatter dates must be deterministic ISO dates",
                "--reference",
                "scripts/edge_case_test.py",
                "--date",
                "20260610",
            ],
            "--date must be YYYY-MM-DD",
        )
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(root),
                "--title",
                "Bad Minimum Hypotheses",
                "--hypothesis",
                "Minimum hypotheses should be positive",
                "--finding",
                "Silent coercion hides invalid caller input",
                "--reference",
                "scripts/edge_case_test.py",
                "--min-hypotheses",
                "0",
            ],
            "--min-hypotheses must be >= 2 for paper_closed_loop.v3",
        )
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(root),
                "--title",
                "Bad Slug Paper",
                "--slug",
                "bad/path",
                "--hypothesis",
                "Bad slug should fail",
                "--finding",
                "Unsafe custom slugs can break deterministic output paths",
                "--reference",
                "scripts/edge_case_test.py",
            ],
            "--slug must contain only ASCII letters, numbers, and single hyphens",
        )
        missing_paper = root / "papers" / "PAPER-9999-missing.md"
        for command in [
            [sys.executable, script("check_paper.py"), str(missing_paper)],
            [sys.executable, script("check_closed_loop_paper.py"), str(missing_paper), "--phase", "before"],
            [sys.executable, script("transition_paper.py"), str(missing_paper), "Research Ready"],
            [sys.executable, script("agent_review.py"), str(missing_paper)],
            [sys.executable, script("update_paper_metadata.py"), str(missing_paper), "--check"],
        ]:
            run_fail(command, f"Missing paper file: {missing_paper}")

        review_repair = create_edge_paper(root, "Agent Review Repair Edge")
        repair_text = review_repair.read_text(encoding="utf-8")
        review_start = repair_text.index("\n## Agent Review\n")
        impact_start = repair_text.index("\n## Impact Score\n")
        review_repair.write_text(
            repair_text[:review_start] + repair_text[impact_start:],
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(review_repair)],
            "Agent Review",
        )
        run_ok([sys.executable, script("agent_review.py"), str(review_repair)])
        run_ok([sys.executable, script("check_paper.py"), str(review_repair)])
        if "Agent reviewer: Codex" not in review_repair.read_text(encoding="utf-8"):
            raise SystemExit("Agent review did not repair missing Agent Review section")
        if "Decision: AI Validated" not in review_repair.read_text(encoding="utf-8"):
            raise SystemExit("Agent review default decision was not a valid status")
        run_fail(
            [
                sys.executable,
                script("agent_review.py"),
                str(review_repair),
                "--decision",
                "Agent Reviewed",
            ],
            "invalid choice",
        )

        review_injection = create_edge_paper(root, "Agent Review Injection Edge")
        run_ok(
            [
                sys.executable,
                script("agent_review.py"),
                str(review_injection),
                "--reviewer",
                "Codex\n## Agent Review",
                "--decision",
                "AI Validated",
                "--notes",
                "Looks good\n## Impact Score\ninjected",
            ]
        )
        review_text = review_injection.read_text(encoding="utf-8")
        if review_text.count("\n## Agent Review\n") != 1:
            raise SystemExit("Agent review input injected an extra Agent Review heading")
        if review_text.count("\n## Impact Score\n") != 1:
            raise SystemExit("Agent review input injected an extra Impact Score heading")
        if "Codex ## Agent Review" not in review_text:
            raise SystemExit("Agent reviewer input was not collapsed to inline Markdown")
        if "Decision: AI Validated" not in review_text:
            raise SystemExit("Agent decision was not recorded as a valid status")
        if "Looks good ## Impact Score injected" not in review_text:
            raise SystemExit("Agent review notes were not collapsed to inline Markdown")
        if f"updated: {date.today().isoformat()}" not in review_text:
            raise SystemExit("Agent review did not refresh updated frontmatter")
        run_ok([sys.executable, script("check_paper.py"), str(review_injection)])

        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Missing Target Review",
                "--target",
                "PAPER-9999",
                "--format",
                "json",
            ],
            "Missing target paper files for: PAPER-9999",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Malformed Target Review",
                "--target",
                "PAPER-0001-extra",
                "--format",
                "json",
            ],
            "Expected PAPER-NNNN",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Short Target Review",
                "--target",
                "PAPER-1",
                "--format",
                "json",
            ],
            "Expected PAPER-NNNN",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Bad Date Review",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
                "--date",
                "2026-13-01",
            ],
            "--date must be a valid calendar date",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Bad Slug Review",
                "--slug",
                "../bad",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
            ],
            "--slug must contain only ASCII letters, numbers, and single hyphens",
        )
        prompt_output_dir = root / "inbox" / "prompt-output-dir"
        prompt_output_dir.mkdir(parents=True)
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Directory Prompt Output Review",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
                "--prompt-out",
                str(prompt_output_dir),
            ],
            f"Expected prompt output file, got directory: {prompt_output_dir}",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Oversized Target Review",
                "--target",
                "PAPER-10000",
                "--format",
                "json",
            ],
            "Expected PAPER-NNNN",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Bad: Title",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
            ],
            "--title must not contain",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Duplicate Explicit Target Review",
                "--target",
                "PAPER-0001",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
            ],
            "Duplicate review targets: PAPER-0001",
        )

        no_slug_target_root = project / "no-slug-target-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(no_slug_target_root),
                "--project-name",
                "Loop Paper No Slug Target Edge",
                "--date",
                "2026-06-10",
            ]
        )
        slugged_target = create_edge_paper(no_slug_target_root, "No Slug Target Edge")
        no_slug_target = no_slug_target_root / "papers" / "PAPER-0001.md"
        slugged_target.rename(no_slug_target)
        no_slug_answers = no_slug_target_root / "inbox" / "answers.json"
        no_slug_answers.parent.mkdir(parents=True, exist_ok=True)
        write_answers(no_slug_answers)
        no_slug_review = Path(
            run_ok(
                [
                    sys.executable,
                    script("new_review_paper.py"),
                    "--root",
                    str(no_slug_target_root),
                    "--title",
                    "No Slug Target Review",
                    "--target",
                    "PAPER-0001",
                    "--answers",
                    str(no_slug_answers),
                    "--date",
                    "2026-06-10",
                ]
            ).stdout.strip()
        )
        if not no_slug_review.exists():
            raise SystemExit("Review paper was not created for canonical no-slug target")
        run_ok([sys.executable, script("check_paper.py"), str(no_slug_target_root)])

        conflicting_answers = root / "inbox" / "conflicting-answers.json"
        write_answers(conflicting_answers)
        before_conflict_count = len(list((root / "papers").glob("PAPER-*.html")))
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Conflicting Prompt Out Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(conflicting_answers),
                "--prompt-out",
                str(root / "inbox" / "ignored-prompts.json"),
                "--date",
                "2026-06-10",
            ],
            "Prompt rendering options cannot be used with --answers: --prompt-out",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Conflicting Format Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(conflicting_answers),
                "--format",
                "json",
                "--date",
                "2026-06-10",
            ],
            "Prompt rendering options cannot be used with --answers: --format",
        )
        if len(list((root / "papers").glob("PAPER-*.html"))) != before_conflict_count:
            raise SystemExit("Conflicting review options created a review paper unexpectedly")
        if (root / "inbox" / "ignored-prompts.json").exists():
            raise SystemExit("Conflicting review options wrote prompt output unexpectedly")

        answers = root / "inbox" / "bad-answers.json"
        answers.parent.mkdir(parents=True, exist_ok=True)
        missing_answers = root / "inbox" / "missing-answers.json"
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Missing Answers Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(missing_answers),
                "--date",
                "2026-06-10",
            ],
            f"Missing answers JSON file: {missing_answers}",
        )
        answers_directory = root / "inbox" / "answers-directory.json"
        answers_directory.mkdir()
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Directory Answers Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(answers_directory),
                "--date",
                "2026-06-10",
            ],
            f"Expected answers JSON file, got directory: {answers_directory}",
        )
        invalid_json = root / "inbox" / "invalid-json-answers.json"
        invalid_json.write_text("{", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Invalid Json Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(invalid_json),
                "--date",
                "2026-06-10",
            ],
            "answers JSON is invalid",
        )
        malformed_list = root / "inbox" / "malformed-list-answers.json"
        malformed_list.write_text(json.dumps([{"id": "verdict.PAPER-0001"}]), encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Malformed List Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(malformed_list),
                "--date",
                "2026-06-10",
            ],
            "answers list items must be objects with id and answer",
        )
        duplicate_answer_list = root / "inbox" / "duplicate-answer-list.json"
        duplicate_answer_list.write_text(
            json.dumps(
                [
                    {"id": "verdict.PAPER-0001", "answer": "Supported"},
                    {"id": "verdict.PAPER-0001", "answer": "Failed"},
                ]
            ),
            encoding="utf-8",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Duplicate Answer Id Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(duplicate_answer_list),
                "--date",
                "2026-06-10",
            ],
            "duplicate answer id: verdict.PAPER-0001",
        )
        unknown_answer = root / "inbox" / "unknown-answer.json"
        write_answers(unknown_answer)
        unknown_payload = json.loads(unknown_answer.read_text(encoding="utf-8"))
        unknown_payload["unexpected.PAPER-0001"] = "Supported"
        unknown_answer.write_text(json.dumps(unknown_payload), encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Unknown Answer Id Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(unknown_answer),
                "--date",
                "2026-06-10",
            ],
            "answers contain unknown ids: unexpected.PAPER-0001",
        )
        write_answers(answers, evidence="Unsupported option")
        before_count = len(list((root / "papers").glob("PAPER-*.html")))
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Bad Answer Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(answers),
                "--date",
                "2026-06-10",
            ],
            "not in options",
        )
        after_count = len(list((root / "papers").glob("PAPER-*.html")))
        if before_count != after_count:
            raise SystemExit("Failed review answer validation wrote a paper unexpectedly")

        review_meta_root = project / "review-metadata-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(review_meta_root),
                "--project-name",
                "Loop Paper Review Metadata Edge",
                "--date",
                "2026-06-10",
            ]
        )
        create_edge_paper(review_meta_root, "Review Metadata Target")
        review_answers = review_meta_root / "inbox" / "answers.json"
        review_answers.parent.mkdir(parents=True, exist_ok=True)
        write_answers(review_answers)
        review_paper = Path(
            run_ok(
                [
                    sys.executable,
                    script("new_review_paper.py"),
                    "--root",
                    str(review_meta_root),
                    "--title",
                    "Review Metadata Paper",
                    "--target",
                    "PAPER-0001",
                    "--answers",
                    str(review_answers),
                    "--date",
                    "2026-06-10",
                ]
            ).stdout.strip()
        )
        run_ok([sys.executable, script("check_paper.py"), str(review_meta_root)])
        review_text = review_paper.read_text(encoding="utf-8")
        contradictory_answers = review_meta_root / "inbox" / "contradictory-answers.json"
        write_answers(contradictory_answers, coherence="Contradictory")
        contradictory_review = Path(
            run_ok(
                [
                    sys.executable,
                    script("new_review_paper.py"),
                    "--root",
                    str(review_meta_root),
                    "--title",
                    "Contradictory Review Metadata Paper",
                    "--target",
                    "PAPER-0001",
                    "--answers",
                    str(contradictory_answers),
                    "--date",
                    "2026-06-10",
                ]
            ).stdout.strip()
        )
        contradictory_text = contradictory_review.read_text(encoding="utf-8")
        expected_failed_ledger = (
            "| H1 | A structured review of PAPER-0001 produces a coherent next-step "
            "recommendation | Per-target dimensions enumerated below | "
            "Multiple-choice walk over each dimension | Failed |"
        )
        if expected_failed_ledger not in contradictory_text:
            raise SystemExit("Contradictory review did not record Failed in the Hypothesis Ledger")
        if "- Failed: structured per-target verdicts recorded with documented options;" not in contradictory_text:
            raise SystemExit("Contradictory review did not record Failed in the Validation verdict")
        if "- Supported: structured per-target verdicts recorded with documented options" in contradictory_text:
            raise SystemExit("Contradictory review kept the old hard-coded Supported verdict")
        run_ok(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(contradictory_review),
                "--phase",
                "after",
            ]
        )
        review_paper.write_text(
            review_text.replace("paper_kind: review", "paper_kind: mystery", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(review_paper)],
            "Invalid paper_kind: mystery",
        )
        review_paper.write_text(review_text, encoding="utf-8")
        review_paper.write_text(
            review_text.replace("review_targets: PAPER-0001", "review_targets: PAPER-1", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(review_paper)],
            "Invalid review_targets entry: PAPER-1",
        )
        review_paper.write_text(review_text, encoding="utf-8")
        review_paper.write_text(
            review_text.replace("review_targets: PAPER-0001", "review_targets: PAPER-0001,", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(review_paper)],
            "review_targets contains empty entry",
        )
        review_paper.write_text(review_text, encoding="utf-8")
        review_paper.write_text(
            review_text.replace("review_targets: PAPER-0001", "review_targets: PAPER-0001,,PAPER-0001", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(review_paper)],
            "review_targets contains empty entry",
        )
        review_paper.write_text(review_text, encoding="utf-8")
        review_paper.write_text(
            review_text.replace("review_targets: PAPER-0001", "review_targets: PAPER-9999", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(review_meta_root)],
            "Dangling review target: PAPER-9999",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(review_meta_root), "--strict"],
            "Dangling review target: PAPER-9999",
        )
        review_paper.write_text(review_text, encoding="utf-8")
        review_id = "-".join(review_paper.name.split("-", 2)[:2])
        review_paper.write_text(
            review_text.replace("review_targets: PAPER-0001", f"review_targets: {review_id}", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(review_meta_root)],
            f"Review paper cannot target itself: {review_id}",
        )
        review_paper.write_text(review_text, encoding="utf-8")
        review_paper.write_text(
            review_text.replace("References: PAPER-0001", "References: None", 1),
            encoding="utf-8",
        )
        for command in [
            [sys.executable, script("check_paper.py"), str(review_meta_root)],
            [sys.executable, script("pipeline.py"), str(review_meta_root), "--strict"],
            [sys.executable, script("render_dashboard.py"), str(review_meta_root)],
            [sys.executable, script("index_references.py"), str(review_meta_root)],
            [
                sys.executable,
                script("combine_papers.py"),
                str(review_meta_root),
                "--ids",
                "PAPER-0001",
                review_id,
            ],
        ]:
            run_fail(command, "review_targets must match References relationship targets")
        review_paper.write_text(review_text, encoding="utf-8")
        review_paper.write_text(
            review_text.replace("paper_kind: review\n", "", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(review_paper), "--check"],
            f"CHANGED {review_id}",
        )
        run_ok([sys.executable, script("update_paper_metadata.py"), str(review_paper)])
        repaired_review_text = review_paper.read_text(encoding="utf-8")
        if "paper_kind: review" not in repaired_review_text:
            raise SystemExit("Metadata sync did not repair missing review paper_kind")
        if "review_targets: PAPER-0001" not in repaired_review_text:
            raise SystemExit("Metadata sync lost review_targets while repairing paper_kind")
        run_ok([sys.executable, script("check_paper.py"), str(review_paper)])
        review_paper.write_text(review_text, encoding="utf-8")
        review_paper.write_text(
            review_text.replace("review_targets: PAPER-0001\n", "", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(review_paper), "--check"],
            f"CHANGED {review_id}",
        )
        run_ok([sys.executable, script("update_paper_metadata.py"), str(review_paper)])
        if "review_targets: PAPER-0001" not in review_paper.read_text(encoding="utf-8"):
            raise SystemExit("Metadata sync did not repair missing review_targets from References")
        run_ok([sys.executable, script("check_paper.py"), str(review_paper)])
        review_paper.write_text(review_text, encoding="utf-8")
        review_paper.write_text(
            review_text.replace("paper_kind: review\n", "", 1).replace(
                "review_targets: PAPER-0001\n",
                "",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(review_paper), "--check"],
            f"CHANGED {review_id}",
        )
        run_ok([sys.executable, script("update_paper_metadata.py"), str(review_paper)])
        repaired_review_text = review_paper.read_text(encoding="utf-8")
        if "paper_kind: review" not in repaired_review_text:
            raise SystemExit("Metadata sync misclassified review paper as closed_loop")
        if "review_targets: PAPER-0001" not in repaired_review_text:
            raise SystemExit("Metadata sync did not restore review_targets when kind was missing")
        run_ok([sys.executable, script("check_paper.py"), str(review_paper)])
        review_paper.write_text(review_text, encoding="utf-8")
        closed_loop_with_targets = review_meta_root / "papers" / "PAPER-0001-review-metadata-target.html"
        closed_loop_text = closed_loop_with_targets.read_text(encoding="utf-8")
        closed_loop_with_targets.write_text(
            closed_loop_text.replace(
                "impact_score: TBD\n",
                "impact_score: TBD\nreview_targets: PAPER-0002\n",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(closed_loop_with_targets)],
            "review_targets requires paper_kind: review",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(closed_loop_with_targets)],
            "review_targets requires paper_kind: review",
        )

        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(created), "--phase", "before"],
            "BEFORE_REQUIRED slots remain",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(created), "Research Ready"],
            "Research Ready requires Prior Research and References placeholders to be resolved",
        )
        prior_gate = create_edge_paper(root, "Prior Gate Edge")
        make_before_ready_except_prior_research(prior_gate)
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(prior_gate), "--phase", "before"],
            "prior research checkboxes are not all checked",
        )
        run_ok([sys.executable, script("transition_paper.py"), str(prior_gate), "Research Ready"])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(prior_gate), "Plan Ready"],
            "prior research checkboxes are not all checked",
        )
        missing_prior_risk_gate = create_edge_paper(root, "Missing Prior Risk Gate Edge")
        make_before_ready_with_uppercase_checks(missing_prior_risk_gate)
        missing_prior_risk_gate.write_text(
            missing_prior_risk_gate.read_text(encoding="utf-8").replace(
                "Prior Research Status: Present",
                "Prior Research Status: Missing",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(missing_prior_risk_gate),
                "--phase",
                "before",
            ],
            "missing prior research must explicitly mark Risk: High",
        )
        invalid_prior_status_gate = create_edge_paper(root, "Invalid Prior Status Gate Edge")
        make_before_ready_with_uppercase_checks(invalid_prior_status_gate)
        invalid_prior_status_gate.write_text(
            invalid_prior_status_gate.read_text(encoding="utf-8").replace(
                "Prior Research Status: Present",
                "Prior Research Status: Maybe",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(invalid_prior_status_gate),
                "--phase",
                "before",
            ],
            "invalid Prior Research Status: Maybe; expected Present, Missing, or Retrospective",
        )
        invalid_risk_gate = create_edge_paper(root, "Invalid Risk Gate Edge")
        make_before_ready_with_uppercase_checks(invalid_risk_gate)
        invalid_risk_gate.write_text(
            invalid_risk_gate.read_text(encoding="utf-8").replace(
                "Risk: Low",
                "Risk: Critical",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(invalid_risk_gate),
                "--phase",
                "before",
            ],
            "invalid Risk: Critical; expected Low, Medium, or High",
        )
        missing_prior_risk_pipeline_root = project / "missing-prior-risk-pipeline-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(missing_prior_risk_pipeline_root),
                "--project-name",
                "Loop Paper Missing Prior Risk Pipeline",
                "--date",
                "2026-06-10",
            ]
        )
        missing_prior_risk_pipeline = create_edge_paper(
            missing_prior_risk_pipeline_root,
            "Missing Prior Risk Pipeline Edge",
        )
        make_before_ready_with_uppercase_checks(missing_prior_risk_pipeline)
        missing_prior_risk_pipeline.write_text(
            missing_prior_risk_pipeline.read_text(encoding="utf-8").replace(
                "Prior Research Status: Present",
                "Prior Research Status: Missing",
                1,
            ),
            encoding="utf-8",
        )
        set_status(missing_prior_risk_pipeline, "Plan Ready")
        run_fail(
            [sys.executable, script("pipeline.py"), str(missing_prior_risk_pipeline_root), "--strict"],
            "missing prior research must explicitly mark Risk: High",
        )
        uppercase_gate = create_edge_paper(root, "Uppercase Checkbox Edge")
        make_before_ready_with_uppercase_checks(uppercase_gate)
        run_ok(
            [sys.executable, script("check_closed_loop_paper.py"), str(uppercase_gate), "--phase", "before"]
        )
        unrelated_hypothesis_checks_gate = create_edge_paper(root, "Unrelated Hypothesis Checks Edge")
        make_before_ready_with_unrelated_hypothesis_checks(unrelated_hypothesis_checks_gate)
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(unrelated_hypothesis_checks_gate),
                "--phase",
                "before",
            ],
            "hypothesis checkboxes are not all checked",
        )
        for status in ["Research Ready"]:
            run_ok([sys.executable, script("transition_paper.py"), str(unrelated_hypothesis_checks_gate), status])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(unrelated_hypothesis_checks_gate), "Plan Ready"],
            "hypothesis checkboxes are not all checked",
        )
        empty_hypothesis_claim_gate = create_edge_paper(root, "Empty Hypothesis Claim Edge")
        make_before_ready_with_empty_hypothesis_claim(empty_hypothesis_claim_gate)
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(empty_hypothesis_claim_gate),
                "--phase",
                "before",
            ],
            "hypothesis ledger row 1 has empty required cells: Claim",
        )
        empty_prior_finding_gate = create_edge_paper(root, "Empty Prior Finding Edge")
        make_before_ready_with_empty_prior_finding(empty_prior_finding_gate)
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(empty_prior_finding_gate),
                "--phase",
                "before",
            ],
            "prior research ledger row 1 has empty required cells: Finding",
        )
        empty_implementation_risks_gate = create_edge_paper(root, "Empty Implementation Risks Edge")
        make_before_ready_with_empty_implementation_risks(empty_implementation_risks_gate)
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(empty_implementation_risks_gate),
                "--phase",
                "before",
            ],
            "implementation plan Risks block has no concrete content",
        )
        empty_validation_baseline_gate = create_edge_paper(root, "Empty Validation Baseline Edge")
        make_before_ready_with_empty_validation_baseline(empty_validation_baseline_gate)
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(empty_validation_baseline_gate),
                "--phase",
                "before",
            ],
            "validation plan Before-change evidence block has no concrete content",
        )
        validation_plan_gate = create_edge_paper(root, "Validation Plan Gate Edge")
        make_before_ready_except_validation_plan(validation_plan_gate)
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(validation_plan_gate), "--phase", "before"],
            "validation plan AI-actionable validation block has no checked item",
        )
        run_ok(
            [
                sys.executable,
                script("transition_paper.py"),
                str(validation_plan_gate),
                "Plan Ready",
                "--force",
            ]
        )
        run_ok([sys.executable, script("transition_paper.py"), str(validation_plan_gate), "Research Ready"])
        unrelated_validation_plan_check_gate = create_edge_paper(root, "Unrelated Validation Plan Check Edge")
        make_before_ready_with_unrelated_validation_plan_check(unrelated_validation_plan_check_gate)
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(unrelated_validation_plan_check_gate),
                "--phase",
                "before",
            ],
            "validation plan AI-actionable validation block has no checked item",
        )
        run_ok([sys.executable, script("transition_paper.py"), str(unrelated_validation_plan_check_gate), "Research Ready"])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(unrelated_validation_plan_check_gate), "Plan Ready"],
            "validation plan AI-actionable validation block has no checked item",
        )
        validation_evidence_gate = create_edge_paper(root, "Validation Evidence Gate Edge")
        make_after_ready_except_validation_evidence(validation_evidence_gate)
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(validation_evidence_gate), "--phase", "after"],
            "validation evidence checkbox is not checked",
        )
        for status in ["Research Ready", "Plan Ready", "Implementing", "Implemented"]:
            run_ok([sys.executable, script("transition_paper.py"), str(validation_evidence_gate), status])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(validation_evidence_gate), "AI Validated"],
            "validation evidence checkbox is not checked",
        )
        empty_validation_after_gate = create_edge_paper(root, "Empty Validation After Edge")
        make_after_ready_with_empty_validation_after(empty_validation_after_gate)
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(empty_validation_after_gate),
                "--phase",
                "after",
            ],
            "validation After block has no concrete evidence",
        )
        for status in ["Research Ready", "Plan Ready", "Implementing", "Implemented"]:
            run_ok([sys.executable, script("transition_paper.py"), str(empty_validation_after_gate), status])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(empty_validation_after_gate), "AI Validated"],
            "validation After block has no concrete evidence",
        )
        open_hypothesis_verdict_gate = create_edge_paper(root, "Open Hypothesis Verdict Edge")
        make_after_ready(open_hypothesis_verdict_gate)
        text = open_hypothesis_verdict_gate.read_text(encoding="utf-8")
        text = re.sub(r"(?m)^(\| H\d+ \|.*\| )Supported( \|)$", r"\1Open\2", text, count=1)
        open_hypothesis_verdict_gate.write_text(text, encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(open_hypothesis_verdict_gate),
                "--phase",
                "after",
            ],
            "hypothesis ledger row 1 has invalid after verdict: Open",
        )
        for status in ["Research Ready", "Plan Ready", "Implementing", "Implemented"]:
            run_ok([sys.executable, script("transition_paper.py"), str(open_hypothesis_verdict_gate), status])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(open_hypothesis_verdict_gate), "AI Validated"],
            "hypothesis ledger row 1 has invalid after verdict: Open",
        )
        missing_agent_reviewer_gate = create_edge_paper(root, "Missing Agent Reviewer Edge")
        make_after_ready_with_missing_agent_reviewer(missing_agent_reviewer_gate)
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(missing_agent_reviewer_gate),
                "--phase",
                "after",
            ],
            "agent review missing Agent reviewer",
        )
        for status in ["Research Ready", "Plan Ready", "Implementing", "Implemented"]:
            run_ok([sys.executable, script("transition_paper.py"), str(missing_agent_reviewer_gate), status])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(missing_agent_reviewer_gate), "AI Validated"],
            "agent review missing Agent reviewer",
        )
        unrelated_agent_checks_gate = create_edge_paper(root, "Unrelated Agent Checks Edge")
        make_after_ready_with_unrelated_agent_checks(unrelated_agent_checks_gate)
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(unrelated_agent_checks_gate),
                "--phase",
                "after",
            ],
            "agent review checkboxes are not all checked",
        )
        for status in ["Research Ready", "Plan Ready", "Implementing", "Implemented"]:
            run_ok([sys.executable, script("transition_paper.py"), str(unrelated_agent_checks_gate), status])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(unrelated_agent_checks_gate), "AI Validated"],
            "agent review checkboxes are not all checked",
        )
        invalid_agent_decision_gate = create_edge_paper(root, "Invalid Agent Decision Edge")
        make_after_ready_with_invalid_agent_decision(invalid_agent_decision_gate)
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(invalid_agent_decision_gate),
                "--phase",
                "after",
            ],
            "agent review invalid Decision",
        )
        for status in ["Research Ready", "Plan Ready", "Implementing", "Implemented"]:
            run_ok([sys.executable, script("transition_paper.py"), str(invalid_agent_decision_gate), status])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(invalid_agent_decision_gate), "AI Validated"],
            "agent review invalid Decision",
        )
        duplicate_agent_decision_gate = create_edge_paper(root, "Duplicate Agent Decision Edge")
        make_after_ready_with_duplicate_agent_decision(duplicate_agent_decision_gate)
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(duplicate_agent_decision_gate),
                "--phase",
                "after",
            ],
            "agent review duplicate Decision",
        )
        for status in ["Research Ready", "Plan Ready", "Implementing", "Implemented"]:
            run_ok([sys.executable, script("transition_paper.py"), str(duplicate_agent_decision_gate), status])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(duplicate_agent_decision_gate), "AI Validated"],
            "agent review duplicate Decision",
        )
        empty_impact_basis_gate = create_edge_paper(root, "Empty Impact Basis Edge")
        make_after_ready_with_empty_impact_basis(empty_impact_basis_gate)
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(empty_impact_basis_gate),
                "--phase",
                "after",
            ],
            "impact score basis missing Measured outcome",
        )
        for status in ["Research Ready", "Plan Ready", "Implementing", "Implemented"]:
            run_ok([sys.executable, script("transition_paper.py"), str(empty_impact_basis_gate), status])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(empty_impact_basis_gate), "AI Validated"],
            "impact score basis missing Measured outcome",
        )
        duplicate_impact_fields_gate = create_edge_paper(root, "Duplicate Impact Fields Edge")
        make_after_ready_with_duplicate_impact_fields(duplicate_impact_fields_gate)
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(duplicate_impact_fields_gate),
                "--phase",
                "after",
            ],
            "impact score duplicate Impact score value",
        )
        for status in ["Research Ready", "Plan Ready", "Implementing", "Implemented"]:
            run_ok([sys.executable, script("transition_paper.py"), str(duplicate_impact_fields_gate), status])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(duplicate_impact_fields_gate), "AI Validated"],
            "impact score duplicate Impact score value",
        )
        invalid_impact_score_gate = create_edge_paper(root, "Invalid Impact Score Edge")
        make_after_ready_with_invalid_impact_score(invalid_impact_score_gate)
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(invalid_impact_score_gate),
                "--phase",
                "after",
            ],
            "impact score value must be TBD or a number from 0 to 10",
        )
        for status in ["Research Ready", "Plan Ready", "Implementing", "Implemented"]:
            run_ok([sys.executable, script("transition_paper.py"), str(invalid_impact_score_gate), status])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(invalid_impact_score_gate), "AI Validated"],
            "impact score value must be TBD or a number from 0 to 10",
        )
        empty_run_records_gate = create_edge_paper(root, "Empty Run Records Edge")
        make_after_ready_with_empty_run_records(empty_run_records_gate)
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(empty_run_records_gate),
                "--phase",
                "after",
            ],
            "execution records Run records block has no concrete content",
        )
        for status in ["Research Ready", "Plan Ready", "Implementing", "Implemented"]:
            run_ok([sys.executable, script("transition_paper.py"), str(empty_run_records_gate), status])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(empty_run_records_gate), "AI Validated"],
            "execution records Run records block has no concrete content",
        )
        verdict_gate = create_edge_paper(root, "Verdict Instruction Gate Edge")
        make_after_ready_with_instruction_verdict(verdict_gate)
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(verdict_gate), "--phase", "after"],
            "no hypothesis verdict recorded",
        )
        for status in ["Research Ready", "Plan Ready", "Implementing", "Implemented"]:
            run_ok([sys.executable, script("transition_paper.py"), str(verdict_gate), status])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(verdict_gate), "AI Validated"],
            "no hypothesis verdict recorded",
        )
        pipeline_gate = create_edge_paper(root, "Pipeline Gate Edge")
        make_after_ready_except_validation_evidence(pipeline_gate)
        set_status(pipeline_gate, "AI Validated")
        run_fail(
            [sys.executable, script("pipeline.py"), str(root), "--strict"],
            "validation evidence checkbox is not checked",
        )
        phase_output_root = project / "phase-output-gate-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(phase_output_root),
                "--project-name",
                "Loop Paper Phase Output Gate",
                "--date",
                "2026-06-10",
            ]
        )
        phase_output_gate = create_edge_paper(phase_output_root, "Phase Output Gate Edge")
        make_after_ready_except_validation_evidence(phase_output_gate)
        set_status(phase_output_gate, "AI Validated")
        run_fail(
            [sys.executable, script("pipeline.py"), str(phase_output_root), "--strict"],
            "SKIP generated outputs",
        )
        blocked_outputs = [
            phase_output_root / "dashboard" / "references.json",
            phase_output_root / "dashboard" / "impact-scores.json",
            phase_output_root / "dashboard" / "index.html",
            phase_output_root / "dashboard" / "report.md",
        ]
        written = [str(path) for path in blocked_outputs if path.exists()]
        if written:
            raise SystemExit("Failed phase gate wrote generated outputs: " + ", ".join(written))
        failed_summary = phase_output_root / "dashboard" / "pipeline-summary.json"
        if not failed_summary.exists():
            raise SystemExit("Failed phase gate did not write pipeline summary")
        failed_summary_payload = json.loads(failed_summary.read_text(encoding="utf-8"))
        if failed_summary_payload.get("closed_loop_checked") is not False:
            raise SystemExit("Failed phase gate summary did not record closed_loop_checked=false")
        if failed_summary_payload.get("dashboard_rendered") is not False:
            raise SystemExit("Failed phase gate summary did not record skipped dashboard render")
        stale_output_root = project / "stale-output-gate-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(stale_output_root),
                "--project-name",
                "Loop Paper Stale Output Gate",
                "--date",
                "2026-06-10",
            ]
        )
        stale_output_gate = create_edge_paper(stale_output_root, "Stale Output Gate Edge")
        run_ok([sys.executable, script("pipeline.py"), str(stale_output_root), "--strict"])
        stale_outputs = [
            stale_output_root / "dashboard" / "data.json",
            stale_output_root / "dashboard" / "references.json",
            stale_output_root / "dashboard" / "impact-scores.json",
            stale_output_root / "dashboard" / "index.html",
            stale_output_root / "dashboard" / "report.md",
        ]
        missing_outputs = [str(path) for path in stale_outputs if not path.exists()]
        if missing_outputs:
            raise SystemExit("Successful pipeline did not write outputs: " + ", ".join(missing_outputs))
        set_status(stale_output_gate, "Plan Ready")
        run_fail(
            [sys.executable, script("pipeline.py"), str(stale_output_root), "--strict"],
            "SKIP generated outputs",
        )
        stale_remaining = [str(path) for path in stale_outputs if path.exists()]
        if stale_remaining:
            raise SystemExit("Failed phase gate left stale generated outputs: " + ", ".join(stale_remaining))
        stale_summary = stale_output_root / "dashboard" / "pipeline-summary.json"
        if not stale_summary.exists():
            raise SystemExit("Failed stale-output gate did not write pipeline summary")
        partial_output_root = project / "partial-output-gate-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(partial_output_root),
                "--project-name",
                "Loop Paper Partial Output Gate",
                "--date",
                "2026-06-10",
            ]
        )
        create_edge_paper(partial_output_root, "Partial Output Gate Edge")
        partial_report_collision = partial_output_root / "dashboard" / "report.md"
        partial_report_collision.mkdir(parents=True)
        run_fail(
            [sys.executable, script("pipeline.py"), str(partial_output_root), "--strict"],
            "Expected output file, got directory",
        )
        partial_outputs = [
            partial_output_root / "dashboard" / "data.json",
            partial_output_root / "dashboard" / "references.json",
            partial_output_root / "dashboard" / "impact-scores.json",
            partial_output_root / "dashboard" / "index.html",
        ]
        partial_remaining = [str(path) for path in partial_outputs if path.exists()]
        if partial_remaining:
            raise SystemExit("Failed output step left partial generated outputs: " + ", ".join(partial_remaining))
        partial_summary = partial_output_root / "dashboard" / "pipeline-summary.json"
        if not partial_summary.exists():
            raise SystemExit("Failed partial-output gate did not write pipeline summary")
        partial_summary_payload = json.loads(partial_summary.read_text(encoding="utf-8"))
        if partial_summary_payload.get("report_exported") is not False:
            raise SystemExit("Failed partial-output summary did not record report_exported=false")
        run_fail(
            [sys.executable, script("watch_pipeline.py"), str(root), "--once"],
            "validation evidence checkbox is not checked",
        )
        run_fail(
            [sys.executable, script("watch_pipeline.py"), str(root), "--interval", "0", "--once"],
            "--interval must be greater than zero",
        )
        status_root = project / "status-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(status_root),
                "--project-name",
                "Loop Paper Status Edge",
                "--date",
                "2026-06-10",
            ]
        )
        invalid_status_gate = create_edge_paper(status_root, "Invalid Status Edge")
        set_status(invalid_status_gate, "Totally Done")
        run_fail(
            [sys.executable, script("check_paper.py"), str(invalid_status_gate)],
            "Invalid status: Totally Done",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(status_root), "--strict"],
            "Invalid status: Totally Done",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(status_root), "--last", "1"],
            "Cannot combine invalid papers",
        )
        invalid_impact_metadata_root = project / "invalid-impact-metadata-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(invalid_impact_metadata_root),
                "--project-name",
                "Loop Paper Invalid Impact Metadata Edge",
                "--date",
                "2026-06-10",
            ]
        )
        invalid_impact_metadata = create_edge_paper(
            invalid_impact_metadata_root,
            "Invalid Impact Metadata Edge",
        )
        invalid_impact_metadata.write_text(
            invalid_impact_metadata.read_text(encoding="utf-8").replace(
                "impact_score: TBD",
                "impact_score: A | B",
                1,
            ),
            encoding="utf-8",
        )
        for command in [
            [sys.executable, script("check_paper.py"), str(invalid_impact_metadata)],
            [sys.executable, script("check_paper.py"), str(invalid_impact_metadata_root)],
            [sys.executable, script("pipeline.py"), str(invalid_impact_metadata_root), "--strict"],
            [sys.executable, script("render_dashboard.py"), str(invalid_impact_metadata_root)],
            [sys.executable, script("export_report.py"), str(invalid_impact_metadata_root)],
        ]:
            run_fail(command, "Invalid impact_score: A | B; expected TBD or a number from 0 to 10")
        lowercase_not_run_root = project / "lowercase-not-run-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(lowercase_not_run_root),
                "--project-name",
                "Loop Paper Lowercase Not Run Edge",
                "--date",
                "2026-06-10",
            ]
        )
        lowercase_not_run = create_edge_paper(
            lowercase_not_run_root,
            "Lowercase Not Run Edge",
        )
        set_status(lowercase_not_run, "AI Validated")
        lowercase_not_run.write_text(
            lowercase_not_run.read_text(encoding="utf-8").replace(
                "Record actual evidence only after execution or inspection.",
                "not run",
                1,
            ),
            encoding="utf-8",
        )
        for command in [
            [sys.executable, script("check_paper.py"), str(lowercase_not_run)],
            [sys.executable, script("check_paper.py"), str(lowercase_not_run_root)],
            [sys.executable, script("pipeline.py"), str(lowercase_not_run_root), "--strict"],
            [sys.executable, script("score_impact.py"), str(lowercase_not_run_root)],
        ]:
            run_fail(command, "Advanced status conflicts with validation evidence marked Not run.")
        hyphen_not_run_root = project / "hyphen-not-run-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(hyphen_not_run_root),
                "--project-name",
                "Loop Paper Hyphen Not Run Edge",
                "--date",
                "2026-06-10",
            ]
        )
        hyphen_not_run = create_edge_paper(
            hyphen_not_run_root,
            "Hyphen Not Run Edge",
        )
        hyphen_not_run.write_text(
            hyphen_not_run.read_text(encoding="utf-8").replace(
                "Record actual evidence only after execution or inspection.",
                "Not-run",
                1,
            ),
            encoding="utf-8",
        )
        set_status(hyphen_not_run, "AI Validated")
        for command in [
            [sys.executable, script("check_paper.py"), str(hyphen_not_run)],
            [sys.executable, script("check_paper.py"), str(hyphen_not_run_root)],
            [sys.executable, script("pipeline.py"), str(hyphen_not_run_root), "--strict"],
            [sys.executable, script("score_impact.py"), str(hyphen_not_run_root)],
        ]:
            run_fail(command, "Advanced status conflicts with validation evidence marked Not run.")
        transition_hyphen_not_run = create_edge_paper(
            hyphen_not_run_root,
            "Hyphen Not Run Transition Edge",
        )
        make_after_ready(transition_hyphen_not_run)
        transition_hyphen_not_run.write_text(
            transition_hyphen_not_run.read_text(encoding="utf-8").replace(
                "Record actual evidence only after execution or inspection.",
                "Not-run",
                1,
            ),
            encoding="utf-8",
        )
        for status in ["Research Ready", "Plan Ready", "Implementing", "Implemented"]:
            run_ok([sys.executable, script("transition_paper.py"), str(transition_hyphen_not_run), status])
        run_fail(
            [sys.executable, script("transition_paper.py"), str(transition_hyphen_not_run), "AI Validated"],
            "Validation still says Not run",
        )
        missing_status_root = project / "missing-status-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(missing_status_root),
                "--project-name",
                "Loop Paper Missing Status Edge",
                "--date",
                "2026-06-10",
            ]
        )
        missing_status = create_edge_paper(missing_status_root, "Missing Status Edge")
        missing_status.write_text(
            missing_status.read_text(encoding="utf-8").replace("status: Draft\n", "", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(missing_status)],
            "Missing status frontmatter",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(missing_status), "Research Ready"],
            "Missing status frontmatter",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(missing_status), "--check"],
            "CHANGED PAPER-0001",
        )
        run_ok([sys.executable, script("update_paper_metadata.py"), str(missing_status)])
        run_ok([sys.executable, script("check_paper.py"), str(missing_status)])
        if "paper_kind: closed_loop" not in missing_status.read_text(encoding="utf-8"):
            raise SystemExit("Metadata sync did not backfill closed-loop paper_kind")
        run_ok([sys.executable, script("pipeline.py"), str(missing_status_root), "--strict"])
        run_ok([sys.executable, script("combine_papers.py"), str(missing_status_root), "--last", "1"])
        missing_kind_root = project / "missing-kind-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(missing_kind_root),
                "--project-name",
                "Loop Paper Missing Kind Edge",
                "--date",
                "2026-06-10",
            ]
        )
        missing_kind = create_edge_paper(missing_kind_root, "Missing Kind Edge")
        missing_kind.write_text(
            missing_kind.read_text(encoding="utf-8").replace("paper_kind: closed_loop\n", "", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(missing_kind)],
            "Missing paper_kind frontmatter",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(missing_kind), "--check"],
            "CHANGED PAPER-0001",
        )
        run_ok([sys.executable, script("update_paper_metadata.py"), str(missing_kind)])
        run_ok([sys.executable, script("check_paper.py"), str(missing_kind)])
        if "paper_kind: closed_loop" not in missing_kind.read_text(encoding="utf-8"):
            raise SystemExit("Metadata sync did not repair missing paper_kind")
        run_ok([sys.executable, script("pipeline.py"), str(missing_kind_root), "--strict"])
        missing_impact_metadata_root = project / "missing-impact-metadata-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(missing_impact_metadata_root),
                "--project-name",
                "Loop Paper Missing Impact Metadata Edge",
                "--date",
                "2026-06-10",
            ]
        )
        missing_impact_metadata = create_edge_paper(
            missing_impact_metadata_root,
            "Missing Impact Metadata Edge",
        )
        missing_impact_metadata.write_text(
            missing_impact_metadata.read_text(encoding="utf-8").replace("impact_score: TBD\n", "", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(missing_impact_metadata)],
            "Missing impact_score frontmatter",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(missing_impact_metadata), "--check"],
            "CHANGED PAPER-0001",
        )
        run_ok([sys.executable, script("update_paper_metadata.py"), str(missing_impact_metadata)])
        run_ok([sys.executable, script("check_paper.py"), str(missing_impact_metadata)])
        if "impact_score: TBD" not in missing_impact_metadata.read_text(encoding="utf-8"):
            raise SystemExit("Metadata sync did not repair missing impact_score")
        run_ok([sys.executable, script("pipeline.py"), str(missing_impact_metadata_root), "--strict"])
        missing_title_root = project / "missing-title-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(missing_title_root),
                "--project-name",
                "Loop Paper Missing Title Edge",
                "--date",
                "2026-06-10",
            ]
        )
        missing_title = create_edge_paper(missing_title_root, "Missing Title Edge")
        missing_title.write_text(
            missing_title.read_text(encoding="utf-8").replace("title: Missing Title Edge\n", "", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(missing_title)],
            "Missing title frontmatter",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(missing_title), "Research Ready"],
            "Missing title frontmatter",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(missing_title), "--check"],
            "CHANGED PAPER-0001",
        )
        run_ok([sys.executable, script("update_paper_metadata.py"), str(missing_title)])
        run_ok([sys.executable, script("check_paper.py"), str(missing_title)])
        run_ok([sys.executable, script("pipeline.py"), str(missing_title_root), "--strict"])
        run_ok([sys.executable, script("combine_papers.py"), str(missing_title_root), "--last", "1"])
        date_root = project / "date-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(date_root),
                "--project-name",
                "Loop Paper Date Edge",
                "--date",
                "2026-06-10",
            ]
        )
        invalid_date = create_edge_paper(date_root, "Invalid Metadata Date Edge")
        invalid_date.write_text(
            invalid_date.read_text(encoding="utf-8").replace("created: 2026-06-10", "created: 2026-02-30", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(invalid_date)],
            "created must be a valid calendar date",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(date_root), "--strict"],
            "created must be a valid calendar date",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(date_root), "--last", "1"],
            "Cannot combine invalid papers",
        )
        frontmatter_root = project / "frontmatter-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(frontmatter_root),
                "--project-name",
                "Loop Paper Frontmatter Edge",
                "--date",
                "2026-06-10",
            ]
        )
        malformed_frontmatter = create_edge_paper(frontmatter_root, "Malformed Frontmatter Edge")
        malformed_frontmatter.write_text(
            malformed_frontmatter.read_text(encoding="utf-8").replace(
                "status: Draft",
                "status Draft",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(malformed_frontmatter)],
            "Malformed frontmatter line",
        )
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(malformed_frontmatter), "--phase", "before"],
            "Malformed frontmatter line",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(frontmatter_root), "--strict"],
            "Malformed frontmatter line",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(frontmatter_root), "--last", "1"],
            "Cannot combine invalid papers",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(malformed_frontmatter), "Research Ready"],
            "Malformed frontmatter line",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(malformed_frontmatter), "Research Ready", "--force"],
            "Malformed frontmatter line",
        )
        malformed_close_root = project / "malformed-frontmatter-close-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(malformed_close_root),
                "--project-name",
                "Loop Paper Malformed Frontmatter Close Edge",
                "--date",
                "2026-06-10",
            ]
        )
        malformed_close = create_edge_paper(malformed_close_root, "Malformed Frontmatter Close Edge")
        malformed_close.write_text(
            malformed_close.read_text(encoding="utf-8").replace("\n---\n\n# PAPER-0001", "\n---bad\n\n# PAPER-0001", 1),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(malformed_close)],
            "Unterminated YAML frontmatter",
        )
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(malformed_close), "--phase", "before"],
            "Unterminated YAML frontmatter",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(malformed_close_root), "--strict"],
            "Unterminated YAML frontmatter",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(malformed_close_root), "--last", "1"],
            "Cannot combine invalid papers",
        )
        duplicate_frontmatter_root = project / "duplicate-frontmatter-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(duplicate_frontmatter_root),
                "--project-name",
                "Loop Paper Duplicate Frontmatter Edge",
                "--date",
                "2026-06-10",
            ]
        )
        duplicate_frontmatter = create_edge_paper(duplicate_frontmatter_root, "Duplicate Frontmatter Edge")
        duplicate_frontmatter.write_text(
            duplicate_frontmatter.read_text(encoding="utf-8").replace(
                "status: Draft",
                "status: Draft\nstatus: Accepted",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(duplicate_frontmatter)],
            "Duplicate frontmatter key: status",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(duplicate_frontmatter_root), "--strict"],
            "Duplicate frontmatter key: status",
        )
        heading_root = project / "heading-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(heading_root),
                "--project-name",
                "Loop Paper Heading Edge",
                "--date",
                "2026-06-10",
            ]
        )
        heading_mismatch = create_edge_paper(heading_root, "Heading Mismatch Edge")
        heading_mismatch.write_text(
            heading_mismatch.read_text(encoding="utf-8").replace(
                "# PAPER-0001 Heading Mismatch Edge",
                "# PAPER-9999 Heading Mismatch Edge",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(heading_mismatch)],
            "heading paper_id PAPER-9999 does not match PAPER-0001",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(heading_root), "--strict"],
            "heading paper_id PAPER-9999 does not match PAPER-0001",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(heading_root), "--last", "1"],
            "Cannot combine invalid papers",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(heading_mismatch), "Research Ready"],
            "heading paper_id PAPER-9999 does not match PAPER-0001",
        )
        title_heading_root = project / "title-heading-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(title_heading_root),
                "--project-name",
                "Loop Paper Title Heading Edge",
                "--date",
                "2026-06-10",
            ]
        )
        title_heading = create_edge_paper(title_heading_root, "Title Heading Edge")
        title_heading.write_text(
            title_heading.read_text(encoding="utf-8").replace(
                "# PAPER-0001 Title Heading Edge",
                "# PAPER-0001 Different Visible Title",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(title_heading)],
            "heading title 'Different Visible Title' does not match title frontmatter",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(title_heading), "Research Ready"],
            "heading title 'Different Visible Title' does not match title frontmatter",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(title_heading), "--check"],
            "CHANGED PAPER-0001",
        )
        run_ok([sys.executable, script("update_paper_metadata.py"), str(title_heading)])
        run_ok([sys.executable, script("check_paper.py"), str(title_heading)])
        run_ok([sys.executable, script("pipeline.py"), str(title_heading_root), "--strict"])
        run_ok([sys.executable, script("combine_papers.py"), str(title_heading_root), "--last", "1"])
        titleless_heading_root = project / "titleless-heading-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(titleless_heading_root),
                "--project-name",
                "Loop Paper Titleless Heading Edge",
                "--date",
                "2026-06-10",
            ]
        )
        titleless_heading = create_edge_paper(titleless_heading_root, "Titleless Heading Edge")
        titleless_heading.write_text(
            titleless_heading.read_text(encoding="utf-8").replace(
                "# PAPER-0001 Titleless Heading Edge",
                "# PAPER-0001",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(titleless_heading)],
            "heading title '' does not match title frontmatter",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(titleless_heading), "--check"],
            "Top-level paper heading is missing a visible title",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(titleless_heading)],
            "Top-level paper heading is missing a visible title",
        )
        duplicate_heading_root = project / "duplicate-heading-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(duplicate_heading_root),
                "--project-name",
                "Loop Paper Duplicate Heading Edge",
                "--date",
                "2026-06-10",
            ]
        )
        duplicate_heading = create_edge_paper(duplicate_heading_root, "Duplicate Heading Edge")
        duplicate_heading.write_text(
            duplicate_heading.read_text(encoding="utf-8").replace(
                "# PAPER-0001 Duplicate Heading Edge",
                "# PAPER-0001 Duplicate Heading Edge\n\n# PAPER-0001 Duplicate Heading Edge Copy",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(duplicate_heading)],
            "Duplicate top-level paper heading",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(duplicate_heading_root), "--strict"],
            "Duplicate top-level paper heading",
        )
        duplicate_section_root = project / "duplicate-section-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(duplicate_section_root),
                "--project-name",
                "Loop Paper Duplicate Section Edge",
                "--date",
                "2026-06-10",
            ]
        )
        duplicate_section = create_edge_paper(duplicate_section_root, "Duplicate Section Edge")
        duplicate_section.write_text(
            duplicate_section.read_text(encoding="utf-8").replace(
                "## Validation\n",
                "## Validation\n\nInjected duplicate section.\n\n## Validation\n",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(duplicate_section)],
            "Duplicate section: Validation",
        )
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(duplicate_section), "--phase", "before"],
            "Duplicate section: Validation",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(duplicate_section_root), "--strict"],
            "Duplicate section: Validation",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(duplicate_section_root), "--last", "1"],
            "Cannot combine invalid papers",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(duplicate_section), "Research Ready"],
            "Duplicate section: Validation",
        )
        schema_root = project / "schema-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(schema_root),
                "--project-name",
                "Loop Paper Schema Edge",
                "--date",
                "2026-06-10",
            ]
        )
        missing_schema = create_edge_paper(schema_root, "Missing Schema Edge")
        missing_schema.write_text(
            re.sub(
                r"closed_loop_schema: paper_closed_loop\.v[123]\n",
                "",
                missing_schema.read_text(encoding="utf-8"),
                count=1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(missing_schema)],
            "Missing closed_loop_schema frontmatter",
        )
        run_fail(
            [sys.executable, script("check_closed_loop_paper.py"), str(missing_schema), "--phase", "before"],
            "Missing closed_loop_schema frontmatter",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(schema_root), "--last", "1"],
            "Cannot combine invalid papers",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(missing_schema), "Research Ready"],
            "Missing closed_loop_schema frontmatter",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(missing_schema), "--check"],
            "CHANGED PAPER-0001",
        )
        run_ok([sys.executable, script("update_paper_metadata.py"), str(missing_schema)])
        run_ok([sys.executable, script("check_paper.py"), str(missing_schema)])
        if "closed_loop_schema: paper_closed_loop.v1" not in missing_schema.read_text(encoding="utf-8"):
            raise SystemExit("Metadata sync did not repair missing closed_loop_schema")
        run_ok([sys.executable, script("pipeline.py"), str(schema_root), "--strict"])
        run_ok([sys.executable, script("combine_papers.py"), str(schema_root), "--last", "1"])
        invalid_schema_root = project / "invalid-schema-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(invalid_schema_root),
                "--project-name",
                "Loop Paper Invalid Schema Edge",
                "--date",
                "2026-06-10",
            ]
        )
        invalid_schema = create_edge_paper(invalid_schema_root, "Invalid Schema Edge")
        invalid_schema.write_text(
            re.sub(
                r"closed_loop_schema: paper_closed_loop\.v[123]",
                "closed_loop_schema: paper_closed_loop.v0",
                invalid_schema.read_text(encoding="utf-8"),
                count=1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(invalid_schema)],
            "Invalid closed_loop_schema: paper_closed_loop.v0",
        )
        identity_root = project / "identity-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(identity_root),
                "--project-name",
                "Loop Paper Identity Edge",
                "--date",
                "2026-06-10",
            ]
        )
        mismatch = create_edge_paper(identity_root, "Identity Mismatch Edge")
        set_paper_id(mismatch, "PAPER-9999")
        run_fail(
            [sys.executable, script("check_paper.py"), str(mismatch)],
            "paper_id PAPER-9999 does not match filename PAPER-0001",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(identity_root), "--strict"],
            "paper_id PAPER-9999 does not match filename PAPER-0001",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(identity_root), "--last", "1"],
            "Cannot combine invalid papers",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(mismatch), "Research Ready"],
            "paper_id PAPER-9999 does not match filename PAPER-0001",
        )
        run_fail(
            [sys.executable, script("agent_review.py"), str(mismatch)],
            "paper_id PAPER-9999 does not match filename PAPER-0001",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(mismatch)],
            "paper_id PAPER-9999 does not match filename PAPER-0001",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(identity_root),
                "--title",
                "Invalid Identity Target Review",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
            ],
            "paper_id PAPER-9999 does not match filename PAPER-0001",
        )
        zero_root = project / "zero-id-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(zero_root),
                "--project-name",
                "Loop Paper Zero ID Edge",
                "--date",
                "2026-06-10",
            ]
        )
        zero_id = create_edge_paper(zero_root, "Zero ID Edge")
        set_paper_id(zero_id, "PAPER-0000")
        zero_path = zero_id.with_name("PAPER-0000-zero-id-edge.md")
        zero_id.rename(zero_path)
        run_fail(
            [sys.executable, script("check_paper.py"), str(zero_path)],
            "Invalid paper_id: PAPER-0000",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(zero_root), "--strict"],
            "Invalid paper_id: PAPER-0000",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(zero_root), "--last", "1"],
            "Invalid paper_id: PAPER-0000",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(zero_path), "Research Ready"],
            "Invalid paper_id: PAPER-0000",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Zero Target Review",
                "--target",
                "PAPER-0000",
                "--format",
                "json",
            ],
            "Expected PAPER-NNNN",
        )
        filename_root = project / "filename-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(filename_root),
                "--project-name",
                "Loop Paper Filename Edge",
                "--date",
                "2026-06-10",
            ]
        )
        bad_filename = create_edge_paper(filename_root, "Bad Filename Edge")
        renamed_bad_filename = bad_filename.with_name("PAPER-bad-filename.md")
        bad_filename.rename(renamed_bad_filename)
        run_fail(
            [sys.executable, script("check_paper.py"), str(renamed_bad_filename)],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(filename_root), "--strict"],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(renamed_bad_filename), "Research Ready"],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        malformed_numeric_filename_root = project / "malformed-numeric-filename-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(malformed_numeric_filename_root),
                "--project-name",
                "Loop Paper Malformed Numeric Filename Edge",
                "--date",
                "2026-06-10",
            ]
        )
        malformed_numeric_filename = create_edge_paper(
            malformed_numeric_filename_root,
            "Malformed Numeric Filename Edge",
        )
        renamed_malformed_numeric_filename = malformed_numeric_filename.with_name("PAPER-0001bad.md")
        malformed_numeric_filename.rename(renamed_malformed_numeric_filename)
        run_fail(
            [sys.executable, script("check_paper.py"), str(renamed_malformed_numeric_filename)],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(malformed_numeric_filename_root), "--strict"],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(malformed_numeric_filename_root),
                "--last",
                "1",
            ],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        run_fail(
            [
                sys.executable,
                script("transition_paper.py"),
                str(renamed_malformed_numeric_filename),
                "Research Ready",
            ],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(malformed_numeric_filename_root),
                "--title",
                "After Malformed Filename",
                "--hypothesis",
                "Creation should reject malformed existing filenames",
                "--finding",
                "ID allocation depends on canonical filenames",
                "--reference",
                "scripts/edge_case_test.py",
                "--date",
                "2026-06-10",
            ],
            "Existing paper filename is not canonical: PAPER-0001bad.md",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(malformed_numeric_filename_root),
                "--title",
                "Review After Malformed Filename",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
                "--date",
                "2026-06-10",
            ],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        malformed_slug_filename_root = project / "malformed-slug-filename-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(malformed_slug_filename_root),
                "--project-name",
                "Loop Paper Malformed Slug Filename Edge",
                "--date",
                "2026-06-10",
            ]
        )
        malformed_slug_filename = create_edge_paper(
            malformed_slug_filename_root,
            "Malformed Slug Filename Edge",
        )
        renamed_malformed_slug_filename = malformed_slug_filename.with_name("PAPER-0001-bad--slug.md")
        malformed_slug_filename.rename(renamed_malformed_slug_filename)
        run_fail(
            [sys.executable, script("check_paper.py"), str(renamed_malformed_slug_filename)],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(malformed_slug_filename_root), "--strict"],
            "Filename must contain canonical PAPER-NNNN ID",
        )
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(malformed_slug_filename_root),
                "--title",
                "After Malformed Slug Filename",
                "--hypothesis",
                "Creation should reject malformed existing slug filenames",
                "--finding",
                "ID allocation depends on canonical filenames",
                "--reference",
                "scripts/edge_case_test.py",
                "--date",
                "2026-06-10",
            ],
            "Existing paper filename is not canonical: PAPER-0001-bad--slug.md",
        )
        missing_relationship_root = project / "missing-relationship-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(missing_relationship_root),
                "--project-name",
                "Loop Paper Missing Relationship Edge",
                "--date",
                "2026-06-10",
            ]
        )
        missing_relationship = create_edge_paper(
            missing_relationship_root,
            "Missing Relationship Edge",
        )
        missing_relationship.write_text(
            missing_relationship.read_text(encoding="utf-8").replace(
                "Extends: None\n",
                "",
                1,
            ),
            encoding="utf-8",
        )
        for command in [
            [sys.executable, script("check_paper.py"), str(missing_relationship)],
            [sys.executable, script("check_paper.py"), str(missing_relationship_root)],
            [sys.executable, script("pipeline.py"), str(missing_relationship_root), "--strict"],
            [sys.executable, script("combine_papers.py"), str(missing_relationship_root), "--last", "1"],
            [sys.executable, script("index_references.py"), str(missing_relationship_root)],
            [sys.executable, script("render_dashboard.py"), str(missing_relationship_root)],
        ]:
            run_fail(command, "Missing relationship line: Extends")
        empty_relationship_root = project / "empty-relationship-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(empty_relationship_root),
                "--project-name",
                "Loop Paper Empty Relationship Edge",
                "--date",
                "2026-06-10",
            ]
        )
        empty_relationship = create_edge_paper(empty_relationship_root, "Empty Relationship Edge")
        empty_relationship.write_text(
            empty_relationship.read_text(encoding="utf-8").replace(
                "Extends: None",
                "Extends:",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(empty_relationship)],
            "Empty relationship line: Extends",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(empty_relationship_root), "--strict"],
            "Empty relationship line: Extends",
        )
        placeholder_relationship_root = project / "placeholder-relationship-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(placeholder_relationship_root),
                "--project-name",
                "Loop Paper Placeholder Relationship Edge",
                "--date",
                "2026-06-10",
            ]
        )
        placeholder_relationship = create_edge_paper(
            placeholder_relationship_root,
            "Placeholder Relationship Edge",
        )
        placeholder_relationship.write_text(
            placeholder_relationship.read_text(encoding="utf-8").replace(
                "Extends: None",
                "Extends: TBD",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(placeholder_relationship)],
            "Invalid relationship value: Extends -> TBD",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(placeholder_relationship_root), "--last", "1"],
            "Invalid relationship value: Extends -> TBD",
        )
        mixed_none_relationship_root = project / "mixed-none-relationship-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(mixed_none_relationship_root),
                "--project-name",
                "Loop Paper Mixed None Relationship Edge",
                "--date",
                "2026-06-10",
            ]
        )
        mixed_none_relationship = create_edge_paper(
            mixed_none_relationship_root,
            "Mixed None Relationship Source",
        )
        create_edge_paper(mixed_none_relationship_root, "Mixed None Relationship Target")
        mixed_none_relationship.write_text(
            mixed_none_relationship.read_text(encoding="utf-8").replace(
                "References: None",
                "References: None, PAPER-0002",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(mixed_none_relationship_root)],
            "Relationship line mixes None with targets: References",
        )
        run_fail(
            [sys.executable, script("index_references.py"), str(mixed_none_relationship_root)],
            "Relationship line mixes None with targets: References",
        )
        prose_relationship_root = project / "prose-relationship-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(prose_relationship_root),
                "--project-name",
                "Loop Paper Prose Relationship Edge",
                "--date",
                "2026-06-10",
            ]
        )
        prose_relationship = create_edge_paper(prose_relationship_root, "Prose Relationship Source")
        create_edge_paper(prose_relationship_root, "Prose Relationship Target")
        prose_relationship.write_text(
            prose_relationship.read_text(encoding="utf-8").replace(
                "References: None",
                "References: PAPER-0002 and background notes",
                1,
            ),
            encoding="utf-8",
        )
        for command in [
            [sys.executable, script("check_paper.py"), str(prose_relationship_root)],
            [sys.executable, script("pipeline.py"), str(prose_relationship_root), "--strict"],
            [sys.executable, script("combine_papers.py"), str(prose_relationship_root), "--last", "1"],
            [sys.executable, script("render_dashboard.py"), str(prose_relationship_root)],
        ]:
            run_fail(command, "Invalid relationship value: References -> PAPER-0002 and background notes")
        duplicate_relationship_target_root = project / "duplicate-relationship-target-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(duplicate_relationship_target_root),
                "--project-name",
                "Loop Paper Duplicate Relationship Target Edge",
                "--date",
                "2026-06-10",
            ]
        )
        duplicate_relationship_target = create_edge_paper(
            duplicate_relationship_target_root,
            "Duplicate Relationship Target Source",
        )
        create_edge_paper(duplicate_relationship_target_root, "Duplicate Relationship Target")
        duplicate_relationship_target.write_text(
            duplicate_relationship_target.read_text(encoding="utf-8").replace(
                "References: None",
                "References: PAPER-0002, PAPER-0002",
                1,
            ),
            encoding="utf-8",
        )
        for command in [
            [sys.executable, script("check_paper.py"), str(duplicate_relationship_target)],
            [sys.executable, script("pipeline.py"), str(duplicate_relationship_target_root), "--strict"],
            [sys.executable, script("index_references.py"), str(duplicate_relationship_target_root)],
        ]:
            run_fail(command, "Duplicate relationship target: References -> PAPER-0002")
        dangling_root = project / "dangling-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(dangling_root),
                "--project-name",
                "Loop Paper Dangling Edge",
                "--date",
                "2026-06-10",
            ]
        )
        dangling = create_edge_paper(dangling_root, "Dangling Reference Edge")
        make_before_ready_with_uppercase_checks(dangling)
        dangling.write_text(
            dangling.read_text(encoding="utf-8").replace(
                "References: None",
                "References: PAPER-9999",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(dangling_root)],
            "Dangling relationship target: References -> PAPER-9999",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(dangling)],
            "Dangling relationship target: References -> PAPER-9999",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(dangling_root), "--strict"],
            "Dangling relationship target: References -> PAPER-9999",
        )
        run_fail(
            [
                sys.executable,
                script("check_closed_loop_paper.py"),
                str(dangling),
                "--phase",
                "before",
            ],
            "Dangling relationship target: References -> PAPER-9999",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(dangling_root), "--last", "1"],
            "Dangling relationship target: References -> PAPER-9999",
        )
        for command in [
            [sys.executable, script("index_references.py"), str(dangling_root)],
            [sys.executable, script("score_impact.py"), str(dangling_root)],
            [sys.executable, script("export_report.py"), str(dangling_root)],
            [sys.executable, script("render_dashboard.py"), str(dangling_root)],
        ]:
            run_fail(command, "Dangling relationship target: References -> PAPER-9999")
        run_fail(
            [sys.executable, script("transition_paper.py"), str(dangling), "Research Ready"],
            "Dangling relationship target: References -> PAPER-9999",
        )
        run_fail(
            [sys.executable, script("agent_review.py"), str(dangling)],
            "Dangling relationship target: References -> PAPER-9999",
        )
        run_fail(
            [sys.executable, script("update_paper_metadata.py"), str(dangling)],
            "Dangling relationship target: References -> PAPER-9999",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(dangling_root),
                "--title",
                "Dangling Target Review",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
            ],
            "Dangling relationship target: References -> PAPER-9999",
        )
        malformed_relationship_root = project / "malformed-relationship-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(malformed_relationship_root),
                "--project-name",
                "Loop Paper Malformed Relationship Edge",
                "--date",
                "2026-06-10",
            ]
        )
        malformed_relationship = create_edge_paper(
            malformed_relationship_root,
            "Malformed Relationship Source",
        )
        create_edge_paper(malformed_relationship_root, "Malformed Relationship Target")
        malformed_relationship.write_text(
            malformed_relationship.read_text(encoding="utf-8").replace(
                "References: None",
                "References: PAPER-0002bad",
                1,
            ),
            encoding="utf-8",
        )
        for command in [
            [sys.executable, script("check_paper.py"), str(malformed_relationship_root)],
            [sys.executable, script("pipeline.py"), str(malformed_relationship_root), "--strict"],
            [sys.executable, script("combine_papers.py"), str(malformed_relationship_root), "--last", "1"],
            [sys.executable, script("index_references.py"), str(malformed_relationship_root)],
            [sys.executable, script("render_dashboard.py"), str(malformed_relationship_root)],
        ]:
            run_fail(command, "Invalid relationship target: References -> PAPER-0002bad")
        duplicate_relationship_line_root = project / "duplicate-relationship-line-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(duplicate_relationship_line_root),
                "--project-name",
                "Loop Paper Duplicate Relationship Line Edge",
                "--date",
                "2026-06-10",
            ]
        )
        duplicate_relationship_line = create_edge_paper(
            duplicate_relationship_line_root,
            "Duplicate Relationship Line Source",
        )
        create_edge_paper(duplicate_relationship_line_root, "Duplicate Relationship Line Target")
        duplicate_relationship_line.write_text(
            duplicate_relationship_line.read_text(encoding="utf-8").replace(
                "References: None",
                "References: None\nReferences: PAPER-0002",
                1,
            ),
            encoding="utf-8",
        )
        for command in [
            [sys.executable, script("check_paper.py"), str(duplicate_relationship_line_root)],
            [sys.executable, script("render_dashboard.py"), str(duplicate_relationship_line_root)],
            [sys.executable, script("index_references.py"), str(duplicate_relationship_line_root)],
        ]:
            run_fail(command, "Duplicate relationship line: References")
        self_relation_root = project / "self-relation-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(self_relation_root),
                "--project-name",
                "Loop Paper Self Relation Edge",
                "--date",
                "2026-06-10",
            ]
        )
        self_relation = create_edge_paper(self_relation_root, "Self Relation Edge")
        self_relation.write_text(
            self_relation.read_text(encoding="utf-8").replace(
                "Depends on: None",
                "Depends on: PAPER-0001",
                1,
            ),
            encoding="utf-8",
        )
        run_fail(
            [sys.executable, script("check_paper.py"), str(self_relation_root)],
            "Self relationship target: Depends on -> PAPER-0001",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(self_relation_root), "--strict"],
            "Self relationship target: Depends on -> PAPER-0001",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(self_relation_root), "--last", "1"],
            "Self relationship target: Depends on -> PAPER-0001",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(self_relation), "Research Ready"],
            "Self relationship target: Depends on -> PAPER-0001",
        )
        duplicate_root = project / "duplicate-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(duplicate_root),
                "--project-name",
                "Loop Paper Duplicate Edge",
                "--date",
                "2026-06-10",
            ]
        )
        duplicate = create_edge_paper(duplicate_root, "Duplicate Identity Edge")
        duplicate_copy = duplicate.with_name("PAPER-0001-duplicate-copy.md")
        duplicate_copy.write_text(duplicate.read_text(encoding="utf-8"), encoding="utf-8")
        run_fail(
            [sys.executable, script("check_paper.py"), str(duplicate_root)],
            "Duplicate paper_id in stack: PAPER-0001",
        )
        run_fail(
            [sys.executable, script("pipeline.py"), str(duplicate_root), "--strict"],
            "Duplicate paper_id in stack: PAPER-0001",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(duplicate_root), "--last", "1"],
            "Duplicate paper_id in stack: PAPER-0001",
        )
        run_fail(
            [sys.executable, script("transition_paper.py"), str(duplicate), "Research Ready"],
            "Duplicate paper_id in stack: PAPER-0001",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(duplicate_root),
                "--title",
                "Duplicate Target Review",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
            ],
            "Duplicate paper_id in stack: PAPER-0001",
        )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--ids",
                "PAPER-0001",
                "--last",
                "1",
            ],
            "Choose exactly one selection mode",
        )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--ids",
                "PAPER-0001",
                "PAPER-0001",
            ],
            "Duplicate paper IDs in --ids: PAPER-0001",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(root), "--from", "PAPER-0001"],
            "Interval selection requires both --from and --to",
        )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--from",
                "PAPER-0000",
                "--to",
                "PAPER-0001",
            ],
            "Expected PAPER-NNNN",
        )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--from",
                "PAPER-1",
                "--to",
                "PAPER-0002",
            ],
            "Expected PAPER-NNNN",
        )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--from",
                "PAPER-0001-extra",
                "--to",
                "PAPER-0002",
            ],
            "Expected PAPER-NNNN",
        )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--from",
                "PAPER-0002",
                "--to",
                "PAPER-0001",
            ],
            "--from must be less than or equal to --to",
        )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--from",
                "PAPER-0001",
                "--to",
                "PAPER-9999",
            ],
            "Missing interval boundary paper IDs: PAPER-9999",
        )
        sparse_interval_root = project / "sparse-interval-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(sparse_interval_root),
                "--project-name",
                "Loop Paper Sparse Interval Edge",
                "--date",
                "2026-06-10",
            ]
        )
        sparse_first = create_edge_paper(sparse_interval_root, "Sparse Interval First")
        sparse_second = create_edge_paper(sparse_interval_root, "Sparse Interval Missing")
        sparse_third = create_edge_paper(sparse_interval_root, "Sparse Interval Third")
        sparse_second.unlink()
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(sparse_interval_root),
                "--from",
                "PAPER-0001",
                "--to",
                "PAPER-0003",
            ],
            "Missing interior interval paper IDs: PAPER-0002",
        )
        sparse_ids = run_ok(
            [
                sys.executable,
                script("combine_papers.py"),
                str(sparse_interval_root),
                "--ids",
                "PAPER-0001",
                "PAPER-0003",
                "--json",
            ]
        )
        sparse_payload = json.loads(sparse_ids.stdout)
        if [item["paper_id"] for item in sparse_payload["selected"]] != ["PAPER-0001", "PAPER-0003"]:
            raise SystemExit("Sparse --ids selection did not preserve explicit paper set")
        if sparse_first.name not in sparse_ids.stdout or sparse_third.name not in sparse_ids.stdout:
            raise SystemExit("Sparse --ids output did not include expected paper paths")
        run_fail(
            [sys.executable, script("combine_papers.py"), str(root), "--last", "0"],
            "--last must be greater than zero",
        )
        run_fail(
            [sys.executable, script("combine_papers.py"), str(root), "--last", "999"],
            "--last requested 999 papers",
        )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--last",
                "1",
                "--max-references",
                "0",
            ],
            "--max-references must be greater than zero",
        )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--last",
                "1",
                "--mode",
                "references",
                "--target-paper",
                "PAPER-9999",
            ],
            "Missing target paper ID for reference ranking: PAPER-9999",
        )
        for extra_args in [
            ["--target-paper", "PAPER-0001"],
            ["--query", "ignored reference terms"],
            ["--max-references", "1"],
        ]:
            run_fail(
                [
                    sys.executable,
                    script("combine_papers.py"),
                    str(root),
                    "--last",
                    "1",
                    "--mode",
                    "summary",
                    *extra_args,
                ],
                "Reference ranking options require --mode references or --mode both",
            )
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--last",
                "1",
                "--mode",
                "references",
                "--interval-size",
                "1",
            ],
            "Summary interval options require --mode summary or --mode both: --interval-size",
        )
        output_dir = root / "dashboard" / "output-dir"
        output_dir.mkdir(parents=True)
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--last",
                "1",
                "--output",
                str(output_dir),
            ],
            f"Expected output file, got directory: {output_dir}",
        )
        for command in [
            [sys.executable, script("index_references.py"), str(root), "--output", str(output_dir)],
            [sys.executable, script("score_impact.py"), str(root), "--output", str(output_dir)],
            [sys.executable, script("export_report.py"), str(root), "--output", str(output_dir)],
        ]:
            run_fail(command, f"Expected output file, got directory: {output_dir}")
        papers_output = root / "papers" / "PAPER-9998-generated-output.md"
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--last",
                "1",
                "--output",
                str(papers_output),
            ],
            f"Refusing to write output inside papers directory: {papers_output}",
        )
        for command in [
            [sys.executable, script("index_references.py"), str(root), "--output", str(papers_output)],
            [sys.executable, script("score_impact.py"), str(root), "--output", str(papers_output)],
            [sys.executable, script("export_report.py"), str(root), "--output", str(papers_output)],
        ]:
            run_fail(command, f"Refusing to write output inside papers directory: {papers_output}")
        prompt_papers_output = root / "papers" / "PAPER-9999-review-prompts.md"
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Papers Directory Prompt Output Review",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
                "--prompt-out",
                str(prompt_papers_output),
            ],
            f"Refusing to write prompt output inside papers directory: {prompt_papers_output}",
        )
        if papers_output.exists() or prompt_papers_output.exists():
            raise SystemExit("Generated output guard wrote into papers directory unexpectedly")
        output_parent_file = root / "dashboard" / "output-parent-file"
        output_parent_file.write_text("file parent", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--last",
                "1",
                "--output",
                str(output_parent_file / "combined.md"),
            ],
            f"Expected parent directory for output, got file: {output_parent_file}",
        )
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(root),
                "--title",
                "Parent File Prompt Output Review",
                "--target",
                "PAPER-0001",
                "--format",
                "json",
                "--prompt-out",
                str(output_parent_file / "prompts.json"),
            ],
            f"Expected parent directory for prompt output, got file: {output_parent_file}",
        )
        output_ancestor_file = root / "dashboard" / "output-ancestor-file"
        output_ancestor_file.write_text("file ancestor", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("combine_papers.py"),
                str(root),
                "--last",
                "1",
                "--output",
                str(output_ancestor_file / "nested" / "combined.md"),
            ],
            f"Expected parent directory for output, got file: {output_ancestor_file}",
        )
        dashboard_file_root = project / "dashboard-file-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(dashboard_file_root),
                "--project-name",
                "Loop Paper Dashboard File Edge",
                "--date",
                "2026-06-10",
            ]
        )
        create_edge_paper(dashboard_file_root, "Dashboard File Edge")
        dashboard_file = dashboard_file_root / "dashboard"
        dashboard_file.rmdir()
        dashboard_file.write_text("not a directory", encoding="utf-8")
        run_fail(
            [sys.executable, script("render_dashboard.py"), str(dashboard_file_root)],
            f"Expected dashboard directory, got file: {dashboard_file}",
        )
        papers_file_root = project / "papers-file-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(papers_file_root),
                "--project-name",
                "Loop Paper Papers File Edge",
                "--date",
                "2026-06-10",
            ]
        )
        papers_file = papers_file_root / "papers"
        papers_file.rmdir()
        papers_file.write_text("not a directory", encoding="utf-8")
        run_fail(
            [sys.executable, script("render_dashboard.py"), str(papers_file_root)],
            f"Expected papers directory, got file: {papers_file}",
        )
        for command in [
            [sys.executable, script("check_paper.py"), str(papers_file_root)],
            [sys.executable, script("index_references.py"), str(papers_file_root)],
            [sys.executable, script("score_impact.py"), str(papers_file_root)],
            [sys.executable, script("export_report.py"), str(papers_file_root)],
            [sys.executable, script("pipeline.py"), str(papers_file_root), "--strict"],
            [sys.executable, script("watch_pipeline.py"), str(papers_file_root), "--once"],
            [sys.executable, script("combine_papers.py"), str(papers_file_root), "--last", "1"],
        ]:
            run_fail(command, f"Expected papers directory, got file: {papers_file}")
        stray_markdown_root = project / "stray-markdown-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(stray_markdown_root),
                "--project-name",
                "Loop Paper Stray Markdown Edge",
                "--date",
                "2026-06-10",
            ]
        )
        create_edge_paper(stray_markdown_root, "Stray Markdown Edge")
        stray_markdown = stray_markdown_root / "papers" / "notes.md"
        stray_markdown.write_text("not a paper", encoding="utf-8")
        for command in [
            [sys.executable, script("check_paper.py"), str(stray_markdown_root)],
            [sys.executable, script("index_references.py"), str(stray_markdown_root)],
            [sys.executable, script("score_impact.py"), str(stray_markdown_root)],
            [sys.executable, script("export_report.py"), str(stray_markdown_root)],
            [sys.executable, script("render_dashboard.py"), str(stray_markdown_root)],
            [sys.executable, script("pipeline.py"), str(stray_markdown_root), "--strict"],
            [sys.executable, script("watch_pipeline.py"), str(stray_markdown_root), "--once"],
            [sys.executable, script("combine_papers.py"), str(stray_markdown_root), "--last", "1"],
        ]:
            run_fail(command, "Unexpected paper file in papers directory: notes.md")
        missing_root = project / "missing-root"
        run_fail(
            [sys.executable, script("check_paper.py"), str(missing_root)],
            f"Missing papers directory: {missing_root / 'papers'}",
        )
        for command in [
            [sys.executable, script("update_paper_metadata.py"), str(missing_root)],
            [sys.executable, script("index_references.py"), str(missing_root)],
            [sys.executable, script("score_impact.py"), str(missing_root)],
            [sys.executable, script("export_report.py"), str(missing_root)],
            [sys.executable, script("render_dashboard.py"), str(missing_root)],
            [sys.executable, script("pipeline.py"), str(missing_root), "--strict"],
            [sys.executable, script("watch_pipeline.py"), str(missing_root), "--once"],
            [sys.executable, script("combine_papers.py"), str(missing_root), "--last", "1"],
        ]:
            run_fail(command, f"Missing papers directory: {missing_root / 'papers'}")
        if missing_root.exists():
            raise SystemExit("Stack reader created a missing root unexpectedly")
        overflow_root = project / "overflow-stack"
        run_ok(
            [
                sys.executable,
                script("init_loop_paper.py"),
                "--root",
                str(overflow_root),
                "--project-name",
                "Loop Paper Overflow Edge",
                "--date",
                "2026-06-10",
            ]
        )
        overflow_papers = overflow_root / "papers"
        overflow_papers.mkdir(parents=True, exist_ok=True)
        create_edge_paper(overflow_root, "Overflow Target Edge")
        (overflow_papers / "PAPER-9999-last.md").write_text("", encoding="utf-8")
        run_fail(
            [
                sys.executable,
                script("new_closed_loop_paper.py"),
                "--root",
                str(overflow_root),
                "--title",
                "Overflow Paper",
                "--hypothesis",
                "Overflow should fail",
                "--finding",
                "PAPER-NNNN has a finite range",
                "--reference",
                "scripts/edge_case_test.py",
            ],
            "Cannot allocate next paper ID beyond PAPER-9999",
        )
        overflow_answers = overflow_root / "inbox" / "answers.json"
        overflow_answers.parent.mkdir(parents=True, exist_ok=True)
        write_answers(overflow_answers)
        run_fail(
            [
                sys.executable,
                script("new_review_paper.py"),
                "--root",
                str(overflow_root),
                "--title",
                "Overflow Review",
                "--target",
                "PAPER-0001",
                "--answers",
                str(overflow_answers),
            ],
            "Cannot allocate next paper ID beyond PAPER-9999",
        )

    print("OK loop-paper edge-case test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
