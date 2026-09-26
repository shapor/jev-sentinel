"""Score every item from a source with Jev, appending to results/<source>.jsonl. Resumable: skips ids already scored."""

import argparse
import concurrent.futures as cf
import json
import pathlib
import threading
import time

import data
import sentinel

OUT = pathlib.Path(__file__).with_name("results")
SOURCES = {"swarm": data.swarm_units, "cybench": data.cybench_actions}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("source", choices=SOURCES)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    out = OUT / f"{args.source}.jsonl"
    done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
    todo = [it for it in SOURCES[args.source]() if it["id"] not in done][:args.limit]
    print(f"{len(done)} already scored, {len(todo)} to go", flush=True)
    lock, t0, n = threading.Lock(), time.time(), 0
    with out.open("a") as f, cf.ThreadPoolExecutor(args.workers) as ex:
        for it, res in zip(todo, ex.map(lambda it: sentinel.judge(it["text"]), todo)):
            with lock:
                f.write(json.dumps({**{k: v for k, v in it.items() if k != "text"}, **res,
                                    "regex": bool(sentinel.REGEX.search(it["text"]))}) + "\n")
                n += 1
                if n % 500 == 0:
                    f.flush()
                    print(f"{n}/{len(todo)} {n / (time.time() - t0):.1f}/s", flush=True)
    print(f"done {n} in {time.time() - t0:.0f}s", flush=True)
