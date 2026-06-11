#!/usr/bin/env python3
"""
Render the single self-contained test report HTML (Static / Log / BDD tabs, per-mod sections)
from the json data files + the human-authored bdd.md / observe.md.

Called by run_test.py; not usually run directly.
"""
import os, re, json, html, datetime

CSS = """
body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#1e1f22;color:#e6e6e6}
header{padding:14px 22px;background:#2b2d31;border-bottom:1px solid #444}
h1{margin:0;font-size:18px} .sub{color:#9aa;font-size:12px;margin-top:4px}
.tabs{display:flex;gap:4px;padding:8px 22px 0;background:#2b2d31}
.tab{padding:8px 18px;cursor:pointer;border:1px solid #444;border-bottom:none;
 border-radius:6px 6px 0 0;background:#232427;color:#bbb}
.tab.active{background:#1e1f22;color:#fff;font-weight:600}
.panel{display:none;padding:18px 22px} .panel.active{display:block}
.mod{margin:0 0 22px;border:1px solid #3a3c41;border-radius:8px;overflow:hidden}
.mod>h2{margin:0;padding:10px 14px;background:#26282c;font-size:15px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border:1px solid #3a3c41;padding:6px 9px;text-align:left;vertical-align:top}
th{background:#26282c} td.c{text-align:center;width:70px}
.ok{color:#5fcf80;font-weight:600}.bad{color:#ff6b6b;font-weight:600}.warn{color:#e0b24a}
.muted{color:#8a8f98}.pill{padding:2px 8px;border-radius:10px;font-size:12px}
.pill.ok{background:#16361f}.pill.bad{background:#3a1a1a}.pill.warn{background:#382f15}
pre.note{white-space:pre-wrap;background:#232427;border:1px solid #3a3c41;border-radius:6px;
 padding:10px;font-family:inherit;font-size:13px;color:#cdd}
details>summary{cursor:pointer;color:#9aa}
code{background:#2b2d31;padding:1px 5px;border-radius:4px;font-size:12px}
.small{font-size:11px;color:#8a8f98}
.observe{font-size:11px;line-height:1.45;color:#aeb4bd;margin:6px 0 12px}
.observe .oh{font-weight:600;color:#cdd;font-size:11px;text-transform:uppercase;
 letter-spacing:.4px;margin:8px 0 2px}
.observe ul{margin:1px 0 4px 16px;padding:0}.observe li{margin:1px 0}
.observe>div{margin:1px 0}.observe code{font-size:10px}
#toTop{position:fixed;right:18px;bottom:18px;padding:9px 14px;border-radius:20px;
 background:#3a6df0;color:#fff;font-size:12px;cursor:pointer;opacity:.85;transition:opacity .2s;
 box-shadow:0 2px 8px rgba(0,0,0,.4);user-select:none;z-index:50}
#toTop:hover{opacity:1}
"""

JS = """
function show(i){
 document.querySelectorAll('.tab').forEach((t,k)=>t.classList.toggle('active',k==i));
 document.querySelectorAll('.panel').forEach((p,k)=>p.classList.toggle('active',k==i));
}
function toTop(){window.scrollTo({top:0,behavior:'smooth'});
 document.documentElement.scrollTop=0;document.body.scrollTop=0;}
"""


def esc(s):
    return html.escape(str(s))


def md_block(text):
    """Compact markdown -> HTML for observe.md: small font, tight lists, no blank-line padding."""
    out, in_list = [], False

    def inline(s):
        s = esc(s)
        s = re.sub(r"_(.+?)_", r"<em class='muted'>\1</em>", s)
        return re.sub(r"`(.+?)`", r"<code>\1</code>", s)

    def close():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for raw in text.splitlines():
        ln = raw.strip()
        if not ln:
            continue                                  # skip blanks (no <br> padding)
        if ln.startswith("#"):
            close()
            out.append(f"<div class='oh'>{esc(ln.lstrip('#').strip())}</div>")
        elif ln.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(ln[2:])}</li>")
        else:
            close()
            out.append(f"<div>{inline(ln)}</div>")
    close()
    return "\n".join(out)


def _yn(s):
    s = (s or "").strip().upper()
    return "Y" if s in ("Y", "YES") else "N" if s in ("N", "NO") else ""


