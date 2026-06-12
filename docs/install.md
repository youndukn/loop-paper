# Installation

Requires `python3` (3.10+) on PATH — every script and the guard hook use it,
with no third-party packages. Without it the scripts fail fast and the guard
hook fails open (Claude Code reports a non-blocking hook error).

Loop Paper is a single-skill repository. Install the directory that contains
`SKILL.md`; bundled `scripts/`, `assets/`, `references/`, and
`agents/openai.yaml` should travel with it.

## One Command

```bash
npx skills add youndukn/loop-paper
```

The [vercel-labs/skills](https://github.com/vercel-labs/skills) CLI copies the
full payload, auto-detects the running agent, and supports 70+ agents
(`-g` for user scope, `--list` to preview).

## Universal Installer

From a cloned checkout:

```bash
python3 scripts/install_skill.py --agent codex
python3 scripts/install_skill.py --agent claude
python3 scripts/install_skill.py --agent hermes
python3 scripts/install_skill.py --agent pi
python3 scripts/install_skill.py --agent all
```

The installer copies the portable skill payload by default. Use `--mode symlink`
when your agent follows symlinks and you want live edits from the checkout.

Useful options:

```bash
python3 scripts/install_skill.py --list
python3 scripts/install_skill.py --agent codex --scope project --project-root /path/to/project
python3 scripts/install_skill.py --dest /custom/skills/loop-paper
python3 scripts/install_skill.py --agent all --dry-run
python3 scripts/install_skill.py --agent codex --force
```

## Platform Paths

| Platform | User install | Project install |
| --- | --- | --- |
| OpenAI Codex | `~/.codex/skills/loop-paper/` | `.codex/skills/loop-paper/` |
| Claude Code | `~/.claude/skills/loop-paper/` | `.claude/skills/loop-paper/` |
| Hermes Agent | `~/.hermes/skills/loop-paper/` | `skills/loop-paper/` |
| pi-mono | `~/.pimo/skills/loop-paper/` | use `--dest` if needed |
| OpenClaw / ClawHub | `~/.openclaw/skills/loop-paper/` | `skills/loop-paper/` |
| Generic Agent Skills | `~/.agents/skills/loop-paper/` | `.agents/skills/loop-paper/` |

After installing, restart or reload the agent session so it rescans skill
directories.

## Manual Clone Examples

```bash
# Codex
git clone https://github.com/youndukn/loop-paper.git ~/.codex/skills/loop-paper

# Claude Code
git clone https://github.com/youndukn/loop-paper.git ~/.claude/skills/loop-paper

# Hermes Agent
git clone https://github.com/youndukn/loop-paper.git ~/.hermes/skills/loop-paper

# pi-mono
git clone https://github.com/youndukn/loop-paper.git ~/.pimo/skills/loop-paper
```

## Validate

```bash
python3 scripts/validate_skill_repo.py
python3 scripts/smoke_test.py
python3 scripts/edge_case_test.py
```
