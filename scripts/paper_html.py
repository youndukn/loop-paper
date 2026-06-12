#!/usr/bin/env python3
"""HTML paper container: canonical markdown source embedded in a self-rendering HTML file.

A paper is one .html file. The byte-exact, gate-checked source lives in
<script type="text/markdown" id="paper-source">; an inline renderer displays
it as HTML (tables, checkboxes, diff highlighting). Fenced ```html blocks are
injected live, so papers can carry interactive explanations.
"""

from __future__ import annotations

import re
from pathlib import Path


PAPER_SOURCE_OPEN = '<script type="text/markdown" id="paper-source">'
INTERACTIVE_FENCE = "```html"
PAPER_SOURCE_CLOSE = "</script>"
TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", flags=re.MULTILINE)

RENDERER = r"""
function esc(s){return s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function inline(s){return esc(s).replace(/`([^`]+)`/g,'<code>$1</code>');}
function render(src){
  const out=[];const lines=src.split('\n');let i=0;
  if(lines[0]==='---'){const fm=[];i=1;while(i<lines.length&&lines[i]!=='---'){fm.push(lines[i]);i++;}i++;
    out.push('<details class="fm"><summary>metadata</summary><pre>'+esc(fm.join('\n'))+'</pre></details>');}
  while(i<lines.length){
    const line=lines[i];
    const fence=line.match(/^(```+|~~~+)\s*(\S*)\s*$/);
    if(fence){const lang=fence[2];const buf=[];i++;
      while(i<lines.length&&!lines[i].startsWith(fence[1])){buf.push(lines[i]);i++;}i++;
      const body=buf.join('\n');
      if(lang==='html'){out.push('<div class="live">'+body+'</div>');}
      else if(lang==='diff'){out.push('<pre class="code">'+buf.map(l=>l.startsWith('+')?'<span class="add">'+esc(l)+'</span>':l.startsWith('-')?'<span class="del">'+esc(l)+'</span>':esc(l)).join('\n')+'</pre>');}
      else{out.push('<pre class="code">'+esc(body)+'</pre>');}
      continue;}
    const h=line.match(/^(#{1,4})\s+(.*)$/);
    if(h){out.push('<h'+h[1].length+'>'+inline(h[2])+'</h'+h[1].length+'>');i++;continue;}
    if(line.startsWith('|')){const rows=[];while(i<lines.length&&lines[i].startsWith('|')){rows.push(lines[i]);i++;}
      out.push('<table>'+rows.filter(r=>!/^\|[\s:-]+\|/.test(r.replace(/[^|\s:-]/g,'x'))||!/---/.test(r)).filter(r=>!/^[\s|:-]+$/.test(r)).map((r,idx)=>{
        const cells=r.replace(/^\||\|$/g,'').split('|').map(c=>inline(c.trim()));
        const tag=idx===0?'th':'td';
        return '<tr>'+cells.map(c=>'<'+tag+'>'+c+'</'+tag+'>').join('')+'</tr>';
      }).join('')+'</table>');continue;}
    const cb=line.match(/^\s*-\s+\[([ xX])\]\s+(.*)$/);
    if(cb){out.push('<div class="cb"><label><input type="checkbox"'+(cb[1]===' '?'':' checked')+'> '+inline(cb[2])+'</label></div>');i++;continue;}
    if(/^\s*-\s+/.test(line)){const items=[];while(i<lines.length&&/^\s*-\s+/.test(lines[i])&&!/\[[ xX]\]/.test(lines[i])){items.push(lines[i].replace(/^\s*-\s+/,''));i++;}
      if(items.length){out.push('<ul>'+items.map(x=>'<li>'+inline(x)+'</li>').join('')+'</ul>');continue;}}
    if(line.trim()===''){i++;continue;}
    const para=[];while(i<lines.length&&lines[i].trim()!==''&&!/^(#{1,4}\s|```|~~~|\||\s*-\s)/.test(lines[i])){para.push(lines[i]);i++;}
    if(para.length){out.push('<p>'+inline(para.join(' '))+'</p>');}else{i++;}
  }
  return out.join('\n');
}
const srcEl=document.getElementById('paper-source');
document.getElementById('paper-body').innerHTML=render(srcEl.textContent.replace(/<\\\/script/g,'</'+'script').replace(/^\n/,''));
const KEY='loop-paper:'+location.pathname;
let saved={};try{saved=JSON.parse(localStorage.getItem(KEY)||'{}');}catch(e){}
document.querySelectorAll('#paper-body input[type=checkbox]').forEach((el,i)=>{
  if(saved[i]!==undefined){el.checked=saved[i];el.parentElement.classList.add('touched');}
  el.addEventListener('change',()=>{saved[i]=el.checked;el.parentElement.classList.add('touched');localStorage.setItem(KEY,JSON.stringify(saved));});
});
"""

STYLE = """
body{margin:0 auto;max-width:860px;padding:24px;font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#1f2933;line-height:1.55;}
h1{font-size:24px;border-bottom:1px solid #d9dee7;padding-bottom:8px;}
h2{font-size:19px;margin-top:28px;color:#0f766e;}
h3{font-size:16px;}
table{border-collapse:collapse;margin:10px 0;width:100%;font-size:14px;}
th,td{border:1px solid #d9dee7;padding:6px 9px;text-align:left;vertical-align:top;}
th{background:#f3f5f8;}
pre.code{background:#f3f5f8;border:1px solid #d9dee7;border-radius:6px;padding:10px;overflow:auto;font-size:13px;}
.add{color:#067647;}.del{color:#b42318;}
code{background:#f3f5f8;border-radius:4px;padding:1px 4px;font-size:0.92em;}
.cb{margin:2px 0;}
.touched{outline:1px dashed #b45309;outline-offset:2px;}
.fm{margin-bottom:14px;color:#667085;font-size:13px;}
.fm pre{background:#f7f8fa;padding:8px;border-radius:6px;}
.live{border:1px dashed #d9dee7;border-radius:6px;padding:10px;margin:10px 0;}
"""


def escape_source(source: str) -> str:
    return source.replace("</script", "<\\/script")


def unescape_source(source: str) -> str:
    return source.replace("<\\/script", "</script")


def paper_title(source: str) -> str:
    match = TITLE_RE.search(source)
    return match.group(1) if match else "Paper"


def wrap_paper_source(source: str) -> str:
    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{paper_title(source)}</title>\n"
        f"<style>{STYLE}</style>\n</head>\n<body>\n"
        f"{PAPER_SOURCE_OPEN}\n{escape_source(source)}\n{PAPER_SOURCE_CLOSE}\n"
        "<div id=\"paper-body\"></div>\n"
        f"<script>{RENDERER}</script>\n</body>\n</html>\n"
    )


def is_wrapped(text: str) -> bool:
    return PAPER_SOURCE_OPEN in text


def extract_paper_source(text: str) -> str:
    if not is_wrapped(text):
        return text
    start = text.index(PAPER_SOURCE_OPEN) + len(PAPER_SOURCE_OPEN)
    end = text.index(PAPER_SOURCE_CLOSE, start)
    return unescape_source(text[start:end].strip("\n") + "\n")


def read_paper_text(path: Path) -> str:
    return extract_paper_source(path.read_text(encoding="utf-8"))


def write_paper_text(path: Path, source: str) -> None:
    path.write_text(wrap_paper_source(source), encoding="utf-8")
