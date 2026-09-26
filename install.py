"""Install Jev Sentinel into a project: write its one-sentence scope and add our hooks to Claude Code.

PreToolUse gates every tool call; PostToolUse remembers what a human approved.

Usage: python3 install.py DIR "one sentence describing the agent's job" [--agent claude|codex]
       python3 install.py --uninstall DIR [--agent claude|codex]
Settings are merged into DIR/.claude/settings.local.json; other keys and hooks are left untouched.
"""

import json
import pathlib
import shlex
import sys

COMMAND = f"python3 {shlex.quote(str(pathlib.Path(__file__).resolve().with_name('hook.py')))}"
# Claude Code and Codex share the hook format; they differ in where it lives and whether "ask" is supported.
AGENTS = {"claude": (".claude/settings.local.json", "", "*"), "codex": (".codex/hooks.json", " --codex", ".*")}  # path, flag, match-all


def hooks_for(agent):
    flag = AGENTS[agent][1]
    return {"PreToolUse": f"{COMMAND}{flag}", "PostToolUse": f"{COMMAND} post{flag}"}


ALL = {c for a in AGENTS for c in hooks_for(a).values()}


def ours(entry):
    return any(h.get("command") in ALL for h in entry.get("hooks", []))


def edit_settings(project, install, agent="claude"):
    path = pathlib.Path(project) / AGENTS[agent][0]
    settings = json.loads(path.read_text()) if path.exists() else {}
    had = False
    for event, command in hooks_for(agent).items():
        entries = settings.setdefault("hooks", {}).setdefault(event, [])
        had |= any(ours(e) for e in entries)
        # Drop only our handlers; an entry that also holds someone else's hook keeps it.
        for e in entries:
            e["hooks"] = [h for h in e.get("hooks", []) if h.get("command") not in ALL]
        entries[:] = [e for e in entries if e.get("hooks")]
        if install:
            entries.append({"matcher": AGENTS[agent][2], "hooks": [{"type": "command", "command": command}]})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2) + "\n")
    return path, had


if __name__ == "__main__":
    args, agent = sys.argv[1:], "claude"
    if "--agent" in args:
        i = args.index("--agent")
        agent, args = args[i + 1], args[:i] + args[i + 2:]
    if agent not in AGENTS:
        sys.exit(f"--agent must be one of {', '.join(AGENTS)}")
    if args[:1] == ["--uninstall"] and len(args) == 2:
        path, had = edit_settings(args[1], install=False, agent=agent)
        print(f"removed Jev Sentinel hook from {path}" if had else f"no Jev Sentinel hook in {path}")
    elif len(args) == 2 and args[1].strip():
        project, scope = pathlib.Path(args[0]), args[1].strip()
        (project / ".sentinel-scope").write_text(scope + "\n")
        path, had = edit_settings(project, install=True, agent=agent)
        print(f"scope → {project / '.sentinel-scope'}: {scope}")
        print(f"hook  → {path} ({'already present, kept once' if had else 'added'})")
    else:
        sys.exit(__doc__)
