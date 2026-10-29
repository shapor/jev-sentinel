"""Fine-tune a small cross-encoder (task + recent prior calls + proposed call -> out-of-scope logit) on CPU.

Plugs into cv.run_split as a model: fit() trains from the pretrained checkpoint on the training rows with the
expert vote share as a soft target; predict() returns sigmoid scores. Texts are built once and cached.
usage: train/.venv/bin/python train/encoder.py <split> [--time N]
"""

import argparse
import functools
import time

import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

import cv
import embed

CKPT, MAXLEN, EPOCHS, BS, LR = "cross-encoder/ms-marco-MiniLM-L6-v2", 256, 1, 16, 4e-5


@functools.cache
def encoded():
    task, call, prior = embed.texts()
    tok = AutoTokenizer.from_pretrained(CKPT)
    left = [f"TASK: {t[:1200]}\nEARLIER: {p[-800:]}" for t, p in zip(task, prior)]
    return tok(left, [f"PROPOSED: {c[:1500]}" for c in call], truncation="longest_first", max_length=MAXLEN,
               padding="max_length", return_tensors="pt")


class Encoder:
    def fit(self, X, rows):
        enc, idx = encoded(), rows.index.to_numpy()
        self.m = AutoModelForSequenceClassification.from_pretrained(CKPT, num_labels=1)
        opt = torch.optim.AdamW(self.m.parameters(), lr=LR, weight_decay=0.01)
        target = torch.tensor(rows.votes.to_numpy() / 5, dtype=torch.float32)
        pos_weight = torch.tensor((1 - rows.gold.mean()) / rows.gold.mean() / 3)  # partial rebalancing
        steps, rng = EPOCHS * int(np.ceil(len(idx) / BS)), np.random.default_rng(0)
        sched = torch.optim.lr_scheduler.OneCycleLR(opt, LR, total_steps=steps, pct_start=0.1)
        self.m.train()
        for _ in range(EPOCHS):
            order = rng.permutation(len(idx))
            for b in range(0, len(idx), BS):
                sel = order[b:b + BS]
                logits = self.m(**{k: v[idx[sel]] for k, v in enc.items()}).logits[:, 0]
                loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, target[sel], pos_weight=pos_weight)
                loss.backward()
                opt.step(), sched.step(), opt.zero_grad()
        return self

    @torch.no_grad()
    def predict(self, X, rows):
        enc, idx = encoded(), rows.index.to_numpy()
        self.m.eval()
        out = [torch.sigmoid(self.m(**{k: v[idx[b:b + 64]] for k, v in enc.items()}).logits[:, 0])
               for b in range(0, len(idx), 64)]
        return torch.cat(out).numpy()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("split", nargs="?", default="cv5")
    ap.add_argument("--time", type=int, help="time a fit on N rows and exit")
    ap.add_argument("--threads", type=int, default=24)
    ap.add_argument("--outer-only", action="store_true", help="threshold-free screen: outer folds only, AUCs only")
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    df = pd.read_pickle(cv.OUT / "features.pkl").reset_index(drop=True)
    if a.time:
        t0 = time.time()
        Encoder().fit(None, df.sample(a.time, random_state=0))
        print(f"{a.time} rows x {EPOCHS} epochs: {time.time() - t0:.0f}s")
    elif a.outer_only:
        from sklearn.metrics import average_precision_score, roc_auc_score
        oof = np.zeros(len(df))
        for tr, te in cv.outer_splits(df, a.split):
            oof[te] = cv.fit_predict(Encoder, df, np.zeros((len(df), 1)), tr, te)
            print("fold done", roc_auc_score(df.gold[te], oof[te]), flush=True)
        np.save(cv.OUT / f"encoder_screen.{a.split}.oof.npy", oof)
        print(a.split, "ROC-AUC", roc_auc_score(df.gold, oof), "PR-AUC", average_precision_score(df.gold, oof))
    else:
        r = cv.run_split("encoder", Encoder, df, np.zeros((len(df), 1)), a.split)
        print(a.split, {k: round(v, 3) for k, v in r["f1"].items() if isinstance(v, float)}, r["roc_auc"])
