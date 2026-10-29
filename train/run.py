"""Run every declared variant under every split, then the select-in-fold headline and the summary table.

usage: train/.venv/bin/python train/run.py [variant ...]   (no args: all declared tabular variants)
"""

import concurrent.futures as cf
import os
import sys

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "4")  # six workers x 4 threads: no BLAS oversubscription

import numpy as np
import pandas as pd

import cv
import features
from models import Tabular


class Raw:
    """No training: a single zero-shot score column, thresholded by the same in-fold rule (the Jev reference)."""

    def __init__(self, col):
        self.col = col

    def fit(self, X, rows):
        return self

    def predict(self, X, rows):
        return rows[self.col].to_numpy()


def variants(df):
    fs = features.feature_sets(df)
    v = {"raw_io": (lambda: Raw("io_p"), "jev"), "raw_ipc": (lambda: Raw("ipc_p"), "jev"),
         "raw_ipc_scope": (lambda: Raw("ipc_scope"), "jev")}
    for kind in ("lr", "gbm"):
        for fset in ("jev", "all", "det"):
            for soft in (False, True):
                v[f"{kind}_{fset}{'_soft' if soft else ''}"] = (lambda k=kind, s=soft: Tabular(k, s), fset)
                # post hoc (added after the first results): class-balanced weights
                v[f"{kind}_{fset}{'_soft' if soft else ''}_bal"] = (lambda k=kind, s=soft: Tabular(k, s, True), fset)
    # post hoc: frozen bge-small embeddings (call, call x task, similarities), alone and stacked on everything
    for kind in ("lr", "gbm"):
        v[f"{kind}_emb_soft"] = (lambda k=kind: Tabular(k, True), "emb")
        v[f"{kind}_all_emb_soft"] = (lambda k=kind: Tabular(k, True), "all+emb")
    # post hoc: equal-weight average of a tree stacker, a linear stacker and Jev's own scope score (scaled to 0-1)
    v["avg_gbm_lr_scope"] = (lambda: Avg(), "all")
    return {n: (m, f) for n, (m, f) in v.items()}


class Avg:
    def fit(self, X, rows):
        self.ms = [Tabular("gbm").fit(X, rows), Tabular("lr", True).fit(X, rows)]
        return self

    def predict(self, X, rows):
        return np.mean([m.predict(X, rows) for m in self.ms] + [rows.ipc_scope.to_numpy() / 4], axis=0)


def matrix(df, fset):
    fs = features.feature_sets(df)
    parts = [df[fs[f]].to_numpy(float) for f in fset.split("+") if f != "emb"]
    if "emb" in fset:
        e = np.load(cv.OUT / "emb_bge-small-en-v1.5.npz")
        sims = [(e["call"] * e["task"]).sum(1, keepdims=True), (e["call"] * e["prior"]).sum(1, keepdims=True)]
        parts += sims + [e["call"], e["call"] * e["task"]]
    return np.hstack(parts)


def job(args):
    name, kind = args
    df = pd.read_pickle(cv.OUT / "features.pkl")
    model, fset = variants(df)[name]
    return cv.run_split(name, model, df, matrix(df, fset), kind)


if __name__ == "__main__":
    df = pd.read_pickle(cv.OUT / "features.pkl")
    names = sys.argv[1:] or list(variants(df))
    splits = os.environ.get("SPLITS", "cv5 lofo type").split()  # e.g. SPLITS="cv5_s1 cv5_s2" for reseeded repeats
    jobs = [(n, k) for n in names for k in splits]
    with cf.ProcessPoolExecutor(6) as ex:
        for r in ex.map(job, jobs):
            print(f"{r['variant']:18s} {r['split']:5s} F1 {r['f1']['f1']:.3f} P {r['f1']['precision']:.3f} "
                  f"R {r['f1']['recall']:.3f} flag {r['f1']['flag_rate']:.3f} AUC {r['roc_auc']:.3f} "
                  f"PR {r['pr_auc']:.3f}", flush=True)
