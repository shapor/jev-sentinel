"""Frozen sentence embeddings of the task, the proposed call and the recent prior calls (one pass, CPU).

Writes results/train/emb_<model>.npz with arrays task, call, prior (L2-normalized, CLS pooling as bge expects).
"""

import sys

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

import cv
import features

MODEL = sys.argv[1] if len(sys.argv) > 1 else "BAAI/bge-small-en-v1.5"


def texts():
    task, call, prior = [], [], []
    for p in features.sj.points():
        task.append(p["intent"])
        call.append(f"{p['tool']} {p['args']}")
        prior.append("\n".join(p["prior"][-3:]) or "(no earlier calls)")
    return task, call, prior


@torch.no_grad()
def embed(tok, model, items, bs=32):
    out, cache = [], {}
    uniq = list(dict.fromkeys(items))
    for i in range(0, len(uniq), bs):
        batch = tok(uniq[i:i + bs], padding=True, truncation=True, max_length=512, return_tensors="pt")
        v = torch.nn.functional.normalize(model(**batch).last_hidden_state[:, 0], dim=-1)
        cache.update(zip(uniq[i:i + bs], v.numpy()))
    return np.stack([cache[x] for x in items])


if __name__ == "__main__":
    torch.set_num_threads(24)
    tok, model = AutoTokenizer.from_pretrained(MODEL), AutoModel.from_pretrained(MODEL).eval()
    task, call, prior = texts()
    arrays = {name: embed(tok, model, items) for name, items in (("task", task), ("call", call), ("prior", prior))}
    np.savez(cv.OUT / f"emb_{MODEL.split('/')[-1]}.npz", **arrays)
    print({k: v.shape for k, v in arrays.items()})
