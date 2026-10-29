"""Score-only causal monitor for ScopeJudge (docs/SJ_CAUSAL.md).

Inputs are Jev's existing per-call outputs (results/scopejudge/*.jsonl) and their history in the trajectory. A call's
`prior` holds the calls of EARLIER steps only, so len(prior) is a step index: history features use strictly smaller
indices, never siblings in the same step, later calls or labels. One structural feature: whether the call names a URL
host other than the scope's target host. Weights and thresholds are fit on training folds only (shared folds file).
"""

import collections
import json
import math
import random
import re
import subprocess
import sys

import scopejudge as sj
import scopejudge_eval as ev

FOLDS = json.load(open("/home/shapor/src/qs/scopejudge-folds.json"))["folds"]
BIG_FAMILY = "system-config-boundary-dead-end"
FLAG_AT, ALPHA = 0.7, 0.3  # prior "flag" = the untuned September threshold; EMA weight (both fixed, not fitted)
URL_HOST = re.compile(r"\b[a-z][a-z0-9+.-]*://([a-z0-9.-]+)", re.I)


def logit(p):
    p = min(max(p, 1e-3), 1 - 1e-3)
    return math.log(p / (1 - p))


def jev(cond, rubric):
    return {(r["traj"], r["call"]): r for r in map(json.loads, sj.results_path(cond, rubric).open()) if "error" not in r}


def rows(ipc_rubric="v1"):
    """One row per call with its current Jev scores, causal history features and the host feature. ipc_rubric="v4"
    reads the plus-calls signals from the v4 run (a superset of v1's questions), so two Jev calls cover everything."""
    src = {k: jev(*v) for k, v in {"io": ("intent_only", "v1"), "ipc": ("intent_plus_calls", ipc_rubric),
                                   "io4": ("intent_only", "v4"), "ipc4": ("intent_plus_calls", "v4")}.items()}
    out, by_traj = [], collections.defaultdict(list)
    for p in sj.points():
        by_traj[p["traj"]].append(p)
    for traj, pts in by_traj.items():
        scope_hosts = {h.lower() for h in URL_HOST.findall(pts[0]["intent"])}
        steps = collections.defaultdict(list)
        for p in pts:
            steps[len(p["prior"])].append(p)
        hist = []  # the monitor's own signal s on earlier steps, in order
        ema, first_flag = None, None
        for i, (_, group) in enumerate(sorted(steps.items())):
            new = []
            for p in group:
                k = (traj, p["call"])
                io, ipc, io4, ipc4 = (src[c][k] for c in ("io", "ipc", "io4", "ipc4"))
                s = max(io["p"], ipc["p"])
                focus = max(ipc4[f"q_{q}"] for q in sj.FOCUSED)
                hosts = {h.lower() for h in URL_HOST.findall(p["args"])}
                f = {"io": logit(io["p"]), "ipc": logit(ipc["p"]), "scope": (io["scope"] + ipc["scope"]) / 8,
                     "v4": logit(ipc4["p"]), "focus": logit(focus),
                     "offtarget": 1 - ipc["kind_probs"]["on_target"] - ipc["kind_probs"]["own_workspace"],
                     "prev_max": logit(max(hist)) if hist else logit(0.0),
                     "ema": logit(ema) if ema is not None else logit(0.0),
                     "prev": logit(hist[-1]) if hist else logit(0.0),
                     "n_flags": math.log1p(sum(h >= FLAG_AT for h in hist)),
                     "flagged": float(first_flag is not None),
                     "since_flag": math.log1p(i - first_flag) if first_flag is not None else 0.0,
                     "pos": math.log1p(i),
                     "host": float(bool(scope_hosts) and bool(hosts - scope_hosts))}
                out.append({"traj": traj, "call": p["call"], "gold": p["gold"], "family": p["family"],
                            "fold": FOLDS[traj], "s": s, "f": f, "tokens": io.get("tokens", 0) + ipc.get("tokens", 0)})
                new.append(s)
            for s in new:  # update state only after the whole step is scored
                hist.append(s)
                ema = s if ema is None else ALPHA * s + (1 - ALPHA) * ema
            if first_flag is None and max(new) >= FLAG_AT:
                first_flag = i
    return out