def parse_bdd(text):
    """Parse the markdown table rows into [{num,q,exp,yn,comment}] (5-column format)."""
    rows = []
    for ln in text.splitlines():
        if not ln.strip().startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        if cells[0] in ("#", "") or set(cells[0]) <= set("-: "):
            continue
        rows.append({"num": cells[0], "q": cells[1], "exp": cells[2],
                     "yn": cells[3], "comment": cells[4]})
    return rows


def static_tab(mods):
    h = []
    for mod, st in mods:
        s = st["summary"]
        cls = "ok" if s["failed"] == 0 else "bad"
        h.append(f"<div class='mod'><h2>{esc(mod)} "
                 f"<span class='pill {cls}'>{s['passed']}/{s['checks']} passed</span></h2>")
        h.append("<table><tr><th>File</th><th>Encoding</th><th>Braces</th>"
                 "<th>Quotes</th><th>Folder</th></tr>")
        m = st["metadata"]
        mc = "ok" if m["ok"] else "bad"
        h.append(f"<tr><td><b>.metadata/metadata.json</b></td>"
                 f"<td colspan=4 class='{mc}'>{esc(m['msg'])}</td></tr>")
        for f in st["files"]:
            c = f["checks"]
            def cell(k):
                v = c.get(k)
                if not v or v["ok"] is None:
                    return "<td class='muted c'>-</td>"
                return f"<td class='c {'ok' if v['ok'] else 'bad'}'>{'OK' if v['ok'] else esc(v['msg'])}</td>"
            h.append(f"<tr><td>{esc(f['path'])}</td>"
                     f"{cell('encoding')}{cell('braces')}{cell('quotes')}{cell('folder')}</tr>")
        h.append("</table></div>")
    return "\n".join(h)


