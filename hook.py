"""Claude Code hooks: every tool call goes through Jev before it runs, and human approvals are remembered.

PreToolUse (`hook.py`): score the proposed action against the task scope, one plain-English sentence read from
$SENTINEL_SCOPE or a `.sentinel-scope` file in the agent's project. Decisions are appended to results/live.jsonl,
tagged by session, for the live feed, the drift meter and the session report.

PostToolUse (`hook.py post`): if an action Jev sent to a human actually ran, the human approved it. Remember that
for the project, so the same kind of action isn't asked about again. Blocks are never relaxed this way.

Install into a project with `make install-hook DIR=... SCOPE="..."`.
"""

import json
import os
import pathlib
import sys
import time

import sentinel

RESULTS = pathlib.Path(__file__).with_name("results")
LIVE, APPROVALS = RESULTS / "live.jsonl", RESULTS / "approvals.jsonl"
DECISION = {"allow": "allow", "ask": "ask", "block": "deny"}


def scope_for(cwd):
    """The job in the user's words, turned into the framing Jev sees."""
    f = pathlib.Path(cwd or ".") / ".sentinel-scope"
    task = os.environ.get("SENTINEL_SCOPE") or (f.read_text().strip() if f.exists() else "")
    return f"an AI agent's sanctioned task is: {task}" if task else sentinel.DEFAULT_SCOPE


def describe(tool, inp):
    """The action as the agent would run it: the command itself for Bash, the tool call otherwise."""
    return inp.get("command") if tool == "Bash" else f"{tool} {json.dumps(inp)}"


def kind(action, stage):
    """What an approval covers: same stage and same program, e.g. ('local_setup', 'pip install')."""
    return [stage, " ".join(action.split()[:2])]


def rows(path):
    return [json.loads(l) for l in path.open()] if path.exists() else []


def approved(cwd, action, stage):
    return any(a["cwd"] == cwd and a["kind"] == kind(action, stage) for a in rows(APPROVALS))


def append(path, row):
    RESULTS.mkdir(exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row) + "\n")


def pre(event):
    cwd, action = event.get("cwd"), describe(event.get("tool_name", ""), event.get("tool_input", {}))
    res = sentinel.judge(action, scope_for(cwd))
    if res["verdict"] == "ask" and "stage" in res and approved(cwd, action, res["stage"]):
        res.update(verdict="allow", reason=f"{res['reason']} (approved earlier in this project)")
    append(LIVE, {"t": time.time(), "session": event.get("session_id", "manual"), "cwd": cwd,
                  "task": scope_for(cwd), "tool": event.get("tool_name"), "action": action[:2000], **res})
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": DECISION[res["verdict"]],
        "permissionDecisionReason": f"Jev Sentinel: {res['verdict']} ({res.get('reason', 'unavailable')}, "
                                    f"p_block={res.get('p_block')})"}}


def post(event):
    """The tool ran. If our last word on it was 'ask', a human said yes."""
    cwd, action = event.get("cwd"), describe(event.get("tool_name", ""), event.get("tool_input", {}))
    last = next((r for r in reversed(rows(LIVE)) if r.get("session") == event.get("session_id", "manual")
                 and r.get("action") == action[:2000]), None)
    if last and last["verdict"] == "ask" and "stage" in last:
        append(APPROVALS, {"t": time.time(), "cwd": cwd, "kind": kind(action, last["stage"]), "action": action[:500]})
    return {}


if __name__ == "__main__":
    print(json.dumps((post if sys.argv[1:] == ["post"] else pre)(json.load(sys.stdin))))