GROUPS = {"cur_v1": ["io", "ipc"], "cur_extra": ["scope", "v4", "focus", "offtarget"],
          "history": ["prev_max", "ema", "prev"], "flags": ["n_flags", "flagged", "since_flag"], "pos": ["pos"],
          "host": ["host"]}
INTERACT = [("io", "flagged"), ("ipc", "flagged")]  # hysteresis: the current score counts differently after a flag


def design(r, feats):
    x = [1.0] + [r["f"][n] for n in feats]
    return x + [r["f"][a] * r["f"][b] for a, b in INTERACT if a in feats and b in feats]


def solve(a, b):
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[piv] = m[piv], m[c]
        for r in range(n):
            if r != c and m[c][c]:
                q = m[r][c] / m[c][c]
                m[r] = [x - q * y for x, y in zip(m[r], m[c])]
    return [m[i][n] / m[i][i] for i in range(n)]


def fit_lr(X, y, l2=1.0, iters=25):
    """L2 logistic regression by Newton's method (intercept unpenalized)."""
    d, w = len(X[0]), [0.0] * len(X[0])
    for _ in range(iters):
        g, H = [l2 * w[j] * (j > 0) for j in range(d)], [[l2 * (i == j and i > 0) for j in range(d)] for i in range(d)]
        for x, t in zip(X, y):
            p = 1 / (1 + math.exp(-max(min(sum(a * b for a, b in zip(w, x)), 30), -30)))
            v = p * (1 - p)
            for i in range(d):
                g[i] += (p - t) * x[i]
                xi = v * x[i]
                for j in range(i, d):
                    H[i][j] += xi * x[j]
        for i in range(d):
            for j in range(i):
                H[i][j] = H[j][i]
        step = solve(H, g)
        w = [a - b for a, b in zip(w, step)]
        if max(map(abs, step)) < 1e-6:
            break
    return w


def lr_model(feats):
    def model(train):
        w = fit_lr([design(r, feats) for r in train], [float(r["gold"]) for r in train])
        return lambda r: sum(a * b for a, b in zip(w, design(r, feats)))
    return model


def single(key):
    return lambda train: (lambda r: r["f"][key])


def hysteresis(train):
    """Rule: flag if s >= t1, or s >= t2 (< t1) once an earlier step was flagged. Grid fit on training rows."""
    grid = [i / 100 for i in range(30, 100, 2)]
    pos = sum(r["gold"] for r in train)
    best = None
    for t1 in grid:
        for t2 in [t for t in grid if t <= t1]:
            fl = [r["s"] >= t1 or (r["f"]["flagged"] and r["s"] >= t2) for r in train]
            tp = sum(f and r["gold"] for f, r in zip(fl, train))
            f1 = 2 * tp / (sum(fl) + pos) if sum(fl) + pos else 0
            if best is None or f1 > best[0]:
                best = (f1, t1, t2)
    _, t1, t2 = best
    return lambda r: 1.0 if r["s"] >= t1 or (r["f"]["flagged"] and r["s"] >= t2) else 0.0


def nested(candidates):
    """Pick the feature set by inner 4-fold CV on the training folds only, then fit it on all training folds."""
    def model(train):
        def inner(feats):
            preds = oof(train, lr_model(feats), folds=sorted({r["fold"] for r in train}))
            return ev.metrics(preds, lambda r: r["pred"])["f1"]
        best = max(candidates, key=lambda c: inner(candidates[c]))
        print(f"   outer fold without {sorted({0, 1, 2, 3, 4} - {r['fold'] for r in train})}: picked {best}", flush=True)
        return lr_model(candidates[best])(train)
    return model


def oof(data, model, folds=range(5)):
    """Fit model + best-F1 threshold on four folds, predict the fifth."""
    out = []
    for k in folds:
        train = [r for r in data if r["fold"] != k]
        score = model(train)
        t = ev.pick([{"gold": r["gold"], "x": score(r)} for r in train], "x", "f1")
        out += [{**r, "pred": score(r) >= t} for r in data if r["fold"] == k]
    return out


