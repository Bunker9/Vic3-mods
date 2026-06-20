#!/usr/bin/env python3
"""
v2 testbook — shared helpers for all feature extract scripts.

Every feature's extract.py calls:
    write_component(out_dir, mod, feature_id, tab, title, order, html, summary)
    write_data(out_dir, filename, data)

CSS / JS are inlined by run_v2.py into the assembled main.html.
"""
import os, json
import html as _html

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
V2DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../v2
TBDIR  = os.path.dirname(V2DIR)                                         # .../testbook
MOD1   = os.path.normpath(os.path.join(V2DIR, "..", "..", "mod1"))
OLD_CHECKS = os.path.join(TBDIR, "testkit", "checks")

# ---------------------------------------------------------------------------
# CSS  (dark theme — shared across all assembled HTML)
# ---------------------------------------------------------------------------
CSS = """
body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#1e1f22;color:#e6e6e6}
header{padding:12px 22px 6px;background:#2b2d31;border-bottom:1px solid #444}
h1{margin:0;font-size:17px}
.hdr-sub{color:#9aa;font-size:11px;margin-top:3px}
/* dashboard */
.dashboard{background:#252729;border-bottom:1px solid #3a3c41;padding:6px 22px}
.dash-row{display:flex;align-items:center;gap:6px;padding:3px 0;font-size:12px;
  border-bottom:1px solid #2e3035;flex-wrap:wrap}
.dash-row:last-child{border-bottom:none}
.dash-mod{font-weight:600;color:#cdd;min-width:190px;white-space:nowrap}
.dash-stats{display:flex;gap:4px;flex-wrap:wrap}
/* nav bar */
.nav-bar{display:flex;align-items:center;gap:10px;padding:6px 22px 0;
  background:#2b2d31;border-bottom:1px solid #444;flex-wrap:wrap}
.nav-bar select{background:#232427;color:#e6e6e6;border:1px solid #3a3c41;
  border-radius:4px;padding:3px 8px;font-size:12px}
.tabs{display:flex;gap:3px}
.tab{padding:6px 16px;cursor:pointer;border:1px solid #444;border-bottom:none;
  border-radius:6px 6px 0 0;background:#232427;color:#bbb;font-size:13px}
.tab.active{background:#1e1f22;color:#fff;font-weight:600}
/* panels */
.panel{display:none;padding:14px 22px}.panel.active{display:block}
/* cards (one per rendered unit: a mod-wide view or a feature) */
.card{margin:0 0 18px;border:1px solid #3a3c41;border-radius:8px;overflow:hidden}
.card>h2{margin:0;padding:8px 14px;background:#26282c;font-size:14px}
.card>h2 .mod-tag{font-size:11px;color:#9aa;font-weight:400;margin-left:8px}
.card>h2 .hpill{margin-left:8px}
.card details>summary{padding:4px 0}
.card.stub{opacity:.72}
.card.stub>h2{background:#222}
.card .stub-body{padding:8px 14px;font-size:12px;color:#9aa}
.card .stub-body .mk{color:#cdd}
/* tables */
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border:1px solid #3a3c41;padding:5px 8px;text-align:left;vertical-align:top}
th{background:#26282c}
td.c{text-align:center;width:70px}
/* status colours */
.ok{color:#5fcf80;font-weight:600}.bad{color:#ff6b6b;font-weight:600}.warn{color:#e0b24a}
.muted{color:#8a8f98}
/* pills / badges */
.pill{padding:2px 7px;border-radius:10px;font-size:11px;white-space:nowrap}
.pill.ok{background:#16361f;color:#5fcf80}.pill.bad{background:#3a1a1a;color:#ff6b6b}
.pill.warn{background:#382f15;color:#e0b24a}.pill.grey{background:#2a2c31;color:#9aa}
/* misc */
pre.note{white-space:pre-wrap;background:#232427;border:1px solid #3a3c41;border-radius:5px;
  padding:8px;font-size:12px;color:#cdd;margin:4px 0}
details>summary{cursor:pointer;color:#9aa;font-size:12px}
code{background:#2b2d31;padding:1px 4px;border-radius:3px;font-size:11px}
.small{font-size:11px;color:#8a8f98}
.ptable{width:100%}
/* table controls */
.tctl{display:flex;align-items:center;gap:6px;margin:6px 0 3px;flex-wrap:wrap}
.tctl select{background:#232427;color:#e6e6e6;border:1px solid #3a3c41;
  border-radius:4px;padding:3px 6px;font-size:11px}
.pbtn{background:#232427;color:#cdd;border:1px solid #3a3c41;border-radius:4px;
  padding:2px 9px;font-size:11px;cursor:pointer}
.pbtn:hover:not(:disabled){background:#2f3136}.pbtn:disabled{opacity:.4;cursor:default}
.pinfo{color:#8a8f98;min-width:100px;text-align:center;font-size:11px}
/* scroll to top */
#toTop{position:fixed;right:16px;bottom:16px;padding:7px 12px;border-radius:18px;
  background:#3a6df0;color:#fff;font-size:11px;cursor:pointer;opacity:.85;z-index:50}
"""