def log_tab(mods, logdata):
    h = []
    md = logdata["mods"]
    for mod, _ in mods:
        d = md.get(mod, {"errors": [], "census": []})
        h.append(f"<div class='mod'><h2>{esc(mod)}</h2>")
        if d["census"]:
            h.append("<table><tr><th>Country</th><th>Building</th><th>Type</th>"
                     "<th>Have</th><th>Need</th><th>Placed</th><th>Cap</th><th>OK</th></tr>")
            for r in d["census"]:
                ok = "ok" if r["ok"] else "bad"
                exp = r["expected"] if r["expected"] is not None else "?"
                need = r.get("need")
                need = need if need is not None else "?"
                ctry = r.get("country", "?")
                h.append(f"<tr><td>{esc(ctry)}</td><td>{esc(r['building'])}</td>"
                         f"<td>{esc(r['type'])}</td><td class='c'>{r.get('have', 0)}</td>"
                         f"<td class='c'>{need}</td><td class='c'>{r['placed']}</td>"
                         f"<td class='c'>{exp}</td>"
                         f"<td class='c {ok}'>{'OK' if r['ok'] else 'NO'}</td></tr>")
            h.append("</table>")
        for t in d.get("tables", []):
            h.append(f"<p class='small' style='margin-bottom:3px'><b>{esc(t['title'])}</b></p>")
            if t["rows"]:
                h.append("<table><tr>" + "".join(f"<th>{esc(c)}</th>" for c in t["columns"]) + "</tr>")
                for row in t["rows"]:
                    h.append("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in row) + "</tr>")
                h.append("</table>")
            else:
                h.append("<p class='muted small'>no rows logged (mod didn't emit this table "
                         "— check it ran / re-run the game)</p>")
        real = [e for e in d["errors"] if not e["benign"]]
        ben = [e for e in d["errors"] if e["benign"]]
        if real:
            h.append("<p class='bad'>Real errors:</p>")
            for e in real:
                h.append(f"<pre class='note'>{esc(e['text'])}</pre>")
        else:
            h.append("<p class='ok'>No real errors referencing this mod.</p>")
        if ben:
            h.append(f"<details><summary>{len(ben)} benign note(s)</summary>")
            for e in ben:
                h.append(f"<pre class='note'>{esc(e['text'])}</pre>")
            h.append("</details>")
        h.append("</div>")
    nm = logdata["non_mod_errors"]
    groups = logdata.get("non_mod_groups", [])
    h.append(f"<div class='mod'><h2>Non-mod (vanilla / other) real errors "
             f"<span class='pill warn'>{len(nm)}</span> "
             f"<span class='small'>in {len(groups)} files</span></h2>")
    h.append("<p class='small'>Found in the logs but not referencing any tested mod's files. "
             "Grouped by source file; for awareness only, not a blocker for this mod's PR.</p>")
    for g in groups:
        h.append(f"<details><summary><code>{esc(g['file'])}</code> "
                 f"<span class='pill warn'>{g['count']}</span></summary>")
        for t in g["entries"]:
            h.append(f"<pre class='note'>{esc(t)}</pre>")
        h.append("</details>")
    h.append("</div>")
    return "\n".join(h)


def bdd_tab(mods_human):
    h = []
    for mod, observe, bdd in mods_human:
        h.append(f"<div class='mod'><h2>{esc(mod)}</h2>")
        if observe:
            h.append("<div class='observe'>" + md_block(observe) + "</div>")
        rows = parse_bdd(bdd) if bdd else []
        if rows:
            answered = matches = mism = 0
            body = []
            for r in rows:
                exp, ans = _yn(r["exp"]), _yn(r["yn"])
                if not ans:
                    res, rcls = "—", "muted"
                elif not exp:
                    res, rcls = "?", "muted"
                elif ans == exp:
                    res, rcls, matches = "match", "ok", matches + 1
                else:
                    res, rcls, mism = "MISMATCH", "bad", mism + 1
                if ans:
                    answered += 1
                acls = "ok" if ans == "Y" else ("bad" if ans == "N" else "muted")
                body.append(f"<tr><td class='c'>{esc(r['num'])}</td><td>{esc(r['q'])}</td>"
                            f"<td class='c muted'>{esc(exp) or '-'}</td>"
                            f"<td class='c {acls}'>{esc(ans) or '-'}</td>"
                            f"<td class='c {rcls}'>{res}</td><td>{esc(r['comment'])}</td></tr>")
            pill = "ok" if (mism == 0 and answered == len(rows)) else ("bad" if mism else "warn")
            h.append(f"<p class='small'><span class='pill {pill}'>"
                     f"{matches}/{len(rows)} match · {mism} mismatch · "
                     f"{len(rows) - answered} unanswered</span></p>")
            h.append("<table><tr><th>#</th><th>Question</th><th>Exp</th><th>Answer</th>"
                     "<th>Result</th><th>Comment</th></tr>")
            h.append("".join(body) + "</table>")
        h.append("</div>")
    return "\n".join(h)


def bdd_stats(mods_human):
    """Aggregate BDD pass/fail/na across all mods."""
    P = F = NA = 0
    for _, _, bdd in mods_human:
        for r in parse_bdd(bdd or ""):
            e, a = _yn(r["exp"]), _yn(r["yn"])
            if not a:
                NA += 1
            elif e and a == e:
                P += 1
            else:
                F += 1
    return P, F, NA


def render(branch, mods_static, logdata, mods_human, out_path):
    # summary badges
    sfail = sum(s["summary"]["failed"] for _, s in mods_static)
    lreal = logdata["summary"]["mod_real_errors"]
    bP, bF, bNA = bdd_stats(mods_human)
    def badge(ok, label, cls=None):
        return f"<span class='pill {cls or ('ok' if ok else 'bad')}'>{label}</span>"
    bdd_cls = "ok" if (bF == 0 and bNA == 0) else ("bad" if bF else "warn")
    head = (f"<h1>Vic3 test report — <code>{esc(branch)}</code></h1>"
            f"<div class='sub'>generated {datetime.datetime.now().isoformat(timespec='seconds')} "
            f"&nbsp; {badge(sfail==0,f'static: {sfail} fail')} "
            f"{badge(lreal==0,f'log: {lreal} mod errors')} "
            f"{badge(None,f'bdd: {bP} PASS | {bF} FAIL | {bNA} NA', bdd_cls)} "
            f"&nbsp; mods: {esc(', '.join(m for m,_ in mods_static))}</div>"
            "<div class='sub small'>Re-run <code>python sanity-check/testkit/run_test.py</code> "
            "after a fix, then press F5.</div>")
    doc = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Vic3 test — {esc(branch)}</title><style>{CSS}</style></head><body>
<header>{head}</header>
<div class="tabs">
 <div class="tab active" onclick="show(0)">Static</div>
 <div class="tab" onclick="show(1)">Log</div>
 <div class="tab" onclick="show(2)">BDD</div>
</div>
<div class="panel active">{static_tab(mods_static)}</div>
<div class="panel">{log_tab(mods_static, logdata)}</div>
<div class="panel">{bdd_tab(mods_human)}</div>
<div id="toTop" onclick="toTop()">↑ Top</div>
<script>{JS}</script></body></html>"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    return out_path
