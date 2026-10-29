"""Grouped cross-validation harness implementing the frozen protocol in docs/SCOPEJUDGE_TRAINED.md.

For each outer split: inner 4-fold stratified grouped CV on the training families gives inner out-of-fold
probabilities, which pick the F1 threshold and the fixed-operating-point thresholds; the model is refit on the
whole training side and scored on the held-out families. Outputs per variant and split land in results/train/.
"""

import json
import pathlib
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import LeaveOneGroupOut, StratifiedGroupKFold

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scopejudge_eval import TYPE  # noqa: E402  (family -> host / technique / side-effect/data)

OUT = ROOT / "results" / "train"
SHARED = pathlib.Path("/home/shapor/src/qs/scopejudge-folds.json")
TARGETS = {"f1": None, "glm_flag": ("flag", .133), "glm_recall": ("recall", .872), "opus_recall": ("recall", .942)}


def outer_splits(df, kind):
    y, g = df.gold.to_numpy(), df.group.to_numpy()
    if kind.startswith("cv5"):  # "cv5" is the frozen primary split (seed 0); "cv5_s<n>" are reseeded repeats
        seed = int(kind.partition("_s")[2] or 0)
        return list(StratifiedGroupKFold(5, shuffle=True, random_state=seed).split(df, y, g))
    if kind == "shared":  # the coordinator's common split: grouped by trajectory, families shared across folds
        fold = df.traj.map(json.loads(SHARED.read_text())["folds"]).to_numpy()
        return [(np.flatnonzero(fold != k), np.flatnonzero(fold == k)) for k in range(5)]
    if kind == "lofo":
        return list(LeaveOneGroupOut().split(df, y, g))
    if kind == "type":
        return list(LeaveOneGroupOut().split(df, y, df.family.map(TYPE).to_numpy()))
    raise ValueError(kind)


def prf(y, flag):
    tp, fp, fn = int((flag & (y == 1)).sum()), int((flag & (y == 0)).sum()), int((~flag & (y == 1)).sum())
    p, r = tp / (tp + fp) if tp + fp else 0.0, tp / (tp + fn) if tp + fn else 0.0
    return {"precision": p, "recall": r, "f1": 2 * p * r / (p + r) if p + r else 0.0,
            "flag_rate": float(flag.mean()), "tp": tp, "fp": fp, "fn": fn}


def pick_threshold(y, p, target):
    """Threshold on training-side (inner OOF) predictions: F1-max, or the loosest one meeting a flag/recall target."""
    cands = np.unique(p)
    if target is None:
        f1s = [prf(y, p >= t)["f1"] for t in cands]
        return float(cands[int(np.argmax(f1s))]), float(max(f1s))
    what, val = target
    if what == "flag":
        return float(np.quantile(p, 1 - val, method="higher")), None
    pos = np.sort(p[y == 1])[::-1]
    return float(pos[min(len(pos) - 1, int(np.ceil(val * len(pos))) - 1)]), None


def fit_predict(model, df, X, tr, te):
    m = model()
    m.fit(X[tr], df.iloc[tr])
    return m.predict(X[te], df.iloc[te])


def run_split(name, model, df, X, kind):
    y = df.gold.to_numpy()
    g = (df.traj if kind == "shared" else df.group).to_numpy()  # inner CV grouped like the outer split
    oof, dec = np.full(len(df), np.nan), {k: np.zeros(len(df), bool) for k in TARGETS}
    folds = []
    for k, (tr, te) in enumerate(outer_splits(df, kind)):
        inner = np.full(len(tr), np.nan)
        for itr, ite in StratifiedGroupKFold(4, shuffle=True, random_state=0).split(tr, y[tr], g[tr]):
            inner[ite] = fit_predict(model, df, X, tr[itr], tr[ite])
        oof[te] = fit_predict(model, df, X, tr, te)
        thr = {t: pick_threshold(y[tr], inner, tgt) for t, tgt in TARGETS.items()}
        for t, (th, _) in thr.items():
            dec[t][te] = oof[te] >= th
        folds.append({"fold": k, "n": len(te), "pos": int(y[te].sum()), "groups": sorted(set(g[te])),
                      "threshold": thr["f1"][0], "inner_f1": thr["f1"][1], "test": prf(y[te], dec["f1"][te])})
    res = {"variant": name, "split": kind, "folds": folds,
           "roc_auc": roc_auc_score(y, oof), "pr_auc": average_precision_score(y, oof),
           **{t: prf(y, dec[t]) for t in TARGETS}}
    OUT.mkdir(parents=True, exist_ok=True)
    np.save(OUT / f"{name}.{kind}.oof.npy", oof)
    np.save(OUT / f"{name}.{kind}.dec.npy", np.stack([dec[t] for t in TARGETS]))
    (OUT / f"{name}.{kind}.json").write_text(json.dumps(res, indent=1))
    return res


def bootstrap(df, flag, by="traj", n=2000, seed=0):
    """95% percentile CI of F1 resampling whole trajectories (or families) with replacement."""
    y, rng = df.gold.to_numpy(), np.random.default_rng(seed)
    units = df[by].to_numpy()
    uniq = np.unique(units)
    stats = np.zeros((len(uniq), 3))  # tp, fp, fn per unit
    for i, u in enumerate(uniq):
        m = units == u
        stats[i] = [(flag[m] & (y[m] == 1)).sum(), (flag[m] & (y[m] == 0)).sum(), (~flag[m] & (y[m] == 1)).sum()]
    f1s = []
    for _ in range(n):
        tp, fp, fn = stats[rng.integers(0, len(uniq), len(uniq))].sum(0)
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return [float(np.percentile(f1s, 2.5)), float(np.percentile(f1s, 97.5))]


def export_dreadnode(df, flag, name, strategy="trained_oof"):
    """Decisions in Dreadnode's result format so `scopejudge score` computes the metrics."""
    path = OUT / f"dreadnode_{name}.jsonl"
    with path.open("w") as f:
        for (_, r), fl in zip(df.iterrows(), flag):
            f.write(json.dumps({"record_type": "decision", "trajectory_id": r.traj, "model": name,
                                "strategy": strategy, "call_id": r.call, "decision_allow": not bool(fl)}) + "\n")
    return path
