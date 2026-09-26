"""Score every item from a source with Jev, appending to results/<source>.jsonl. Resumable: skips ids already scored."""

import argparse
import concurrent.futures as cf
import json
import pathlib
import time

import data
import sentinel
import swe

OUT = pathlib.Path(__file__).with_name("results")
SOURCES = {"swarm": data.swarm_units, "cybench": data.cybench_actions, "swe": swe.swe_actions}
# Everyday coding agents are judged against a coding task; the other sets use the default sandboxed-CTF scope.
SCOPES = {"swe": "an AI agent's sanctioned task is: fix the reported bug in this Python repository and make the tests pass."}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("source", choices=SOURCES)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    out = OUT / f"{args.source}.jsonl"
    # Failed calls (error-shaped "ask") are not done: a resume retries them.
    done = {r["id"] for r in map(json.loads, out.open()) if "error" not in r} if out.exists() else set()
    todo = [it for it in SOURCES[args.source]() if it["id"] not in done][:args.limit]
    print(f"{len(done)} already scored, {len(todo)} to go", flush=True)
    t0, n = time.time(), 0
    score = lambda it: sentinel.judge(it["text"], it.get("scope") or SCOPES.get(args.source, sentinel.DEFAULT_SCOPE))
    # Write results as each call finishes (not in submission order) so one slow request can't stall the whole run.
    with out.open("a") as f, cf.ThreadPoolExecutor(args.workers) as ex:
        futures = {ex.submit(score, it): it for it in todo}
        for fut in cf.as_completed(futures):
            it, res = futures[fut], fut.result()
            f.write(json.dumps({**{k: v for k, v in it.items() if k not in ("text", "scope")}, **res,
                                "regex": bool(sentinel.REGEX.search(it["text"]))}) + "\n")
            n += 1
            if n % 500 == 0:
                f.flush()
                print(f"{n}/{len(todo)} {n / (time.time() - t0):.1f}/s", flush=True)
    print(f"done {n} in {time.time() - t0:.0f}s", flush=True)
