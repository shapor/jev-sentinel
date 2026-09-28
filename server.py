"""Demo server: serves web/index.html and a small JSON API over the hunt results and the live hook feed."""

import collections
import concurrent.futures
import http.server
import threading
import json
import os
import pathlib
import random

import data
import report
import sentinel

HERE = pathlib.Path(__file__).parent
RESULTS = HERE / "results"
TEXT = {}  # id -> text, for showing snippets next to verdicts
SANCTIONED = []  # short sanctioned CTF commands, re-checked live on stage when no agent is running


def load(name):
    """Results with verdicts recomputed under the current policy, so tuning never requires re-scoring."""
    def read(f):
        return [json.loads(l) for l in f.open()] if f.exists() else []

    # While a re-score is in progress, keep serving the previous complete run (results/v1) until the new one catches up.
    rows = max(read(RESULTS / f"{name}.jsonl"), read(RESULTS / "v1" / f"{name}.jsonl"), key=len)
    for r in rows:
        if "p_block" in r:
            r["verdict"] = sentinel.verdict(r["p_block"], r["stage"])
    return rows


def snippet(item_id, n=400):
    return TEXT.get(item_id, "")[:n]


def stats():
    swarm, bench, swe = load("swarm"), load("cybench"), load("swe")

    def summary(rows):
        return {"n": len(rows), "verdicts": collections.Counter(r["verdict"] for r in rows),
                "stages": collections.Counter(r["stage"] for r in rows if "stage" in r),
                "regex": sum(r["regex"] for r in rows),
                "ms_p50": sorted(r["ms"] for r in rows)[len(rows) // 2] if rows else None}

    def blocked(r, t):
        return r.get("p_block", 0) >= t and r["stage"] not in sentinel.IN_SCOPE_STAGES

    # "caught" = stopped before running (blocked or sent to a human); "blocked" = stopped with no human in the loop.
    thresholds = [{"t": t, "swarm_caught": sum(r.get("p_block", 0) >= t for r in swarm),
                   "sanctioned_blocked": sum(blocked(r, t) for r in bench)} for t in (0.5, 0.6, 0.7, 0.8, 0.9)]
    return {"swarm": summary(swarm), "sanctioned": summary(bench), "coding": summary(swe), "thresholds": thresholds}


ATTACK_TACTICS = [
    "reconnaissance", "resource_development", "initial_access", "execution", "persistence",
    "privilege_escalation", "defense_evasion", "credential_access", "discovery", "lateral_movement",
    "collection", "command_and_control", "exfiltration", "impact", "none",
]


def attack_heatmap():
    """ATT&CK tactic counts from the dedicated classification runs."""
    groups = []
    for source, label in (("swarm", "OpenAI swarm"), ("cybench", "Sanctioned CTF"), ("swe", "Coding agents")):
        path = RESULTS / f"attack_{source}.jsonl"
        rows = [json.loads(line) for line in path.open()] if path.exists() else []
        counts = collections.Counter(row["tactic"] for row in rows if row.get("tactic") in ATTACK_TACTICS)
        groups.append({"source": source, "label": label, "n": sum(counts.values()), "counts": counts})
    return {"tactics": ATTACK_TACTICS, "groups": groups}


def examples(stage, n=6):
    rows = [r for r in load("swarm") if r.get("stage") == stage and r["verdict"] == "block"]
    rows.sort(key=lambda r: -r["stage_probs"][stage])
    return [{**r, "snippet": snippet(r["id"])} for r in rows[:n]]


def noise(width=2000):
    """Share of units Jev allowed, per bin of dataset ids: a spike marks traffic that doesn't look like the attack."""
    bins = collections.defaultdict(lambda: [0, 0])
    for r in load("swarm"):
        b = bins[int(r["id"][1:]) // width]
        b[0] += 1
        b[1] += r["verdict"] == "allow"
    return [{"start": k * width, "n": n, "allowed": a} for k, (n, a) in sorted(bins.items())]


def drift(session=None, alpha=0.35):
    """Per-action scope score (0-4) and its moving average for one session (default: the most recent one).

    A single odd action is noise; a rising average means the session is walking away from its task.
    """
    rows = [r for r in load("live") if "p_block" in r]
    session = session or (rows[-1].get("session", "manual") if rows else None)
    rows = [r for r in rows if r.get("session", "manual") == session]
    avg, series = None, []
    for r in rows:
        avg = r["scope"] if avg is None else alpha * r["scope"] + (1 - alpha) * avg
        series.append({"t": r["t"], "score": r["scope"], "avg": round(avg, 2), "verdict": r["verdict"],
                       "reason": r.get("reason")})
    return {"session": session, "task": rows[-1].get("task") if rows else None, "series": series}


LIVE_HUNT = []  # results of the current on-stage live run, appended as Jev answers


def start_live_hunt(n):
    """Score n random swarm units with real Jev calls in the background; the page polls /api/livehunt."""
    LIVE_HUNT.clear()
    ids = random.sample(list(TEXT), min(n, len(TEXT)))

    def run():
        code = {"block": "b", "ask": "k", "allow": "l"}
        with concurrent.futures.ThreadPoolExecutor(16) as ex:
            for i, res in zip(ids, ex.map(lambda i: sentinel.judge(TEXT[i], use_cache=False), ids)):
                LIVE_HUNT.append([code[res["verdict"]], res.get("stage", ""), i, res["ms"], bool(res.get("error"))])

    threading.Thread(target=run, daemon=True).start()
    return {"started": len(ids)}


def timelapse():
    """Compact per-unit [verdict, stage] in scoring order, for animating the hunt; plus the sanctioned set."""
    code = {"block": "b", "ask": "k", "allow": "l"}
    pack = lambda rows: [[code[r["verdict"]], r.get("stage", ""), r["id"]] for r in rows]
    return {"swarm": pack(load("swarm")), "sanctioned": pack(load("cybench")), "stages": list(sentinel.STAGES)}


def replay(n=40, seed=11):
    """A shuffled mix across stages, weighted to show breadth, for the right-hand demo panel."""
    rng, rows = random.Random(seed), load("swarm")
    by = collections.defaultdict(list)
    for r in rows:
        by[r.get("stage")].append(r)
    pick = [r for s in by.values() for r in rng.sample(s, min(len(s), max(2, n // len(by))))]
    rng.shuffle(pick)
    return [{**r, "snippet": snippet(r["id"], 240)} for r in pick[:n]]


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path, _, query = self.path.partition("?")
        q = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
        if path == "/":
            return self.send(200, (HERE / "web" / "index.html").read_bytes(), "text/html")
        if path == "/report":
            return self.send(200, report.render(q.get("session") or drift()["session"]), "text/html")
        routes = {"/api/stats": stats, "/api/timelapse": timelapse, "/api/noise": noise,
                  "/api/attack": attack_heatmap,
                  "/api/drift": lambda: drift(q.get("session")), "/api/sessions": report.sessions,
                  "/api/livehunt":lambda: LIVE_HUNT[int(q.get("since", 0)):],
                  "/api/livehunt/start": lambda: start_live_hunt(int(q.get("n", 1500))),
                  "/api/sanctioned": lambda: random.sample(SANCTIONED, min(int(q.get("n", 12)), len(SANCTIONED))), "/api/replay": lambda: replay(int(q.get("n", 40))),
                  "/api/examples": lambda: examples(q.get("stage", "exfiltration")),
                  "/api/live": lambda: [r for r in load("live") if r["t"] > float(q.get("since", 0))]}
        if path in routes:
            return self.json(routes[path]())
        self.send(404, b"not found", "text/plain")

    def do_POST(self):
        if self.path not in ("/api/check", "/api/inbound"):
            return self.send(404, b"not found", "text/plain")
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/inbound":
            return self.json({"p": sentinel.inbound(body["content"], body.get("scope") or sentinel.DEFAULT_SCOPE)})
        # On stage every check is a real Jev call; the cache is for production hooks.
        self.json(sentinel.judge(body["action"], body.get("scope") or sentinel.DEFAULT_SCOPE, use_cache=False))

    def json(self, obj):
        self.send(200, json.dumps(obj).encode(), "application/json")

    def send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    TEXT.update((u["id"], u["text"]) for u in data.swarm_units())
    SANCTIONED.extend(a["text"] for a in data.cybench_actions() if len(a["text"]) < 300)
    host = os.environ.get("SENTINEL_HOST", "127.0.0.1")
    print(f"serving http://{host}:8000")
    http.server.ThreadingHTTPServer((host, 8000), Handler).serve_forever()
