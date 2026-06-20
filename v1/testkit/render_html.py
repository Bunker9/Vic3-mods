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
.observe table.obs{font-size:10px;margin:4px 0 9px;width:auto;min-width:60%}
.observe table.obs th,.observe table.obs td{padding:3px 7px}
.observe table.obs th{background:#23252a;color:#cdd;font-weight:600}
.stamp{font-size:11px;font-weight:400;color:#9aa;margin-left:8px}
.stamp b{color:#cdd;font-weight:600}
.stamp .src{font-size:10px;padding:1px 6px;border-radius:8px;margin-left:6px}
.stamp .src.log{background:#16361f;color:#5fcf80}.stamp .src.source{background:#382f15;color:#e0b24a}
.tctl{display:flex;align-items:center;gap:8px;margin:8px 0 4px;flex-wrap:wrap}
.tctl select{background:#232427;color:#e6e6e6;border:1px solid #3a3c41;border-radius:4px;
 padding:3px 7px;font-size:12px}
.pbtn{background:#232427;color:#cdd;border:1px solid #3a3c41;border-radius:4px;padding:3px 11px;
 font-size:12px;cursor:pointer}
.pbtn:hover:not(:disabled){background:#2f3136}.pbtn:disabled{opacity:.4;cursor:default}
.pinfo{color:#8a8f98;min-width:120px;text-align:center}
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

// ---- generic table enhancer -------------------------------------------------------------
// Any <table class="ptable"> gets a control bar: a Country <select> (when the table has a
// country dimension) + Back/Next paginator (10 rows/page) over the FILTERED rows.
// Country columns: declared via data-cfilter="0,2" (OR-match across those col indices), else
// auto-detected from a header cell literally named "Country". Tiny tables with neither a
// country column nor >10 rows are left untouched.
function _rowsOf(t){
 var head=null, body, all=Array.prototype.slice.call(t.rows);
 if(t.tBodies.length && t.tBodies[0].rows.length){
  body=Array.prototype.slice.call(t.tBodies[0].rows);
  head=(t.tHead&&t.tHead.rows.length)?t.tHead.rows[0]:all[0];
 } else { head=all[0]; body=all.slice(1); }
 return {head:head, body:body};
}
function enhanceTable(t){
 var rb=_rowsOf(t), head=rb.head, body=rb.body;
 if(!body.length) return;
 var cols=[], cf=t.getAttribute('data-cfilter');
 if(cf){ cols=cf.split(',').map(function(x){return parseInt(x,10);}); }
 else if(head){ Array.prototype.slice.call(head.cells).forEach(function(c,i){
   if(c.textContent.trim().toLowerCase()==='country') cols.push(i); }); }
 var per=10, page=0, filter='';
 if(!cols.length && body.length<=per) return;   // nothing to filter, nothing to page
 var bar=document.createElement('div'); bar.className='tctl';
 if(cols.length){
  var vals={};
  body.forEach(function(r){ cols.forEach(function(ci){
    var cell=r.cells[ci]; if(cell){var v=cell.textContent.trim(); if(v)vals[v]=1;} }); });
  var keys=Object.keys(vals).sort();
  var sel=document.createElement('select');
  sel.innerHTML='<option value="">All countries ('+keys.length+')</option>'
   +keys.map(function(v){return '<option>'+v.replace(/&/g,'&amp;').replace(/</g,'&lt;')+'</option>';}).join('');
  sel.onchange=function(){filter=sel.value; page=0; draw();};
  var lab=document.createElement('span'); lab.className='small'; lab.textContent='Country:';
  bar.appendChild(lab); bar.appendChild(sel);
 }
 var prev=document.createElement('button'); prev.className='pbtn'; prev.innerHTML='&#9664; Back';
 var info=document.createElement('span'); info.className='pinfo small';
 var next=document.createElement('button'); next.className='pbtn'; next.innerHTML='Next &#9654;';
 prev.onclick=function(){page--; draw();}; next.onclick=function(){page++; draw();};
 bar.appendChild(prev); bar.appendChild(info); bar.appendChild(next);
 t.parentNode.insertBefore(bar,t);
 function draw(){
  var vis=body.filter(function(r){ if(!filter) return true;
    return cols.some(function(ci){var c=r.cells[ci]; return c && c.textContent.trim()===filter;}); });
  var maxp=Math.max(0,Math.ceil(vis.length/per)-1);
  if(page>maxp)page=maxp; if(page<0)page=0;
  body.forEach(function(r){r.style.display='none';});
  vis.slice(page*per,page*per+per).forEach(function(r){r.style.display='';});
  info.textContent=' '+(vis.length?page+1:0)+'/'+(maxp+1)+' ('+vis.length+' rows) ';
  prev.disabled=(page<=0); next.disabled=(page>=maxp);
 }
 draw();
}
function enhanceTables(){
 Array.prototype.slice.call(document.querySelectorAll('table.ptable')).forEach(enhanceTable);
}
document.addEventListener('DOMContentLoaded',enhanceTables);
"""


def esc(s):
    return html.escape(str(s))


def md_block(text):
    """Compact markdown -> HTML for observe.md: small font, tight lists, real <table>s
    (markdown pipe tables render as styled <table class='obs'>, never raw '| - |' text)."""
    out, in_list, tbl = [], False, []

    def inline(s):
        s = esc(s)
        s = re.sub(r"_(.+?)_", r"<em class='muted'>\1</em>", s)
        return re.sub(r"`(.+?)`", r"<code>\1</code>", s)

    def close():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    def flush_tbl():
        nonlocal tbl
        if not tbl:
            return
        head, body = tbl[0], tbl[1:]
        out.append("<table class='obs'><tr>"
                   + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr>")
        for r in body:
            out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
        out.append("</table>")
        tbl = []

    for raw in text.splitlines():
        ln = raw.strip()
        if ln.startswith("|"):                        # markdown table row
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):     # separator row (|---|---|) -> skip
                continue
            close()
            tbl.append(cells)
            continue
        flush_tbl()
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
    flush_tbl()
    close()
    return "\n".join(out)


VTEST_RX = re.compile(r"VTEST_BUILD\s+(.+?)\s*$")


def read_build_stamp(logs_dir):
    """The loaded-build label for the report header.
    Primary: the versiontest popup writes `VTEST_BUILD <stamp>` to debug.log -> this is the
    bundle that ACTUALLY loaded this run. Fallback: the source stamp in the versiontest loc
    file (may be ahead of what loaded). Returns (stamp, source) where source in {log,source}."""
    path = os.path.join(logs_dir, "debug.log") if logs_dir else None
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            for ln in f:
                m = VTEST_RX.search(ln)
                if m:
                    return m.group(1).strip(), "log"
    loc = os.path.join(os.path.dirname(__file__), "..", "..", "..", "mod1", "versiontestMod",
                       "localization", "english", "versiontest_l_english.yml")
    try:
        with open(loc, encoding="utf-8-sig", errors="replace") as f:
            for ln in f:
                m = re.search(r'versiontest\.1\.d:0\s*"(.+?)"', ln)
                if m:
                    return m.group(1).strip(), "source"
    except OSError:
        pass
    return None, None


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
        h.append("<table class='ptable'><tr><th>File</th><th>Encoding</th><th>Braces</th>"
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
            h.append("<table class='ptable'><tr><th>Country</th><th>Building</th><th>Type</th>"
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
                h.append("<table class='ptable'><tr>" + "".join(f"<th>{esc(c)}</th>" for c in t["columns"]) + "</tr>")
                for row in t["rows"]:
                    h.append("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in row) + "</tr>")
                h.append("</table>")
            else:
                h.append("<p class='muted small'>no rows logged (mod didn't emit this table "
                         "— check it ran / re-run the game)</p>")
        real = [e for e in d["errors"] if not e["benign"]]
        ben = [e for e in d["errors"] if e["benign"]]
        egroups = d.get("error_groups", [])
        if real:
            h.append(f"<p class='bad'>Real errors <span class='pill warn'>{len(real)}</span> "
                     f"<span class='small'>in {len(egroups)} files</span></p>")
            # COMPACT: collapsible per source file (same shape as the non-mod section)
            for g in egroups:
                h.append(f"<details><summary><code>{esc(g['file'])}</code> "
                         f"<span class='pill warn'>{g['count']}</span></summary>")
                for t in g["entries"]:
                    h.append(f"<pre class='note'>{esc(t)}</pre>")
                h.append("</details>")
        else:
            h.append("<p class='ok'>No real errors referencing this mod.</p>")
        if ben:
            h.append(f"<details><summary>{len(ben)} benign note(s)</summary>")
            for e in ben:
                h.append(f"<pre class='note'>{esc(e['text'])}</pre>")
            h.append("</details>")
        h.append("</div>")
    # SUSPECT-MOD: engine errors actually caused by our create_building seeding (capacity/backing)
    suspect = logdata.get("suspect_mod", [])
    if suspect:
        nhist = sum(1 for s in suspect if isinstance(s, dict) and "state.cpp" in s.get("source", ""))
        h.append(f"<div class='mod'><h2 class='bad'>⚠ Likely OURS — bad create_building "
                 f"<span class='pill bad'>{len(suspect)}</span> "
                 f"<span class='small'>({nhist} = wrong HISTORY entry)</span></h2>")
        h.append("<p class='small'>Engine reduced/rejected a <b>create_building</b> we issued. "
                 "<b>state.cpp</b> = a <b>history</b> file entry is wrong for that state (no can_construct "
                 "gate at load — fix/remove the entry). <b>building_manager.cpp</b> = runtime over-build. "
                 "<b>backing</b> = building can't exist there at all.</p>")
        h.append("<table class='ptable'><tr><th>State</th><th>Building</th><th>Can support</th><th>Source / fix</th></tr>")
        for s in suspect:
            if isinstance(s, dict):
                h.append(f"<tr><td>{esc(s['state'])}</td><td>{esc(s['building'])}</td>"
                         f"<td>{esc(str(s['supports']))}</td><td class='small'>{esc(s['source'])}</td></tr>")
            else:  # backward-compat (plain string)
                h.append(f"<tr><td colspan='4'><pre class='note'>{esc(s)}</pre></td></tr>")
        h.append("</table></div>")

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


def bdd_tab(mods_human, build_stamp=None):
    h = []
    stamp, src = build_stamp or (None, None)
    for mod, observe, bdd in mods_human:
        slabel = ""
        if stamp:
            tag = "loaded build" if src == "log" else "source stamp (not confirmed in log)"
            slabel = (f"<span class='stamp'>— <b>{esc(stamp)}</b>"
                      f"<span class='src {src}'>{tag}</span></span>")
        h.append(f"<div class='mod'><h2>{esc(mod)}{slabel}</h2>")
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
            h.append("<table class='ptable'><tr><th>#</th><th>Question</th><th>Exp</th><th>Answer</th>"
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


def conflict_tab(conflictdata):
    h = ["<div class='mod'><h2>Mod file conflicts "
         f"<span class='pill {'ok' if conflictdata['summary']['ok'] else 'bad'}'>"
         f"{conflictdata['summary']['hard']} hard</span> "
         f"<span class='pill warn'>{conflictdata['summary']['soft']} soft</span></h2>"]
    h.append("<p class='small'>Across mods: "
             f"<code>{esc(', '.join(conflictdata['mods']))}</code>. "
             "HARD = same relative path in 2+ mods (later load-order silently OVERRIDES the "
             "earlier). SOFT = same filename at different paths (advisory). "
             "<i>Scaffold: deeper same-object-NAME checks (event ids / scripted effects / "
             "modifiers) are a TODO.</i></p>")
    if conflictdata["hard"]:
        h.append("<p class='bad'>Hard conflicts (real overrides):</p><table class='ptable'>"
                 "<tr><th>Relative path</th><th>Mods</th></tr>")
        for c in conflictdata["hard"]:
            h.append(f"<tr><td><code>{esc(c['relpath'])}</code></td>"
                     f"<td>{esc(', '.join(c['mods']))}</td></tr>")
        h.append("</table>")
    else:
        h.append("<p class='ok'>No hard path collisions across mods.</p>")
    if conflictdata["soft"]:
        h.append("<details><summary class='small'>"
                 f"{len(conflictdata['soft'])} soft (same filename, different folders)</summary>"
                 "<table class='ptable'><tr><th>Filename</th><th>Occurrences</th></tr>")
        for c in conflictdata["soft"]:
            h.append(f"<tr><td><code>{esc(c['basename'])}</code></td>"
                     f"<td class='small'>{esc(', '.join(c['occurrences']))}</td></tr>")
        h.append("</table></details>")
    h.append("</div>")
    return "\n".join(h)


def timeline_tab(tl):
    yrs = tl.get("years") or []
    wars = tl.get("wars", [])
    dcounts = tl.get("diplo_counts", [])
    eco = tl.get("eco", [])
    h = [f"<div class='mod' id='tlpanel'><h2>Timeline "
         f"<span class='pill'>{len(wars)} wars</span> "
         f"<span class='pill'>{sum(r['count'] for r in eco)} eco builds</span></h2>"]
    h.append("<p class='small'>Per game-year (carried from vanilla date lines). Each table below "
             "has its own country filter + 10-rows/page paginator. DIPLO = runtime blob-chain wars "
             "+ annexations (day-1 curated wars live in history with no marker, so they're not here). "
             "ECO = every placement (day-1 seeds + yearly pulse), binned into its year.</p>")
    if not yrs and not eco:
        h.append("<p class='muted'>No timeline events parsed (run the game with debug_log ON).</p></div>")
        return "\n".join(h)

    # ---- ECO BUILDS: flat table, Country=col1 -------------------------------------------
    h.append("<h3 style='margin:14px 0 4px'>Eco buildings placed "
             f"<span class='pill'>{sum(r['count'] for r in eco)}</span></h3>")
    if eco:
        h.append("<table class='ptable' data-cfilter='1'><thead><tr><th>Year</th><th>Country</th>"
                 "<th>State</th><th>Building</th><th>Type</th><th>Levels</th></tr></thead><tbody>")
        for r in sorted(eco, key=lambda r: (r["year"] or 0, r["country"] or "", r["building"] or "")):
            h.append(f"<tr><td>{r['year'] or '?'}</td><td>{esc(r['country'] or '?')}</td>"
                     f"<td>{esc(r.get('state') or '?')}</td>"
                     f"<td>{esc(r['building'] or '?')}</td><td>{esc(r['type'])}</td>"
                     f"<td>{r['count']}</td></tr>")
        h.append("</tbody></table>")
    else:
        h.append("<p class='muted small'>no eco placements logged.</p>")

    # ---- WARS: flat table, Attacker=col1 + Target=col2 feed the filter ------------------
    h.append(f"<h3 style='margin:18px 0 4px'>Wars started <span class='pill'>{len(wars)}</span></h3>")
    if wars:
        h.append("<table class='ptable' data-cfilter='1,2'><thead><tr><th>Year</th><th>Attacker</th>"
                 "<th>Target</th></tr></thead><tbody>")
        for w in sorted(wars, key=lambda w: (w["year"] or 0, w["attacker"] or "")):
            h.append(f"<tr><td>{w['year'] or '?'}</td><td>{esc(w['attacker'])}</td>"
                     f"<td>{esc(w['target'])}</td></tr>")
        h.append("</tbody></table>")
    else:
        h.append("<p class='muted small'>no runtime wars logged.</p>")

    # ---- DIPLO grants: flat table, Country=col1 -----------------------------------------
    if dcounts:
        h.append("<h3 style='margin:18px 0 4px'>Claims / homelands / pops granted</h3>")
        h.append("<table class='ptable' data-cfilter='1'><thead><tr><th>Year</th><th>Country</th>"
                 "<th>Claims</th><th>Homelands</th><th>Pops</th></tr></thead><tbody>")
        for r in sorted(dcounts, key=lambda r: (r["year"] or 0, r["country"] or "")):
            h.append(f"<tr><td>{r['year'] or '?'}</td><td>{esc(r['country'])}</td>"
                     f"<td>{r['claims']}</td><td>{r['homelands']}</td><td>{r['pops']}</td></tr>")
        h.append("</tbody></table>")
    h.append("</div>")
    return "\n".join(h)


def render(branch, mods_static, logdata, mods_human, out_path, conflictdata=None,
           timelinedata=None, build_stamp=None):
    conflictdata = conflictdata or {"mods": [], "hard": [], "soft": [],
                                    "summary": {"hard": 0, "soft": 0, "ok": True}}
    timelinedata = timelinedata or {"years": [], "countries": [], "wars": [], "diplo_counts": [],
                                    "eco": [], "summary": {"wars": 0, "eco_placements": 0}}
    # summary badges
    sfail = sum(s["summary"]["failed"] for _, s in mods_static)
    lreal = logdata["summary"]["mod_real_errors"]
    bP, bF, bNA = bdd_stats(mods_human)
    def badge(ok, label, cls=None):
        return f"<span class='pill {cls or ('ok' if ok else 'bad')}'>{label}</span>"
    bdd_cls = "ok" if (bF == 0 and bNA == 0) else ("bad" if bF else "warn")
    chard = conflictdata["summary"]["hard"]
    head = (f"<h1>Vic3 test report — <code>{esc(branch)}</code></h1>"
            f"<div class='sub'>generated {datetime.datetime.now().isoformat(timespec='seconds')} "
            f"&nbsp; {badge(sfail==0,f'static: {sfail} fail')} "
            f"{badge(lreal==0,f'log: {lreal} mod errors')} "
            f"{badge(None,f'bdd: {bP} PASS | {bF} FAIL | {bNA} NA', bdd_cls)} "
            f"{badge(chard==0,f'conflicts: {chard} hard')} "
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
 <div class="tab" onclick="show(3)">Conflicts</div>
 <div class="tab" onclick="show(4)">Timeline</div>
</div>
<div class="panel active">{static_tab(mods_static)}</div>
<div class="panel">{log_tab(mods_static, logdata)}</div>
<div class="panel">{bdd_tab(mods_human, build_stamp)}</div>
<div class="panel">{conflict_tab(conflictdata)}</div>
<div class="panel">{timeline_tab(timelinedata)}</div>
<div id="toTop" onclick="toTop()">↑ Top</div>
<script>{JS}</script></body></html>"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    return out_path
