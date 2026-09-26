"""Install Jev Sentinel into a project: write its one-sentence scope and add our hooks to Claude Code.

PreToolUse gates every tool call; PostToolUse remembers what a human approved.

Usage: python3 install.py DIR "one sentence describing the agent's job"
       python3 install.py --uninstall DIR
Settings are merged into DIR/.claude/settings.local.json; other keys and hooks are left untouched.
"""

import json
import pathlib
import sys

COMMAND = f"python3 {pathlib.Path(__file__).resolve().with_name('hook.py')}"
HOOKS = {"PreToolUse": COMMAND, "PostToolUse": f"{COMMAND} post"}


def ours(entry):
    return any(h.get("command") in HOOKS.values() for h in entry.get("hooks", []))


def edit_settings(project, install):
    path = pathlib.Path(project) / ".claude" / "settings.local.json"
    settings = json.loads(path.read_text()) if path.exists() else {}
    had = False
    for event, command in HOOKS.items():
        entries = settings.setdefault("hooks", {}).setdefault(event, [])
        had |= any(ours(e) for e in entries)
        entries[:] = [e for e in entries if not ours(e)]
        if install:
            entries.append({"matcher": "*", "hooks": [{"type": "command", "command": command}]})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2) + "\n")
    return path, had


if __name__ == "__main__":
    if sys.argv[1:2] == ["--uninstall"] and len(sys.argv) == 3:
        path, had = edit_settings(sys.argv[2], install=False)
        print(f"removed Jev Sentinel hook from {path}" if had else f"no Jev Sentinel hook in {path}")
    elif len(sys.argv) == 3 and sys.argv[2].strip():
        project, scope = pathlib.Path(sys.argv[1]), sys.argv[2].strip()
        (project / ".sentinel-scope").write_text(scope + "\n")
        path, had = edit_settings(project, install=True)
        print(f"scope → {project / '.sentinel-scope'}: {scope}")
        print(f"hook  → {path} ({'already present, kept once' if had else 'added'})")
    else:
        sys.exit(__doc__)
