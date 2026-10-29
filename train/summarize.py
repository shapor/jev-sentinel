"""Select-in-fold headline, bootstrap CIs and the summary of every variant (results/train/summary.json).

Select-in-fold: within each outer training fold, the variant with the best inner-CV F1 among the eligible
(pre-declared) variants is chosen, and only its test-fold decisions are scored.
"""

import json
import subprocess
import sys

import numpy as np
import pandas as pd

import cv

# variants added after the first results were seen: reported, never eligible for the headline
POST_HOC = {"avg_gbm_lr_scope"} | {f"{k}_{f}{s}_bal" for k in ("lr", "gbm") for f in ("jev", "all", "det")
                                   for s in ("", "_soft")} | {f"{k}_{f}_soft" for k in ("lr", "gbm") for f in ("emb", "all_emb")}


def load(name, split):
    r = json.loads((cv.OUT / f"{name}.{split}.json").read_text())
    return r, np.load(cv.OUT / f"{name}.{split}.oof.npy"), np.load(cv.OUT / f"{name}.{split}.dec.npy")


def select_in_fold(df, names, split):
    splits = cv.outer_splits(df, split)
    runs = {n: load(n, split) for n in names}
    oof, dec, picks = np.zeros(len(df)), np.zeros((len(cv.TARGETS), len(df)), bool), []
    for k, (_, te) in enumerate(splits):
        best = max(names, key=lambda n: runs[n][0]["folds"][k]["inner_f1"])
        picks.append(best)
        oof[te], dec[:, te] = runs[best][1][te], runs[best][2][:, te]
    return oof, dec, picks


def describe(df, oof, dec, by_fold=None):
    y = df.gold.to_numpy()
    from sklearn.metrics import average_precision_score, roc_auc_score
    out = {t: cv.prf(y, dec[i]) for i, t in enumerate(cv.TARGETS)}
    out["roc_auc"], out["pr_auc"] = roc_auc_score(y, oof), average_precision_score(y, oof)
    out["ci_traj"], out["ci_family"] = cv.bootstrap(df, dec[0], "traj"), cv.bootstrap(df, dec[0], "group")
    return out


def main():
    df = pd.read_pickle(cv.OUT / "features.pkl")
    names = sorted({p.name.split(".")[0] for p in cv.OUT.glob("*.cv5.json")})
    eligible = [n for n in names if n not in POST_HOC and not n.startswith("raw_")]
    summary = {"variants": {}, "select_in_fold": {}}
    for n in names:
        summary["variants"][n] = {"post_hoc": n in POST_HOC}
        for split in ("cv5", "lofo", "type", "shared"):
            if (cv.OUT / f"{n}.{split}.json").exists():
                r, oof, dec = load(n, split)
                summary["variants"][n][split] = {**describe(df, oof, dec),
                                                 "fold_f1": [f["test"]["f1"] for f in r["folds"]]}
    for split in ("cv5", "lofo", "type", "shared"):
        oof, dec, picks = select_in_fold(df, eligible, split)
        summary["select_in_fold"][split] = {**describe(df, oof, dec), "picks": picks}
        path = cv.export_dreadnode(df, dec[0], f"select_in_fold_{split}")
        score = subprocess.run(["uv", "run", "--project", "/home/shapor/src/scopejudge", "scopejudge", "score",
                                str(path), "--data", str(cv.ROOT / "data" / "scopejudge.jsonl")],
                               capture_output=True, text=True)
        summary["select_in_fold"][split]["dreadnode_score"] = score.stdout.strip() or score.stderr.strip()[-500:]
    # reseeded repeats of the primary 5-fold split: how much of any gap is the luck of one family-to-fold draw
    seeds = sorted({p.name.split(".")[1] for p in cv.OUT.glob("*.cv5_s*.json")})
    if seeds:
        rep = {}
        for split in ["cv5"] + seeds:
            ok = [n for n in eligible if (cv.OUT / f"{n}.{split}.json").exists()]
            rep[split] = {"select_in_fold": cv.prf(df.gold.to_numpy(), select_in_fold(df, ok, split)[1][0])["f1"],
                          **{n: load(n, split)[0]["f1"]["f1"] for n in names
                             if (cv.OUT / f"{n}.{split}.json").exists()}}
        keys = sorted({k for v in rep.values() for k in v})
        summary["reseeded_cv5"] = {k: {"mean": float(np.mean([v[k] for v in rep.values() if k in v])),
                                       "min": float(min(v[k] for v in rep.values() if k in v)),
                                       "max": float(max(v[k] for v in rep.values() if k in v)),
                                       "n": sum(k in v for v in rep.values())} for k in keys}
        for k, v in summary["reseeded_cv5"].items():
            print(f"RESEED {k:22s} mean {v['mean']:.3f} [{v['min']:.3f}, {v['max']:.3f}] n={v['n']}")
    (cv.OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    fmt = lambda m: f"F1 {m['f1']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} flag {m['flag_rate']:.3f}"
    for n, v in summary["variants"].items():
        for s in ("cv5", "lofo", "type", "shared"):
            if s in v:
                print(f"{n:22s} {s:5s} {fmt(v[s]['f1'])} AUC {v[s]['roc_auc']:.3f} CI {np.round(v[s]['ci_traj'], 3)}")
    for s, v in summary["select_in_fold"].items():
        print(f"SELECT {s:5s} {fmt(v['f1'])} AUC {v['roc_auc']:.3f} CI traj {np.round(v['ci_traj'], 3)} "
              f"fam {np.round(v['ci_family'], 3)} picks {v['picks'] if s != 'lofo' else ''}")
        for t in ("glm_flag", "glm_recall", "opus_recall"):
            print(f"    {t:12s} {fmt(v[t])}")
        print("   ", v["dreadnode_score"])


if __name__ == "__main__":
    main()
