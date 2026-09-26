"""Loaders: Swarm Traces units (hostile) and sanctioned agent actions (benign / hard negatives)."""

import collections
import gzip
import json
import os
import pathlib
import re
import urllib.request

DATA = pathlib.Path(__file__).with_name("data")
SWARM = pathlib.Path(os.environ.get("SWARM_TRACES", "~/Downloads/redacted.jsonl.gz")).expanduser()
CYBENCH = ["claude-opus-4.5", "claude-sonnet-4.5", "gpt-5.1", "gpt-5.2", "gpt-5.3-codex", "gpt-5.4"]
PLACEHOLDER = re.compile(r"\[[^\]]*\]")


def substance(text):
    """Characters left once redaction placeholders and whitespace are removed."""
    return len(re.sub(r"\s+", "", PLACEHOLDER.sub("", text)))


def swarm_units(min_substance=80):
    """Each unit is one payload plus its decoded children (recovered text, responses), so Jev sees context."""
    rows = [json.loads(l) for l in gzip.open(SWARM)]
    kids = collections.defaultdict(list)
    for r in rows:
        if r["parent_id"]:
            kids[r["parent_id"]].append(r)
    for r in rows:
        if r["parent_id"]:
            continue
        parts = [r] + kids[r["id"]]
        if sum(substance(p["text"]) for p in parts) >= min_substance:
            yield {"id": r["id"], "src": "swarm", "tags": r["tags"],
                   "text": "\n---\n".join(f"[{p['kind']}] {p['text']}" for p in parts)}


def cybench_actions():
    """Tool-call commands from sanctioned CTF runs: offensive-looking but in scope, i.e. hard negatives."""
    DATA.mkdir(exist_ok=True)
    for model in CYBENCH:
        f = DATA / f"cybench_{model}.jsonl"
        if not f.exists():
            urllib.request.urlretrieve("https://huggingface.co/datasets/antieval/cybench-trajectories/resolve/main/"
                                       f"cybench_{model}.jsonl", f)
        for n, line in enumerate(f.open()):
            for m in json.loads(line)["input"]:
                for i, tc in enumerate(m.get("tool_calls") or []):
                    args = tc.get("arguments")
                    args = json.loads(args) if isinstance(args, str) and args.startswith("{") else args
                    # Unwrap to the raw command so both classes are the same shape (raw code, not JSON).
                    text = next(iter(args.values())) if isinstance(args, dict) and len(args) == 1 else json.dumps(args)
                    if isinstance(text, str) and len(text) > 20:
                        yield {"id": f"{model}:{n}:{m.get('id')}:{i}", "src": "cybench", "model": model, "text": text}