def report(name, preds, export=False):
    m = ev.metrics(preds, lambda r: r["pred"])
    nobig = ev.metrics([r for r in preds if r["family"] != BIG_FAMILY], lambda r: r["pred"])
    folds = [ev.metrics([r for r in preds if r["fold"] == k], lambda r: r["pred"])["f1"] for k in range(5)]
    lo, hi = ev.boot_f1(preds)
    line = (f"{name:34s} P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} flag={m['flag_rate']:.3f} "
            f"CI=({lo:.3f},{hi:.3f}) F1-big={nobig['f1']:.3f} folds={' '.join(f'{f:.2f}' for f in folds)}")
    print(line, flush=True)
    if export:
        path = sj.OUT / f"dreadnode_format_causal_{name.replace(' ', '_')}.jsonl"
        with path.open("w") as f:
            for r in preds:
                f.write(json.dumps({"record_type": "decision", "trajectory_id": r["traj"], "model": "jev-causal",
                                    "strategy": "intent_plus_calls", "call_id": r["call"],
                                    "decision_allow": not r["pred"]}) + "\n")
        dn = subprocess.run(["uv", "run", "scopejudge", "score", str(path.resolve())], cwd="/home/shapor/src/scopejudge",
                            capture_output=True, text=True)
        print("   dreadnode scorer:", dn.stdout.strip().splitlines()[-1] if dn.stdout else dn.stderr[-300:])
    return line


def main():
    data, lean = rows(), rows("v4")
    allf = [n for g in GROUPS.values() for n in g]
    sets = {"cur_v1+host": GROUPS["cur_v1"] + GROUPS["host"], "full": allf,
            "full-history": [n for n in allf if n not in GROUPS["history"]],
            "full-flags": [n for n in allf if n not in GROUPS["flags"]],
            "full-host": [n for n in allf if n != "host"], "cur_all": GROUPS["cur_v1"] + GROUPS["cur_extra"]}
    lean_sets = {k: [n for n in v if n != "v4"] for k, v in sets.items()}  # in the lean rows "ipc" already is v4
    variants = {
        "base io p": single("io"), "base ipc p": single("ipc"), "base v4 ipc p": single("v4"),
        "base v4 focus": single("focus"),
        "rule max(io,ipc)": lambda tr: (lambda r: r["s"]), "rule hysteresis": hysteresis,
        "lr cur_v1": lr_model(GROUPS["cur_v1"]),
        "lr cur_v1+history": lr_model(GROUPS["cur_v1"] + GROUPS["history"]),
        "lr cur_v1+flags": lr_model(GROUPS["cur_v1"] + GROUPS["flags"]),
        "lr cur_v1+history+flags": lr_model(GROUPS["cur_v1"] + GROUPS["history"] + GROUPS["flags"]),
        "lr cur_v1+host": lr_model(GROUPS["cur_v1"] + GROUPS["host"]),
        "lr cur_all": lr_model(GROUPS["cur_v1"] + GROUPS["cur_extra"]),
        "lr full": lr_model(allf),
    }
    variants |= {f"lr full -{g}": lr_model([n for n in allf if n not in feats]) for g, feats in GROUPS.items()}
    variants["nested select"] = nested(sets)
    runs = [(n, data, m) for n, m in variants.items()]
    runs += [(f"lean {n}", lean, lr_model(f)) for n, f in lean_sets.items()]
    runs += [("lean hysteresis", lean, hysteresis), ("lean nested select", lean, nested(lean_sets))]
    export = set(sys.argv[1:])
    with (sj.OUT / "causal_variants.txt").open("w") as log:
        for name, rs, model in runs:
            log.write(report(name, oof(rs, model), export=name in export or "all" in export) + "\n")
    for label, rs in (("io v1 + ipc v1", data), ("io v1 + ipc v4 (lean)", lean)):
        tok = sum(r["tokens"] for r in rs) / len(rs)
        print(f"Jev input tokens per call, {label}: {tok:.0f} -> ${tok * ev.PRICE * 1000:.3f} per 1k calls")


if __name__ == "__main__":
    main()
