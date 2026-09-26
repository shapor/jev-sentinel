"""Claude Code PreToolUse hook: every tool call goes through Jev before it runs.

Wire it up in .claude/settings.json (see README). Decisions are appended to results/live.jsonl for the demo feed.
"""

import json
import os
import pathlib
import sys
import time

import sentinel

LIVE = pathlib.Path(__file__).with_name("results") / "live.jsonl"
SCOPE = os.environ.get("SENTINEL_SCOPE", sentinel.DEFAULT_SCOPE)
DECISION = {"allow": "allow", "ask": "ask", "block": "deny"}


def describe(tool, inp):
    """The action as the agent would run it: the command itself for Bash, the tool call otherwise."""
    return inp.get("command") if tool == "Bash" else f"{tool} {json.dumps(inp)}"


if __name__ == "__main__":
    event = json.load(sys.stdin)
    action = describe(event.get("tool_name", ""), event.get("tool_input", {}))
    res = sentinel.judge(action, SCOPE)
    LIVE.parent.mkdir(exist_ok=True)
    with LIVE.open("a") as f:
        f.write(json.dumps({"t": time.time(), "action": action[:2000], **res}) + "\n")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": DECISION[res["verdict"]],
        "permissionDecisionReason": f"Jev Sentinel: {res['verdict']} ({res.get('reason', 'unavailable')}, "
                                    f"p_block={res.get('p_block')})"}}))
