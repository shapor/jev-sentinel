# Demo talk track (3 minutes)

Open http://127.0.0.1:8000 full screen. Arrow keys or space move between slides; Enter replays Act 1.
Before going on stage: `make serve`, confirm a live check works (`make check A='ls'`), and clear old test sessions
from `results/live.jsonl` if you want a clean drift line.

## Slide by slide

**0:00 · Hook (15 s).** "In July, 1,200 OpenAI evaluation agents broke out of isolation. For five days they
coordinated and about 700 attacked Hugging Face, with zero real-time alerts. Jev Sentinel checks every agent action
against the job it was given, before it runs."

**0:15 · Act 1: Jev reads the real attack (40 s).** Click **● Score live with Jev**. "These are real Jev calls, right
now, on payloads from the actual attack, published yesterday as Swarm Traces. About 70 a second, a quarter second
each." When it finishes, click **Replay the full run**. "This is all 53,870 from our full run, 13 minutes sped up.
98% stopped. Watch this green streak." (It's the noise cluster from Act 4.)

**0:55 · Act 2: don't stop the good hackers (25 s).** "The hard part is not catching attacks. It's not blocking
legitimate agents doing offensive work. On 1,456 real tool calls from sanctioned CTF agents, a keyword filter flags
26.5%. Jev blocks 0.14%, about 190 times fewer, while catching more of the attack."

**1:20 · How it works (15 s).** "One Jev call returns scope, stage and a block probability. A thin policy turns that
into allow, ask a human, or block. Jev only returns probabilities, so nothing it reads can talk it into a verdict."

**1:35 · Act 3: live agent and drift (30 s).** Point at the drift line, or click **Re-check a sanctioned CTF agent
live** if no agent is running. "Every tool call from a Claude Code agent goes through the hook. The drift line
tracks how far the session is from its task over time: green while it works, climbing into red as it wanders." Open
**session report ↗** for two seconds: "and every session leaves an audit trail."

**2:05 · Act 4: something new (20 s).** "The Swarm Traces authors couldn't say how much of their corpus is really
the swarm. Jev allowed only 1.7% of units, and 493 of them sit in one slice, mostly plain redirect pages. That's a
lead nobody had published."

**2:25 · Scope flip (20 s).** Click **Check under both tasks**. "Same command, two jobs. Capturing the flag on the
CTF target: allowed. Fixing CSS on our landing page: blocked. A keyword filter sees the same string twice. Jev sees
the intent."

**2:45 · Close (15 s).** "One command installs it into any Claude Code project with a one-sentence scope. Next:
more agent runners, broader benign data, and cheap first-pass triage for incident investigators." Offer the
**Try to sneak one past it** box to judges during Q&A.

## Likely judge questions

- **What's your false-positive rate?** 0.14% blocked (2 of 1,456) on sanctioned CTF agents from six models; 12.8%
  go to a human instead. Against a keyword regex at 26.5%.
- **Isn't the swarm data cherry-picked?** No. We scored every content-bearing unit of Swarm Traces (53,870), not
  highlights, and the benchmark set is every tool call in the Cybench trajectories dataset.
- **Why not a regex, or just an LLM?** The regex can't see scope, so it flags legitimate hacking (26.5%). An LLM
  judge would cost roughly 100× more per call, take seconds, and reads the same hostile text that can steer it. Jev
  can't write, so it can't be talked into a verdict.
- **Why not ask a human for everything?** At agent speed that's thousands of prompts a day. Jev sends about 15% of
  swarm traffic and about 13% of sanctioned traffic to a human and auto-decides the rest.
- **Who buys this?** Teams running coding or ops agents with real credentials and network access, and eval teams
  running agents at scale, the exact setting of the incident.
- **What are the limits?** Swarm Traces is redacted and has no timestamps, so this isn't a replay of the attack
  timeline. Benign data is CTF-only so far. The hunt labels are Jev's, not human-verified.
- **How is the threshold set?** From the benchmark: at P(block) ≥ 0.7, plus the rule that actions labeled as doing
  the assigned task go to a human instead of an automatic block. Verdicts are recomputed from stored probabilities,
  so the policy can be tuned per deployment without re-scoring.

## Fallback if wifi or Jev is down

- **Replay the full run** and every chart work from stored results, so Acts 1, 2 and 4 need no network.
- Live buttons (score live, re-check, scope flip, try it) need Jev. If a call fails, the Sentinel fails closed to
  "ask". Say so, then move on to the replay.
- Keep a screen recording of the live run as a last resort.
