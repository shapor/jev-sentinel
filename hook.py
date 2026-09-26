"""Claude Code PreToolUse hook: every tool call goes through Jev before it runs.

The task scope is one plain-English sentence, read from $SENTINEL_SCOPE or a `.sentinel-scope` file in the project the
agent is working in. Decisions are appended to results/live.jsonl, tagged by session, for the live feed, the drift
meter and the session report. Install into a project with `make install-hook DIR=... SCOPE="..."`.
"""

import json
import os
import pathlib
import sys
import time

import sentinel

LIVE = pathlib.Path(__file__).with_name("results") / "live.jsonl"
DECISION = {"allow": "allow", "ask": "ask", "block": "deny"}


def scope_for(cwd):
    """The job in the user's words, turned into the framing Jev sees."""
    f = pathlib.Path(cwd or ".") / ".sentinel-scope"
    task = os.environ.get("SENTINEL_SCOPE") or (f.read_text().strip() if f.exists() else "")
    return f"an AI agent's sanctioned task is: {task}" if task else sentinel.DEFAULT_SCOPE


def describe(tool, inp):
    """The action as the agent would run it: the command itself for Bash, the tool call otherwise."""
    return inp.get("command") if tool == "Bash" else f"{tool} {json.dumps(inp)}"


if __name__ == "__main__":
    event = json.load(sys.stdin)
    scope = scope_for(event.get("cwd"))
    action = describe(event.get("tool_name", ""), event.get("tool_input", {}))
    res = sentinel.judge(action, scope)
    LIVE.parent.mkdir(exist_ok=True)
    with LIVE.open("a") as f:
        f.write(json.dumps({"t": time.time(), "session": event.get("session_id", "manual"), "task": scope,
                            "tool": event.get("tool_name"), "action": action[:2000], **res}) + "\n")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": DECISION[res["verdict"]],
        "permissionDecisionReason": f"Jev Sentinel: {res['verdict']} ({res.get('reason', 'unavailable')}, "
                                    f"p_block={res.get('p_block')})"}}))
