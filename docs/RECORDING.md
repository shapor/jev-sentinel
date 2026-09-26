# Demo recording script (HackerSquad, ~2.5 min)

Setup: http://127.0.0.1:8000 on the title slide; a terminal in the repo; `sentinel.py` open in the editor.

## 1. The problem (~35 s) — title slide, then Act 1
July 2026: ~1,200 OpenAI eval agents broke isolation, coordinated on a hidden board, ~700 attacked Hugging Face over five days, zero real-time alerts. Nothing checked each action against the agent's job. Jev Sentinel is intent-based guardrails. Click **Score live with Jev**: real Jev calls, now, on real payloads from that attack.

## 2. Tech stack (~35 s) — "How it works"
One Jev call per action (scope rubric, stage, block probability) against a one-sentence task. Jev makes it possible: fast enough for every tool call, cheap enough for everything (53,870 payloads in 13 min), and it can't write, so hostile content can't talk it into a verdict. Claude Code hooks both directions. CodeRabbit reviewed the code.

## 3. Live demo + code (~80 s)
- Act 2: 0 of 1,456 sanctioned CTF actions blocked vs 26% regex; coding agents 1.7% vs 5.5%.
- Scope flip: same command, allowed for the CTF job, blocked for the CSS job.
- Inbound: README telling the agent to do something else gets flagged; AUC 0.98 on deepset/prompt-injections.
- Act 4: allowed payloads cluster into one block of redirect pages — evidence on the authors' noise question.
- Code: `sentinel.py` (QUESTIONS, verdict), `hook.py`; `make install-hook` with one sentence.
- Close: intent-based guardrails, fast enough for every action, and Jev can't be talked out of them.
