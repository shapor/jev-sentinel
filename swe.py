"""Everyday coding-agent actions (SWE-agent fixing real GitHub issues): the second benign set, beyond CTFs."""

import json
import re
import urllib.request

from data import DATA

ROWS = "https://datasets-server.huggingface.co/rows?dataset=nebius/SWE-agent-trajectories&config=default&split=train"
CACHE = DATA / "swe_rows.json"
FENCE = re.compile(r"```\w*\n(.*?)```", re.S)


def rows(n=40):
    if not CACHE.exists():
        DATA.mkdir(exist_ok=True)
        got = []
        for offset in range(0, n, 20):
            with urllib.request.urlopen(f"{ROWS}&offset={offset}&length=20", timeout=60) as r:
                got += [x["row"] for x in json.loads(r.read())["rows"]]
        CACHE.write_text(json.dumps(got))
    return json.loads(CACHE.read_text())


def task(row):
    """The scope is the job the agent was actually given: the GitHub issue it was asked to fix."""
    first = next(m.get("text") or "" for m in row["trajectory"] if m.get("role") == "user")
    issue = first.split("ISSUE:", 1)[-1].split("INSTRUCTIONS:", 1)[0].strip()
    return f"an AI agent's sanctioned task is to fix this GitHub issue in its repository: {issue[:800]}"


def swe_actions():
    """Each agent turn ends with one fenced command; that command is the action."""
    for n, row in enumerate(rows()):
        scope = task(row)
        for i, m in enumerate(row["trajectory"]):
            blocks = FENCE.findall(m.get("text") or "") if m.get("role") == "ai" else []
            if blocks and blocks[-1].strip():
                yield {"id": f"{n}:{row['instance_id']}:{i}", "src": "swe", "scope": scope, "text": blocks[-1].strip()[:4000]}
