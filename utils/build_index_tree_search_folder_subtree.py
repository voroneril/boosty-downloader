#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор index.html: поиск ТОЛЬКО по названиям папок.
Совпала папка — показываем всю её ветку (все подпапки и файлы).
Пустой поиск — показываем всё (папки свёрнуты по сохранённому состоянию).
Есть: подсветка, развернуть/свернуть, счётчик, сохранение состояний.
"""
import html
from pathlib import Path
from urllib.parse import quote

EXCLUDE_DIRS = {".git", "__pycache__", ".idea", ".vscode", "_index"}
ALLOWED_FILE_EXTS = None  # None = все

def is_hidden(p: Path) -> bool:
    return p.name.startswith(".")

def rel_href(root: Path, p: Path) -> str:
    rel = p.relative_to(root).as_posix()
    return quote(rel)

def esc(s: str) -> str:
    return html.escape(s, quote=True)

def collect(root: Path):
    def walk(d: Path, idx=[0]):
        idx[0] += 1
        node = {
            "name": d.name,
            "anchor": f"d{idx[0]}",
            "children": [],
            "files": []
        }
        for f in sorted([x for x in d.iterdir() if x.is_file()], key=lambda x: x.name.lower()):
            if ALLOWED_FILE_EXTS and f.suffix.lower() not in ALLOWED_FILE_EXTS: continue
            if is_hidden(f): continue
            node["files"].append({"name": f.name, "href": rel_href(root, f)})
        for sub in sorted([x for x in d.iterdir() if x.is_dir()], key=lambda x: x.name.lower()):
            if is_hidden(sub) or sub.name in EXCLUDE_DIRS: continue
            node["children"].append(walk(sub))
        return node
    return walk(root)

def render_tree(n: dict) -> str:
    parts = []
    # Files
    if n.get("files"):
        parts.append("<ul class='files'>")
        for f in n["files"]:
            parts.append(
                "<li class='file'><a href='{href}'>{name}</a></li>"
                .replace("{href}", f["href"])
                .replace("{name}", esc(f["name"]))
            )
        parts.append("</ul>")
    # Children
    for ch in n.get("children", []):
        # store original name in data-title (for highlight), and lowercase in data-name
        parts.append(
            "<details class='folder' id='{id}' data-name='{name_lc}'>"
            "<summary><span class='title' data-title='{name_orig}'>{name_orig}</span></summary>"
            "<div class='content'>{inner}</div>"
            "</details>"
            .replace("{id}", ch["anchor"])
            .replace("{name_lc}", esc(ch["name"].lower()))
            .replace("{name_orig}", esc(ch["name"]))
            .replace("{inner}", render_tree(ch))
        )
    return "".join(parts)

def build_html(root_name: str, tree_html: str) -> str:
    base = (
        "<!doctype html><html lang='ru'><head><meta charset='utf-8'/>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
        "<title>Структура — __ROOT__</title>"
        "<style>"
        ":root { --bg:#0b0f14; --panel:#111826; --muted:#8aa0b5; --text:#e6edf3; --accent:#60a5fa; --border:#1f2a3a; }"
        "* { box-sizing:border-box; } body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, Arial; background:#0b0f14; color:var(--text);}"
        "header{ position:sticky; top:0; z-index:10; background:rgba(11,15,20,.85); backdrop-filter:blur(8px); border-bottom:1px solid var(--border);}"
        ".wrap{ max-width:1100px; margin:0 auto; padding:16px;} h1{ margin:0; font-size:22px;} .muted{ color:var(--muted); font-size:12px; }"
        ".toolbar{ display:flex; gap:8px; align-items:center; margin-top:10px; flex-wrap:wrap;}"
        "input[type='search']{ flex:1; min-width:260px; padding:12px 14px; border-radius:12px; border:1px solid var(--border); background:#0f1b2a; color:var(--text); outline:none; }"
        ".btn{ padding:10px 12px; border:1px solid var(--border); border-radius:10px; background:#0f1b2a; color:var(--text); cursor:pointer;}"
        ".btn:hover{ background:#122238; }"
        ".count{ font-size:12px; color:var(--muted);}"
        "section{ margin-top:18px; } details.folder{ border:1px solid var(--border); border-radius:12px; margin:8px 0; }"
        "details.folder>summary{ cursor:pointer; list-style:none; padding:10px 12px; background:#0f1623; font-weight:600; }"
        "details.folder>.content{ padding:8px 12px 12px; }"
        "ul.files{ list-style:none; padding-left:12px; margin:6px 0 0; } ul.files li{ margin:4px 0; } ul.files li a{ color:var(--accent); text-decoration:none;}"
        "ul.files li a:hover{ text-decoration:underline; }"
        ".hidden{ display:none !important; }"
        "mark{ background:#3a7afe55; color:inherit; padding:0 2px; border-radius:4px; }"
        "</style></head><body>"
        "<header><div class='wrap'>"
        "<h1>Структура — __ROOT__</h1>"
        "<div class='muted'>Поиск ТОЛЬКО по папкам. Совпала папка — показываем всю её ветку (подпапки и файлы). Ctrl+/ — фокус на строку поиска.</div>"
        "<div class='toolbar'>"
        "<input id='search' type='search' placeholder='Начните вводить имя папки...'/>"
        "<button id='expandAll' class='btn' type='button'>Развернуть всё</button>"
        "<button id='collapseAll' class='btn' type='button'>Свернуть всё</button>"
        "<span id='matchCount' class='count'></span>"
        "</div>"
        "</div></header>"
        "<main class='wrap'><section id='tree'>__TREE__</section></main>"
        "<script>"
        "try{(function(){"
        "  var q=document.getElementById('search');"
        "  var matchCount=document.getElementById('matchCount');"
        "  var storageKey='tree-open-__ROOT__';"
        "  function norm(s){return (s||'').toLowerCase();}"
        "  function getFolderTitleSpan(det){ var s=det.getElementsByTagName('summary'); if(!s.length) return null; return s[0].getElementsByClassName('title')[0] || null; }"
        "  function getFolderNameLower(det){ var t=getFolderTitleSpan(det); if(!t) return ''; var orig=t.getAttribute('data-title')||t.textContent; return orig.toLowerCase(); }"
        "  function resetHighlights(root){ var spans=root.querySelectorAll('summary .title'); for(var i=0;i<spans.length;i++){ var el=spans[i]; var orig=el.getAttribute('data-title')||el.textContent; el.textContent=orig; }}"
        "  function highlight(el, needle){ if(!el){return;} var txt=el.getAttribute('data-title')||el.textContent; if(!needle){ el.textContent=txt; return;} var low=txt.toLowerCase(); var idx=low.indexOf(needle); if(idx===-1){ el.textContent=txt; return;} el.innerHTML=txt.slice(0,idx)+'<mark>'+txt.slice(idx,idx+needle.length)+'</mark>'+txt.slice(idx+needle.length);}"
        "  function setBranchVisibility(det, visible){ det.classList.toggle('hidden', !visible); var content = null; var list = det.getElementsByClassName('content'); for (var i=0;i<list.length;i++){ if (list[i].parentNode===det){ content=list[i]; break; } } if(content){ var nodes = content.querySelectorAll('details.folder, li.file'); for (var k=0;k<nodes.length;k++){ nodes[k].classList.toggle('hidden', !visible); } } }"
        "  function childFoldersOf(det){ var content = null; var list = det.getElementsByClassName('content'); for (var i=0;i<list.length;i++){ if (list[i].parentNode===det){ content=list[i]; break; } } if(!content) return []; var out=[]; var kids=content.children; for(var j=0;j<kids.length;j++){ if(kids[j].tagName && kids[j].tagName.toLowerCase()==='details' && kids[j].classList.contains('folder')) out.push(kids[j]); } return out; }"
        "  function processFolder(det, needle, ancestorMatched){ var nameMatch = getFolderNameLower(det).indexOf(needle)!==-1; var matched = ancestorMatched || (needle!=='' && nameMatch) || (needle===''); setBranchVisibility(det, matched); var span=getFolderTitleSpan(det); highlight(span, (needle && nameMatch)?needle:''); det.open = (needle!=='' && matched); var subs=childFoldersOf(det); for (var k=0;k<subs.length;k++){ processFolder(subs[k], needle, matched); } return matched; }"
        "  function apply(){ var n=norm(q.value); var root=document.getElementById('tree'); resetHighlights(root); var roots=root.children; for(var r=0;r<roots.length;r++){ if(roots[r].tagName && roots[r].tagName.toLowerCase()==='details' && roots[r].classList.contains('folder')){ processFolder(roots[r], n, false); } } if(n===''){ var all=document.querySelectorAll('details.folder'); for(var i=0;i<all.length;i++){ all[i].classList.remove('hidden'); } restoreOpenState(); matchCount.textContent=''; } else { var visibleFiles=document.querySelectorAll('li.file:not(.hidden)'); var visibleFolders=document.querySelectorAll('details.folder:not(.hidden)'); matchCount.textContent='Найдено папок: '+visibleFolders.length+' | файлов: '+visibleFiles.length; } }"
        "  function saveOpenState(){ var openIds=[]; var all=document.querySelectorAll('details.folder[open]'); for(var i=0;i<all.length;i++){ if(all[i].id) openIds.push(all[i].id); } try{ localStorage.setItem(storageKey, JSON.stringify(openIds)); }catch(e){} }"
        "  function restoreOpenState(){ var raw=localStorage.getItem(storageKey), set=null; try{ set=raw?new Set(JSON.parse(raw)):null; }catch(e){ set=null; } var all=document.querySelectorAll('details.folder'); for(var i=0;i<all.length;i++){ if(set && all[i].id && set.has(all[i].id)) all[i].open=true; else all[i].open=false; } }"
        "  document.addEventListener('toggle', function(e){ if(e && e.target && e.target.tagName && e.target.tagName.toLowerCase()==='details' && e.target.classList.contains('folder')) saveOpenState(); }, true);"
        "  q.addEventListener('input', apply);"
        "  window.addEventListener('keydown', function(e){ if((e.ctrlKey||e.metaKey)&&e.key==='/'){ e.preventDefault(); q.focus(); }});"
        "  document.getElementById('expandAll').addEventListener('click', function(){ var vis=document.querySelectorAll('details.folder:not(.hidden)'); for(var i=0;i<vis.length;i++){ vis[i].open=true; } saveOpenState(); });"
        "  document.getElementById('collapseAll').addEventListener('click', function(){ var all=document.querySelectorAll('details.folder'); for(var i=0;i<all.length;i++){ all[i].open=false; } saveOpenState(); });"
        "  restoreOpenState(); apply();"
        "})();}catch(e){ console.error('Init error:', e); }"
        "</script>"
        "</body></html>"
    )
    return base.replace("__ROOT__", esc(root_name)).replace("__TREE__", tree_html)

def main():
    root = Path(__file__).resolve().parent
    data = collect(root)
    tree_html = render_tree(data)
    html = build_html(root.name, tree_html)
    (root / "index.html").write_text(html, encoding="utf-8")
    print("Готово:", root / "index.html")

if __name__ == "__main__":
    main()