# ---------------------------------------------------------------------------
# JS  (tab switch + mod filter + table paginator)
# ---------------------------------------------------------------------------
JS = """
// --- tab switching ---
function showTab(id){
  document.querySelectorAll('.tab').forEach(function(t){t.classList.toggle('active',t.dataset.tab===id);});
  document.querySelectorAll('.panel').forEach(function(p){p.classList.toggle('active',p.dataset.tab===id);});
}

// --- mod filter ---
document.addEventListener('DOMContentLoaded',function(){
  var sel=document.getElementById('mod-filter');
  if(sel) sel.onchange=function(){
    var v=this.value;
    document.querySelectorAll('.card').forEach(function(el){
      el.style.display=(!v||el.dataset.mod===v)?'':'none';
    });
  };

  // --- generic table paginator + country filter ---
  function _rows(t){
    var all=Array.prototype.slice.call(t.rows);
    if(t.tBodies&&t.tBodies[0]){
      var b=Array.prototype.slice.call(t.tBodies[0].rows);
      var h=(t.tHead&&t.tHead.rows.length)?t.tHead.rows[0]:all[0];
      return {head:h,body:b};
    }
    return {head:all[0],body:all.slice(1)};
  }
  function enhanceTable(t){
    var rb=_rows(t),head=rb.head,body=rb.body;
    if(!body.length)return;
    var cols=[],cf=t.getAttribute('data-cfilter');
    if(cf){cols=cf.split(',').map(function(x){return parseInt(x,10);});}
    else if(head){Array.prototype.slice.call(head.cells).forEach(function(c,i){
      if(c.textContent.trim().toLowerCase()==='country')cols.push(i);});}
    var per=10,page=0,filter='';
    if(!cols.length&&body.length<=per)return;
    var bar=document.createElement('div');bar.className='tctl';
    if(cols.length){
      var vals={};
      body.forEach(function(r){cols.forEach(function(ci){
        var c=r.cells[ci];if(c){var v=c.textContent.trim();if(v)vals[v]=1;}});});
      var keys=Object.keys(vals).sort();
      var s=document.createElement('select');
      s.innerHTML='<option value="">All ('+keys.length+')</option>'
        +keys.map(function(v){return '<option>'+v+'</option>';}).join('');
      s.onchange=function(){filter=s.value;page=0;draw();};
      var lab=document.createElement('span');lab.className='small';lab.textContent='Country:';
      bar.appendChild(lab);bar.appendChild(s);
    }
    var prev=document.createElement('button');prev.className='pbtn';prev.innerHTML='&#9664;';
    var info=document.createElement('span');info.className='pinfo';
    var next=document.createElement('button');next.className='pbtn';next.innerHTML='&#9654;';
    prev.onclick=function(){page--;draw();};next.onclick=function(){page++;draw();};
    bar.appendChild(prev);bar.appendChild(info);bar.appendChild(next);
    t.parentNode.insertBefore(bar,t);
    function draw(){
      var vis=body.filter(function(r){
        if(!filter)return true;
        return cols.some(function(ci){var c=r.cells[ci];return c&&c.textContent.trim()===filter;});
      });
      var maxp=Math.max(0,Math.ceil(vis.length/per)-1);
      if(page>maxp)page=maxp;if(page<0)page=0;
      body.forEach(function(r){r.style.display='none';});
      vis.slice(page*per,page*per+per).forEach(function(r){r.style.display='';});
      info.textContent=' '+(vis.length?page+1:0)+'/'+(maxp+1)+' ('+vis.length+') ';
      prev.disabled=(page<=0);next.disabled=(page>=maxp);
    }
    draw();
  }
  document.querySelectorAll('table.ptable').forEach(enhanceTable);
});
function toTop(){window.scrollTo({top:0,behavior:'smooth'});}
"""

# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------
def esc(s):
    return _html.escape(str(s))


def badge(cls, label):
    return f"<span class='pill {cls}'>{esc(label)}</span>"


def tbl(columns, rows, cfilter=None):
    """Build a paginated ptable HTML string."""
    cf = f" data-cfilter='{cfilter}'" if cfilter is not None else ""
    h = [f"<table class='ptable'{cf}><thead><tr>"]
    h += [f"<th>{esc(c)}</th>" for c in columns]
    h.append("</tr></thead><tbody>")
    for row in rows:
        cells = []
        for v in row:
            cls = ""
            if isinstance(v, tuple):          # (value, css_class) for coloured cells
                v, cls = v
            cells.append(f"<td class='{cls} c'>{esc(v)}</td>" if cls else f"<td>{esc(v)}</td>")
        h.append("<tr>" + "".join(cells) + "</tr>")
    h.append("</tbody></table>")
    return "\n".join(h)


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------
TBCOMP_TMPL = '<!-- TBCOMP mod="{mod}" tab="{tab}" feature="{fid}" title="{title}" order="{order}" -->'


def write_component(out_dir, mod, feature_id, tab, title, order, html_content, summary=None):
    """Write component.html with TBCOMP identification marker."""
    os.makedirs(out_dir, exist_ok=True)
    marker = TBCOMP_TMPL.format(mod=mod, tab=tab, fid=feature_id, title=title, order=order)
    content = f"{marker}\n<div class='feature-content'>\n{html_content}\n</div>\n"
    with open(os.path.join(out_dir, "component.html"), "w", encoding="utf-8") as f:
        f.write(content)
    if summary is not None:
        write_data(out_dir, "summary.json", summary)


def write_data(out_dir, filename, data):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def read_data(out_dir, filename):
    p = os.path.join(out_dir, filename)
    return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else None


def mod_name_from_feature_dir(feature_dir):
    """Mod name = the first path component under v2/. Works for any depth:
    v2/<Mod>/<FEATURE-ID>/ (a feature) and v2/<Mod>/_modwide/<view>/ (a mod-wide view)."""
    rel = os.path.relpath(os.path.abspath(feature_dir), V2DIR)
    return rel.split(os.sep)[0]


def stub_card_body(feat):
    """Body for a declared-but-unimplemented feature (xlsx-driven coverage placeholder)."""
    mk = esc(feat.get("markers") or "—")
    st = esc(feat.get("status") or "—")
    return (f"<div class='stub-body'>extractor pending &nbsp;·&nbsp; status: {st}"
            f"<br>markers: <span class='mk'>{mk}</span></div>")


def xtable(col_labels, row_labels, cell_fn):
    """Minimal cross-tab (xtab): rows x columns grid. cell_fn(r, c) -> value or (value, css).
    A reusable component for feature aggregators that compare two dimensions."""
    h = ["<table class='ptable xtab'><thead><tr><th></th>"]
    h += [f"<th>{esc(c)}</th>" for c in col_labels]
    h.append("</tr></thead><tbody>")
    for r in row_labels:
        h.append(f"<tr><th>{esc(r)}</th>")
        for c in col_labels:
            v = cell_fn(r, c)
            cls = ""
            if isinstance(v, tuple):
                v, cls = v
            h.append(f"<td class='{cls} c'>{esc(v)}</td>" if cls else f"<td class='c'>{esc(v)}</td>")
        h.append("</tr>")
    h.append("</tbody></table>")
    return "\n".join(h)
