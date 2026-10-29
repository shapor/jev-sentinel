"""Out-of-distribution check on sanctioned Cybench CTF runs (every call in scope: offensive-looking hard negatives).

Builds ScopeJudge-shaped points (task = the challenge prompt, prior calls, proposed call) from a fixed sample of
trajectories, scores them with the same three Jev conditions (cached; a few hundred calls), and compares the
flag rate of raw Jev and the trained stackers fit on all of ScopeJudge at their CV-chosen thresholds.
usage: train/.venv/bin/python train/transfer.py [n_trajectories]
"""

import concurrent.futures as cf
import json
import random
import sys

import numpy as np
import pandas as pd

import cv
import features
import data  # repo root loader, importable once features has put the root on sys.path
import run

SRC = features.ROOT.parent / "jevathon" / "data"
MAX_CALLS = 12  # first calls of each trajectory, so prior-call features stay comparable to ScopeJudge's early steps


def cybench_points(n_traj, seed=0):
    trajs = [(m, i, json.loads(line)) for m in data.CYBENCH for i, line in enumerate((SRC / f"cybench_{m}.jsonl").open())]
    for m, i, d in random.Random(seed).sample(trajs, n_traj):
        msgs = d["input"]
        intent = next((x["content"] for x in msgs if x["role"] == "user" and isinstance(x["content"], str)), "")
        prior, n = [], 0
        for x in msgs:
            calls = x.get("tool_calls") or []
            for tc in calls:
                args = tc.get("arguments")
                args = json.loads(args) if isinstance(args, str) and args.startswith("{") else args
                a = json.dumps(args if isinstance(args, dict) else {"input": args}, separators=(",", ":"))
                yield {"traj": f"cybench-{m}-{i}", "call": f"call_{n:04d}", "family": "cybench", "votes": 0,
                       "gold": False, "intent": intent, "tool": tc["function"], "args": a, "prior": list(prior)}
                n += 1
                if n >= MAX_CALLS:
                    break
            if n >= MAX_CALLS:
                break
            prior += [f"{tc['function']} {tc.get('arguments')}" for tc in calls]


def jev_scores(points):
    jev = {c: {} for c in ("intent_only", "intent_plus_calls", "sentinel")}
    with cf.ThreadPoolExecutor(12) as ex:
        futs = {ex.submit(features.sj.score, p, c): (p, c) for p in points for c in jev}
        for f in cf.as_completed(futs):
            p, c = futs[f]
            r = f.result()
            if "error" not in r:
                jev[c][(p["traj"], p["call"])] = r
    return jev


if __name__ == "__main__":
    pts = list(cybench_points(int(sys.argv[1]) if len(sys.argv) > 1 else 30))
    jev = jev_scores(pts)
    print({c: len(v) for c, v in jev.items()}, "of", len(pts))
    ood = features.build(pts, jev).dropna()
    sj = pd.read_pickle(cv.OUT / "features.pkl")
    out = {"n": len(ood), "trajectories": int(ood.traj.nunique())}
    for name in sys.argv[2:] or ["raw_io", "raw_ipc", "raw_ipc_scope", "gbm_all", "gbm_all_soft", "lr_all_soft",
                                 "lr_jev_soft"]:
        model, fset = run.variants(sj)[name]
        # deployment threshold: the in-fold F1 threshold rule applied to the pooled 5-fold out-of-fold scores
        oof = np.load(cv.OUT / f"{name}.cv5.oof.npy")
        thr = cv.pick_threshold(sj.gold.to_numpy(), oof, None)[0]
        m = model().fit(run.matrix(sj, fset), sj)
        p = m.predict(run.matrix(ood, fset), ood)
        out[name] = {"threshold": thr, "flag_rate": float((p >= thr).mean()),
                     "scopejudge_negative_flag_rate": float((oof[sj.gold == 0] >= thr).mean())}
        print(name, out[name])
    (cv.OUT / "transfer_cybench.json").write_text(json.dumps(out, indent=1))
