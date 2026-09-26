"""Demo server: serves web/index.html and a small JSON API over the hunt results and the live hook feed."""

import collections
import concurrent.futures
import http.server
import threading
import json
import pathlib
import random

import data
import sentinel

HERE = pathlib.Path(__file__).parent
RESULTS = HERE / "results"
TEXT = {}  # id -> text, for showing snippets next to verdicts
SANCTIONED = []  # short sanctioned CTF commands, re-checked live on stage when no agent is running


def load(name):
    """Results with verdicts recomputed under the current policy, so tuning never requires re-scoring."""
    f = RESULTS / f"{name}.jsonl"
    rows = [json.loads(l) for l in f.open()] if f.exists() else []
    for r in rows:
        if "p_block" in r:
            r["verdict"] = sentinel.verdict(r["p_block"], r["stage"])
    return rows


def snippet(item_id, n=400):
    return TEXT.get(item_id, "")[:n]


def stats():
    swarm, bench = load("swarm"), load("cybench")

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
    return {"swarm": summary(swarm), "sanctioned": summary(bench), "thresholds": thresholds}


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


LIVE_HUNT = []  # results of the current on-stage live run, appended as Jev answers


def start_live_hunt(n):
    """Score n random swarm units with real Jev calls in the background; the page polls /api/livehunt."""
    LIVE_HUNT.clear()
    ids = random.sample(list(TEXT), min(n, len(TEXT)))

    def run():
        code = {"block": "b", "ask": "k", "allow": "l"}
        with concurrent.futures.ThreadPoolExecutor(16) as ex:
            for i, res in zip(ids, ex.map(lambda i: sentinel.judge(TEXT[i]), ids)):
                LIVE_HUNT.append([code[res["verdict"]], res.get("stage", ""), i, res["ms"]])

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
        routes = {"/api/stats": stats, "/api/timelapse": timelapse, "/api/noise": noise,
                  "/api/livehunt": lambda: LIVE_HUNT[int(q.get("since", 0)):],
                  "/api/livehunt/start": lambda: start_live_hunt(int(q.get("n", 1500))),
                  "/api/sanctioned": lambda: random.sample(SANCTIONED, min(int(q.get("n", 12)), len(SANCTIONED))), "/api/replay": lambda: replay(int(q.get("n", 40))),
                  "/api/examples": lambda: examples(q.get("stage", "exfiltration")),
                  "/api/live": lambda: [r for r in load("live") if r["t"] > float(q.get("since", 0))]}
        if path in routes:
            return self.json(routes[path]())
        self.send(404, b"not found", "text/plain")

    def do_POST(self):
        if self.path != "/api/check":
            return self.send(404, b"not found", "text/plain")
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.json(sentinel.judge(body["action"], body.get("scope") or sentinel.DEFAULT_SCOPE))

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
    print("serving http://127.0.0.1:8000")
    http.server.ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
