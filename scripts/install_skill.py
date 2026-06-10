#!/usr/bin/env python3
"""Install Loop Paper into common SKILL.md agent directories."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from paperstack_common import file_ancestor


SKILL_NAME = "loop-paper"
ROOT = Path(__file__).resolve().parent.parent

AGENT_ALIASES = {
    "agent": "agents",
    "agents": "agents",
    "agent-skills": "agents",
    "claude": "claude",
    "claude-code": "claude",
    "codex": "codex",
    "hermes": "hermes",
    "hermes-agent": "hermes",
    "openai": "codex",
    "openclaw": "openclaw",
    "clawhub": "openclaw",
    "pi": "pimo",
    "pi-mono": "pimo",
    "pimo": "pimo",
}

USER_DIRS = {
    "agents": ".agents/skills",
    "claude": ".claude/skills",
    "codex": ".codex/skills",
    "hermes": ".hermes/skills",
    "openclaw": ".openclaw/skills",
    "pimo": ".pimo/skills",
}

PROJECT_DIRS = {
    "agents": ".agents/skills",
    "claude": ".claude/skills",
    "codex": ".codex/skills",
    "hermes": "skills",
    "openclaw": "skills",
}

PAYLOAD = [
    "README.md",
    "SKILL.md",
    "agents",
    "assets",
    "docs",
    "references",
    "scripts",
]


def canonical_agent(value: str) -> str:
    key = value.lower().strip()
    if key == "all":
        return "all"
    if key not in AGENT_ALIASES:
        choices = ", ".join(sorted([*AGENT_ALIASES, "all"]))
        raise argparse.ArgumentTypeError(f"unknown agent {value!r}; choose one of: {choices}")
    return AGENT_ALIASES[key]


def install_targets(
    *,
    agent: str,
    scope: str,
    home: Path,
    project_root: Path,
    dest: Path | None,
) -> list[tuple[str, Path]]:
    if dest is not None:
        return [(agent if agent != "all" else "custom", dest.expanduser())]

    agents = sorted(USER_DIRS) if agent == "all" else [agent]
    targets = []
    by_destination: dict[Path, int] = {}
    for item in agents:
        if scope == "user":
            parent = home / USER_DIRS[item]
        else:
            if item not in PROJECT_DIRS:
                continue
            parent = project_root / PROJECT_DIRS[item]
        destination = parent / SKILL_NAME
        key = destination.expanduser()
        if key in by_destination:
            index = by_destination[key]
            label, existing_destination = targets[index]
            targets[index] = (f"{label}+{item}", existing_destination)
            continue
        by_destination[key] = len(targets)
        targets.append((item, destination))
    return targets


def copy_payload(destination: Path, *, force: bool, mode: str, dry_run: bool) -> str:
    source = ROOT
    destination = destination.expanduser()
    source_resolved = source.resolve()
    destination_resolved = destination.resolve(strict=False)

    if destination_resolved != source_resolved:
        if destination_resolved.is_relative_to(source_resolved):
            raise SystemExit(f"Refusing to install inside the source checkout: {destination}")
        if source_resolved.is_relative_to(destination_resolved):
            raise SystemExit(f"Refusing to install over a parent of the source checkout: {destination}")

    if destination.parent.exists() and not destination.parent.is_dir():
        raise SystemExit(f"Expected install parent directory, got file: {destination.parent}")
    blocked = file_ancestor(destination.parent)
    if blocked:
        raise SystemExit(f"Expected install parent directory, got file: {blocked}")

    if destination.is_symlink() and not destination.exists():
        if dry_run:
            return "would-replace-broken-symlink"
        destination.unlink()

    if destination.exists() or destination.is_symlink():
        same_source = False
        try:
            same_source = destination.resolve() == source_resolved
        except FileNotFoundError:
            same_source = False

        if same_source and (mode == "symlink" or not destination.is_symlink()):
            return "already-installed-source"
        if not force:
            raise SystemExit(f"Refusing to overwrite existing destination: {destination}")
        if dry_run:
            return "would-replace"
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        else:
            shutil.rmtree(destination)

    if dry_run:
        return "would-install"

    destination.parent.mkdir(parents=True, exist_ok=True)
    if mode == "symlink":
        destination.symlink_to(source, target_is_directory=True)
        return "symlinked"

    destination.mkdir(parents=True, exist_ok=True)
    for name in PAYLOAD:
        src = source / name
        dst = destination / name
        if src.is_dir():
            shutil.copytree(
                src,
                dst,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
            )
        elif src.exists():
            shutil.copy2(src, dst)
    return "copied"


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Loop Paper into agent skill directories.")
    parser.add_argument(
        "--agent",
        type=canonical_agent,
        default="codex",
        help="Agent target: codex, claude, hermes, pimo/pi, openclaw, agents, or all",
    )
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--home", type=Path, default=Path.home(), help="Home directory for user-scope installs")
    parser.add_argument("--dest", type=Path, help="Explicit destination; bypasses agent/scope path selection")
    parser.add_argument("--mode", choices=("copy", "symlink"), default="copy")
    parser.add_argument("--force", action="store_true", help="Replace an existing destination")
    parser.add_argument("--dry-run", action="store_true", help="Show targets without writing files")
    parser.add_argument("--list", action="store_true", help="List known agent install roots")
    args = parser.parse_args()

    if args.list:
        print("Known user-scope install roots:")
        for agent, path in sorted(USER_DIRS.items()):
            print(f"- {agent}: ~/{path}/{SKILL_NAME}")
        print("Known project-scope install roots:")
        for agent, path in sorted(PROJECT_DIRS.items()):
            print(f"- {agent}: <project>/{path}/{SKILL_NAME}")
        return 0

    targets = install_targets(
        agent=args.agent,
        scope=args.scope,
        home=args.home.expanduser(),
        project_root=args.project_root.resolve(),
        dest=args.dest,
    )
    if not targets:
        raise SystemExit(f"No {args.scope}-scope target is known for agent {args.agent!r}; use --dest.")

    for agent, destination in targets:
        status = copy_payload(destination, force=args.force, mode=args.mode, dry_run=args.dry_run)
        prefix = "DRY-RUN" if args.dry_run else "OK"
        print(f"{prefix} {agent}: {destination} ({status})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
