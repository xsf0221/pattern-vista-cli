"""Tiny dependency-free renderers: JSON (agent default) and ASCII tables (humans)."""

import json
from typing import Any, Dict, List, Sequence


def as_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def table(rows: Sequence[Dict[str, Any]], columns: List[str], headers: List[str]) -> str:
    """Render an ASCII table for the given columns. Empty rows → a hint line."""
    if not rows:
        return "(no rows)"
    cells = [[_fmt(r.get(c)) for c in columns] for r in rows]
    widths = [
        max(len(headers[i]), *(len(row[i]) for row in cells)) for i in range(len(columns))
    ]
    sep = "  "
    out = [sep.join(h.ljust(widths[i]) for i, h in enumerate(headers))]
    out.append(sep.join("-" * widths[i] for i in range(len(columns))))
    for row in cells:
        out.append(sep.join(row[i].ljust(widths[i]) for i in range(len(columns))))
    return "\n".join(out)


def pct(v: Any) -> str:
    """Format a fractional deviation (0.183) as a signed percent (+18.30%)."""
    if v is None:
        return "—"
    f = float(v) * 100
    return f"{f:+.2f}%"
