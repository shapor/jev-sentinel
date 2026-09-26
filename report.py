"""Session audit report: every action an agent took, its verdict and stage, and how far the session drifted from its task."""

import collections
import html
import json
import os
import pathlib
import time

LIVE = pathlib.Path(os.environ.get("SENTINEL_LIVE", pathlib.Path(__file__).with_name("results") / "live.jsonl"))


def rows():
    return [json.loads(l) for l in LIVE.open()] if LIVE.exists() else []


def by_session():
    out = collections.defaultdict(list)
    for r in rows():
        out[r.get("session", "manual")].append(r)
    return out


def task(rs):
    for r in reversed(rs):
        for k in ("task", "scope"):
            if isinstance(r.get(k), str):
                return r[k]
    return ""


def sessions():
    return [{"session": s, "scope": task(rs), "first": rs[0]["t"], "last": rs[-1]["t"],
             "actions": len(rs), "verdicts": dict(collections.Counter(r["verdict"] for r in rs))}
            for s, rs in by_session().items()]


def drift(rs):
    """Per-action scope score from Jev: 0 = on task, 4 = clearly outside it."""
    return [r["scope"] for r in rs if isinstance(r.get("scope"), (int, float))]


def sparkline(values, w=900, h=120):
    if not values:
        return ""
    step = w / max(len(values) - 1, 1)
    pts = " ".join(f"{i * step:.1f},{h - h * v / 4:.1f}" for i, v in enumerate(values))
    return (f'<svg viewBox="0 0 {w} {h + 4}" width="100%"><line x1="0" y1="{h / 2}" x2="{w}" y2="{h / 2}" '
            f'stroke="#30363d" stroke-dasharray="4"/><polyline points="{pts}" fill="none" stroke="#58a6ff" '
            f'stroke-width="3"/></svg>')


CSS = """body{font:17px/1.5 system-ui,sans-serif;background:#0d1117;color:#e6edf3;max-width:1100px;margin:auto;padding:32px 24px}
h1{margin:0}.dim{color:#8b949e}table{width:100%;border-collapse:collapse;margin-top:18px}
td,th{padding:8px 10px;border-bottom:1px solid #21262d;text-align:left;vertical-align:top}th{color:#8b949e;font-size:13px;text-transform:uppercase}
code{font:13px ui-monospace,monospace;color:#8b949e;white-space:pre-wrap;word-break:break-all}
.v{font-weight:800;border-radius:6px;padding:2px 8px;font-size:13px}.allow{background:#12361f;color:#3fb950}
.ask{background:#3d2e0a;color:#d29922}.block{background:#42161a;color:#f85149}
.tiles{display:flex;gap:14px;margin:18px 0}.tiles div{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:14px 18px}
.tiles b{display:block;font-size:30px}"""


def render(session_id):
    rs = by_session().get(session_id, [])
    e = html.escape
    c = collections.Counter(r["verdict"] for r in rs)
    body = "".join(
        f'<tr><td class="dim">{time.strftime("%H:%M:%S", time.localtime(r["t"]))}</td>'
        f'<td><span class="v {e(r["verdict"])}">{e(r["verdict"].upper())}</span></td>'
        f'<td>{e(r.get("reason", ""))}<br><span class="dim">{e(str(r.get("stage", "")))}</span></td>'
        f'<td>{r.get("p_block", "")}</td><td class="dim">{e(str(r.get("tool") or ""))}</td>'
        f'<td><code>{e(r.get("action", "")[:160])}</code></td></tr>' for r in rs)
    page = (f'<!doctype html><meta charset="utf-8"><title>Session report</title><style>{CSS}</style>'
            f'<h1>Session report</h1><div class="dim">{e(session_id)}</div>'
            f'<p><b>Task:</b> {e(task(rs))}</p>'
            f'<div class="tiles"><div><b>{len(rs)}</b>actions</div><div><b>{c["allow"]}</b>allowed</div>'
            f'<div><b>{c["ask"]}</b>sent to a human</div><div><b>{c["block"]}</b>blocked</div></div>'
            f'<h3>Drift from the task</h3><div class="dim">0 = on task, 4 = clearly outside it '
            f'(dashed line = halfway)</div>{sparkline(drift(rs))}'
            f'<table><tr><th>time</th><th>verdict</th><th>why / stage</th><th>p_block</th><th>tool</th><th>action</th></tr>{body}</table>')
    return page.encode()


if __name__ == "__main__":
    import sys
    s = sys.argv[1] if len(sys.argv) > 1 else (sessions() or [{"session": ""}])[-1]["session"]
    sys.stdout.buffer.write(render(s))
