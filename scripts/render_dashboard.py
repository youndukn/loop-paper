#!/usr/bin/env python3
"""Render an interactive Paper Stack dashboard from markdown papers."""

from __future__ import annotations

import argparse
import html
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


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    return data


def split_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[start:end].strip()
    return sections


def find_ids(text: str) -> list[str]:
    return sorted(set(re.findall(r"PAPER-\d{4}", text)))


def summarize_paper(path: Path, root: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    sections = split_sections(text)
    paper_id = meta.get("paper_id") or re.search(r"PAPER-\d{4}", path.name).group(0)
    missing = [section for section in REQUIRED_SECTIONS if section not in sections]
    unchecked = len(re.findall(r"- \[ \]", text))
    checked = len(re.findall(r"- \[x\]", text, flags=re.IGNORECASE))
    references = [paper for paper in find_ids(sections.get("References", "")) if paper != paper_id]
    relations = {}
    for name in ["References", "Depends on", "Supersedes", "Contradicts", "Extends"]:
        match = re.search(rf"^{re.escape(name)}:\s*(.+)$", text, flags=re.MULTILINE)
        relations[name.lower().replace(" ", "_")] = find_ids(match.group(1)) if match else []

    return {
        "paper_id": paper_id,
        "title": meta.get("title", path.stem),
        "status": meta.get("status", "Draft"),
        "impact_score": meta.get("impact_score", "TBD"),
        "path": str(path),
        "relative_path": str(path.relative_to(root.parent)) if path.is_relative_to(root.parent) else str(path),
        "missing_sections": missing,
        "checked": checked,
        "unchecked": unchecked,
        "references": references,
        "relations": relations,
    }


def write_dashboard(root: Path, papers: list[dict]) -> None:
    dashboard = root / "dashboard"
    dashboard.mkdir(parents=True, exist_ok=True)
    (dashboard / "data.json").write_text(json.dumps({"papers": papers, "statuses": STATUSES}, indent=2), encoding="utf-8")

    data = json.dumps({"papers": papers, "statuses": STATUSES})
    html_text = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Paper Stack Dashboard</title>
<style>
:root {{
  color-scheme: light;
  --bg: #f7f8fa;
  --panel: #ffffff;
  --text: #1f2933;
  --muted: #667085;
  --line: #d9dee7;
  --accent: #0f766e;
  --warn: #b45309;
  --bad: #b42318;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); }}
header {{ padding: 24px 28px 16px; border-bottom: 1px solid var(--line); background: var(--panel); }}
h1 {{ margin: 0 0 12px; font-size: 24px; line-height: 1.2; letter-spacing: 0; }}
.controls {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
input, select {{ height: 36px; border: 1px solid var(--line); border-radius: 6px; padding: 0 10px; background: white; color: var(--text); }}
main {{ padding: 18px 20px 28px; }}
.summary {{ display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 10px; margin-bottom: 16px; }}
.metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px; }}
.metric b {{ display: block; font-size: 22px; margin-bottom: 4px; }}
.metric span {{ color: var(--muted); font-size: 13px; }}
.board {{ display: grid; grid-template-columns: repeat(10, minmax(220px, 1fr)); gap: 12px; overflow-x: auto; padding-bottom: 10px; }}
.column {{ background: #eef1f5; border: 1px solid var(--line); border-radius: 8px; min-height: 360px; padding: 10px; }}
.column h2 {{ margin: 0 0 10px; font-size: 14px; line-height: 1.3; }}
.card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 10px; margin-bottom: 10px; cursor: pointer; }}
.card:hover {{ border-color: var(--accent); }}
.card strong {{ display: block; font-size: 13px; color: var(--accent); margin-bottom: 4px; }}
.card h3 {{ margin: 0 0 8px; font-size: 15px; line-height: 1.25; letter-spacing: 0; }}
.badges {{ display: flex; gap: 6px; flex-wrap: wrap; }}
.badge {{ font-size: 12px; border: 1px solid var(--line); border-radius: 999px; padding: 3px 7px; color: var(--muted); background: #fbfcfe; }}
.badge.warn {{ color: var(--warn); border-color: #f3c27b; }}
.badge.bad {{ color: var(--bad); border-color: #f2a29b; }}
dialog {{ width: min(760px, calc(100vw - 32px)); border: 1px solid var(--line); border-radius: 8px; padding: 0; }}
dialog::backdrop {{ background: rgba(15, 23, 42, 0.35); }}
.detail {{ padding: 18px; }}
.detail h2 {{ margin: 0 0 8px; font-size: 20px; }}
.detail pre {{ white-space: pre-wrap; background: #f3f5f8; border: 1px solid var(--line); border-radius: 6px; padding: 10px; overflow: auto; }}
.close {{ float: right; height: 32px; border: 1px solid var(--line); background: white; border-radius: 6px; }}
@media (max-width: 760px) {{
  .summary {{ grid-template-columns: repeat(2, 1fr); }}
  header {{ padding: 18px; }}
  main {{ padding: 14px; }}
}}
</style>
</head>
<body>
<header>
  <h1>Paper Stack Dashboard</h1>
  <div class="controls">
    <input id="search" type="search" placeholder="Search papers">
    <select id="status"><option value="">All statuses</option></select>
    <select id="filter">
      <option value="">All papers</option>
      <option value="missing">Missing sections</option>
      <option value="human">Human review needed</option>
      <option value="impact">Impact TBD</option>
    </select>
  </div>
</header>
<main>
  <section class="summary" id="summary"></section>
  <section class="board" id="board"></section>
</main>
<dialog id="dialog"><div class="detail"><button class="close" onclick="dialog.close()">Close</button><div id="detail"></div></div></dialog>
<script>
const DATA = {data};
const board = document.getElementById('board');
const summary = document.getElementById('summary');
const search = document.getElementById('search');
const statusSelect = document.getElementById('status');
const filterSelect = document.getElementById('filter');
const dialog = document.getElementById('dialog');
const detail = document.getElementById('detail');

for (const status of DATA.statuses) {{
  const option = document.createElement('option');
  option.value = status;
  option.textContent = status;
  statusSelect.appendChild(option);
}}

function visiblePapers() {{
  const q = search.value.toLowerCase();
  const status = statusSelect.value;
  const filter = filterSelect.value;
  return DATA.papers.filter(p => {{
    const text = `${{p.paper_id}} ${{p.title}}`.toLowerCase();
    if (q && !text.includes(q)) return false;
    if (status && p.status !== status) return false;
    if (filter === 'missing' && p.missing_sections.length === 0) return false;
    if (filter === 'human' && p.status !== 'Human Review Required') return false;
    if (filter === 'impact' && p.impact_score !== 'TBD') return false;
    return true;
  }});
}}

function renderSummary(papers) {{
  const accepted = papers.filter(p => p.status === 'Accepted').length;
  const human = papers.filter(p => p.status === 'Human Review Required').length;
  const missing = papers.filter(p => p.missing_sections.length).length;
  const impact = papers.filter(p => p.impact_score !== 'TBD').length;
  summary.innerHTML = [
    ['Papers', papers.length],
    ['Accepted', accepted],
    ['Human review', human],
    ['Scored impact', impact],
  ].map(([label, value]) => `<div class="metric"><b>${{value}}</b><span>${{label}}</span></div>`).join('');
}}

function openDetail(p) {{
  detail.innerHTML = `
    <h2>${{escapeHtml(p.paper_id)}} ${{escapeHtml(p.title)}}</h2>
    <p>Status: <b>${{escapeHtml(p.status)}}</b> | Impact: <b>${{escapeHtml(p.impact_score)}}</b></p>
    <p>Path: <code>${{escapeHtml(p.path)}}</code></p>
    <pre>Missing sections: ${{p.missing_sections.length ? p.missing_sections.join(', ') : 'none'}}
References: ${{p.references.length ? p.references.join(', ') : 'none'}}
Checked gates: ${{p.checked}}
Unchecked gates: ${{p.unchecked}}</pre>
  `;
  dialog.showModal();
}}

function escapeHtml(value) {{
  return String(value).replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
}}

function render() {{
  const papers = visiblePapers();
  renderSummary(papers);
  board.innerHTML = '';
  for (const status of DATA.statuses) {{
    const column = document.createElement('section');
    column.className = 'column';
    const inColumn = papers.filter(p => p.status === status);
    column.innerHTML = `<h2>${{status}} (${{inColumn.length}})</h2>`;
    for (const p of inColumn) {{
      const card = document.createElement('article');
      card.className = 'card';
      const missingClass = p.missing_sections.length ? 'bad' : '';
      const impactClass = p.impact_score === 'TBD' ? 'warn' : '';
      card.innerHTML = `
        <strong>${{escapeHtml(p.paper_id)}}</strong>
        <h3>${{escapeHtml(p.title)}}</h3>
        <div class="badges">
          <span class="badge ${{missingClass}}">${{p.missing_sections.length}} missing</span>
          <span class="badge">${{p.references.length}} refs</span>
          <span class="badge ${{impactClass}}">impact ${{escapeHtml(p.impact_score)}}</span>
        </div>
      `;
      card.addEventListener('click', () => openDetail(p));
      column.appendChild(card);
    }}
    board.appendChild(column);
  }}
}}

search.addEventListener('input', render);
statusSelect.addEventListener('change', render);
filterSelect.addEventListener('change', render);
render();
</script>
</body>
</html>
"""
    (dashboard / "index.html").write_text(html_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Paper Stack dashboard.")
    parser.add_argument("root", nargs="?", default=".paper-stack", help="Paper Stack root directory")
    args = parser.parse_args()

    root = Path(args.root)
    papers_dir = root / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)
    papers = [summarize_paper(path, root) for path in sorted(papers_dir.glob("PAPER-*.md"))]
    write_dashboard(root, papers)
    print(root / "dashboard" / "index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
