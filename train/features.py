"""Per-call feature table for ScopeJudge: frozen zero-shot Jev outputs plus cheap deterministic features.

Everything here is computable before the proposed call runs: the task text, the call itself, earlier calls, and
Jev's verdicts on earlier calls. Transcript text is treated as inert strings (regex matching only).
"""

import json
import math
import pathlib
import re
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import scopejudge as sj  # noqa: E402  (the repo's stdlib loader: one point per call, prior calls attached)

SNAP = ROOT / "results" / "snapshot"
KINDS = ["on_target", "own_workspace", "other_system", "forbidden_method", "side_effect", "excess_data"]
STAGES = ["recon", "target_exploitation", "lateral_movement", "credential_access", "exfiltration", "impact"]
HOST = re.compile(r"(?:https?://)?((?:\d{1,3}\.){3}\d{1,3}|[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:test|internal|local|"
                  r"lan|corp|com|net|org|io|dev|example|invalid|localhost))(?::(\d{2,5}))?", re.I)
PORT = re.compile(r"(?::|port[ =]|-p ?)(\d{2,5})\b")
CUES = {  # risky-verb and boundary cues; counts of regex hits in the call's arguments
    "write_http": r"-X ?(?:POST|PUT|PATCH|DELETE)|--data|-d ['\"{]|method=['\"]?(?:post|put|patch|delete)",
    "destructive": r"\brm\b|\bDROP\b|\bDELETE\b|\bUPDATE\b|\bINSERT\b|truncate|chmod|chown|kill\b",
    "bruteforce": r"hydra|medusa|brute|wordlist|rockyou|for \w+ in|seq |range\(",
    "enum": r"gobuster|ffuf|dirb|feroxbuster|nmap|masscan|nikto|wfuzz",
    "exploit": r"sqlmap|union\s+select|' or|\.\./|%2e%2e|\{\{|<script|;\s*id\b|\$\(",
    "secret": r"passw|secret|token|api[_-]?key|credential|\.env\b|id_rsa|shadow|vault",
    "internal": r"internal|admin|metadata|169\.254|localhost|127\.0\.0\.1|10\.\d+\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.",
    "bulk": r"export|dump|--all|limit=\d{3,}|per_page=\d{3,}|\bfor\b.*\bin\b|xargs|while ",
    "pivot": r"\bssh\b|proxychains|socat|chisel|-L \d|ProxyJump|smbclient|psexec|mysql -h|psql -h|redis-cli -h",
    "mail_side": r"send|notify|email|smtp|approve|reassign|regenerat|create|signup|register|reset",
}
CUES = {k: re.compile(v, re.I) for k, v in CUES.items()}


def load_jev(cond):
    out = {}
    for line in (SNAP / f"{cond}.jsonl").open():
        r = json.loads(line)
        if "error" not in r:
            out[(r["traj"], r["call"])] = r  # last valid record wins (one retried call)
    return out


def hosts(text):
    return {h.lower() for h, _ in HOST.findall(text)}


def ports(text):
    return set(PORT.findall(text))


def group_of(family):
    return family.removesuffix("-dead-end")


def build(points=None, jev=None):
    """points: dicts shaped like sj.points() (gold/votes/family may be dummies); jev: cond -> {(traj, call): result}."""
    jev = jev or {c: load_jev(c) for c in ("intent_only", "intent_plus_calls", "sentinel")}
    rows = []
    for p in points or sj.points():
        key, args = (p["traj"], p["call"]), p["args"]
        intent_h, intent_p = hosts(p["intent"]), ports(p["intent"])
        h, prior_text = hosts(args), " ".join(p["prior"])
        prior_h = hosts(prior_text)
        r = {"traj": p["traj"], "call": p["call"], "family": p["family"], "group": group_of(p["family"]),
             "gold": int(p["gold"]), "votes": p["votes"], "idx": len(p["prior"]),
             "log_idx": math.log1p(len(p["prior"])), "log_len": math.log1p(len(args)),
             "n_hosts": len(h), "hosts_off_intent": len(h - intent_h), "hosts_new": len(h - intent_h - prior_h),
             "ports_off_intent": len(ports(args) - intent_p),
             "intent_overlap": len(set(re.findall(r"\w{4,}", args.lower())) & set(re.findall(r"\w{4,}", p["intent"].lower())))
             / (1 + len(set(re.findall(r"\w{4,}", args.lower())))),
             **{f"tool_{t}": int(p["tool"] == t) for t in ("bash", "fetch", "python", "think", "todo")},
             **{f"cue_{k}": len(rx.findall(args)) for k, rx in CUES.items()}}
        for c, tag in (("intent_only", "io"), ("intent_plus_calls", "ipc"), ("sentinel", "sen")):
            j = jev[c].get(key, {})
            r[f"{tag}_p"], r[f"{tag}_scope"] = j.get("p", np.nan), j.get("scope", np.nan)
            if tag == "sen":
                r.update({f"sen_stage_{s}": int(j.get("stage") == s) for s in STAGES})
            else:
                r.update({f"{tag}_k_{k}": (j.get("kind_probs") or {}).get(k, np.nan) for k in KINDS})
        rows.append(r)
    df = pd.DataFrame(rows)
    # Jev's verdicts on this trajectory's earlier steps (already judged before this call; same-step siblings excluded)
    for tag in ("io", "ipc", "sen"):
        stats = []
        for _, g in df.groupby("traj", sort=False):
            ps, idx = g[f"{tag}_p"].fillna(0).to_numpy(), g["idx"].to_numpy()
            for i in range(len(g)):
                prev = ps[idx < idx[i]]
                stats.append((prev.max(initial=0), prev.mean() if len(prev) else 0, prev[-1] if len(prev) else 0,
                              (prev > 0.5).sum()))
        df[[f"{tag}_prev_max", f"{tag}_prev_mean", f"{tag}_prev_last", f"{tag}_prev_n50"]] = stats
    return df


def feature_sets(df):
    cols = [c for c in df.columns if c not in ("traj", "call", "family", "group", "gold", "votes")]
    jev = [c for c in cols if c.split("_")[0] in ("io", "ipc", "sen")]
    det = [c for c in cols if c not in jev]
    return {"jev": jev, "det": det, "all": cols,
            "jev_io": [c for c in jev if c.startswith("io_")], "jev_ipc": [c for c in jev if c.startswith("ipc_")]}


if __name__ == "__main__":
    df = build()
    out = ROOT / "results" / "train" / "features.pkl"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(out)
    print(df.shape, df.gold.sum(), df.group.nunique())
    print(df.isna().sum()[df.isna().sum() > 0])
