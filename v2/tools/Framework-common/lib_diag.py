#!/usr/bin/env python3
"""lib_diag — the diagnostics engine's importable core: a SAFE `condition` evaluator (no eval()), the
'which literals fire' selector, and the markdown renderer. DATA-DRIVEN — every human string comes from the
diag_literals CSV, none from code. Imported by ext-diag-eval / gen-diag-md / run-log-diag + chk-diagnostics."""
import re

_OPS = {"==": lambda a, b: a == b, "!=": lambda a, b: a != b, ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, "<": lambda a, b: a < b}
_COND = re.compile(r"^\s*([A-Za-z_]\w*)\s*(==|!=|>=|<=|>|<)\s*(.+?)\s*$")


def _num(v, metrics):
    if isinstance(v, str) and v in metrics:      # right side may name another metric
        v = metrics[v]
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def evaluate(condition, metrics):
    """True/False for a single `metric OP value` condition over a metrics dict. SAFE (no eval). A condition
    naming an unknown metric returns False (a rule whose inputs are absent does not fire)."""
    m = _COND.match(condition or "")
    if not m:
        return False
    left, op, right = m.group(1), m.group(2), m.group(3).strip()
    if left not in metrics:
        return False
    return bool(_OPS[op](_num(metrics[left], metrics), _num(right, metrics)))


def fired(metrics, literals):
    """literals = list[dict] (id,text,condition,logical_reasoning,user_comments,status). Return rows whose
    status != 'ignore' AND whose condition evaluates True over metrics."""
    return [r for r in literals
            if (r.get("status", "").strip().lower() != "ignore")
            and evaluate(r.get("condition", ""), metrics)]


def render_md(title, metrics, fired_rows):
    """Render diagnostics.md — ALL prose from the CSV rows; code only structures it."""
    md = [f"# Diagnostics — {title}", "", "| metric | value |", "|---|---|"]
    md += [f"| {k} | {metrics[k]} |" for k in sorted(metrics)]
    md.append("\n## Findings\n")
    if not fired_rows:
        md.append("_No diagnostic rule fired._")
    for r in fired_rows:
        md.append(f"- **[{r.get('id','')}] {r.get('text','')}**")
        if r.get("logical_reasoning"):
            md.append(f"  - {r['logical_reasoning']}")
    return "\n".join(md) + "\n"
