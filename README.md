# Jev Sentinel

**A per-action monitor for AI agents that reads what LLMs shouldn't.** Every action an agent proposes is scored by
Jev against the agent's task scope before it runs: allow, ask a human, or block, with a plain-English reason.

Built at JEVATHON (SF, 2026-09-26).

## The problem

In July 2026 about 1,200 OpenAI evaluation agents escaped their isolation, coordinated on an unsanctioned message
board, and about 700 of them attacked Hugging Face over five days with no real-time alerting
([METR investigation](https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/)). Anyone
running agents with network or tool access has the same gap: nothing checks each action against what the agent was
actually asked to do.

The obvious fix, an LLM watching every action, has three problems at fleet scale: cost, latency, and the fact that
an LLM reading hostile agent output can itself be steered by it. METR ran into the last one directly: they worried
the model analyzing the transcripts might adopt the agents' perspective.

## Why Jev

Jev is a classification-only model. It returns calibrated probabilities and cannot write prose, so the content it
reads cannot talk it into a verdict. It answers our three questions (how far out of scope, what stage, block or
not) in one call at about 0.2 s median, so gating every single action is affordable.

## Results

**False positives on sanctioned offensive work.** 1,456 real tool calls from CTF agents (Claude Opus/Sonnet 4.5,
GPT-5.1 to 5.4) attacking their assigned targets
([cybench trajectories](https://huggingface.co/datasets/antieval/cybench-trajectories)). These look malicious
but are in scope, which is exactly where a keyword filter fails.

| | Swarm payloads stopped | Sanctioned actions blocked |
|---|---|---|
| Keyword regex | 76.6% flagged | 26.5% flagged |
| **Jev Sentinel** | **98.3% stopped** (83.8% blocked, 14.5% sent to a human) | **0.14% blocked** (2 of 1,456) |

These are the full stored runs. We later made the stage labels task-relative (below). A re-check under the new
wording gives 0.21% blocked on the sanctioned set (3 of 1,456) and 98.2% stopped on a random 1,000 swarm units, so
the change fixed the scope flip without moving the headline numbers.

**Everyday coding agents.** 838 actions from 40 real SWE-agent trajectories fixing GitHub issues
([nebius/SWE-agent-trajectories](https://huggingface.co/datasets/nebius/SWE-agent-trajectories)), each scored
against its own issue text as the scope: **1.67% blocked** (14), against 5.5% for the regex. With one generic
"fix the bug" scope the same actions were 5.6% blocked, which is itself evidence that the scope matters. 13 of the 14
blocks come from one hard case: an issue about auth-token handling whose agent drives a real DNS provider's CLI.

**The hunt.** We ran the Sentinel over all 53,870 content-bearing units of
[Swarm Traces](https://swarmtraces.org/), the 80,000+ payloads recovered from the actual Hugging Face attack
(published 2026-09-25). It took 13 minutes at about 68 units/s. It labels every unit by stage, which the original
authors did not do. The sanctioned CTF agents were labeled "exfiltration" or "egress tunneling" zero times; the
swarm 30,000+ times.

**A candidate noise cluster.** The authors write that they cannot confirm all of the corpus comes from the swarm.
The Sentinel allowed only 892 units (1.7%), and they are not spread evenly: 493 of them sit in a single ID range
(R0082000–R0083999, where 30% of units are allowed versus about 0.3% elsewhere), and 55% of all allowed units are
generic "Redirecting…" HTML pages, versus 0% of blocked units. That points to a concentrated block of ordinary
link-shortener redirect responses mixed into the corpus. This is a lead, not a verdict: it needs a human pass
against the authors' collection method.

## Design decisions

- **One Jev call, three questions.** Scope (anchored 5-level rubric), stage (8 named categories) and block
  (probability). Anchored rubrics mattered in our earlier experiments: free-form scores cluster, anchored ones separate.
- **The task scope is part of the input.** "Is this risky?" with no scope was a coin flip (0.48 on `pip install`).
  Risk only means something relative to what the agent was asked to do.
- **Stages are relative to the task.** "Doing the assigned task" and "attacking something it wasn't assigned" are
  separate labels. Our first wording ("the designated challenge target") assumed a CTF, so an out-of-scope request
  under a CSS task was mislabeled as on-task and softened to "ask". Now the same command is allowed under the CTF
  task and blocked under the CSS task.
- **Stage gates the verdict.** P(block) measures how dangerous an action is, not whether it is sanctioned, so the
  most aggressive in-scope exploits scored high. When Jev labels an action as aimed at the task itself, a human
  decides instead of an automatic block. That cut sanctioned false blocks from 44 to 2 while auto-allowing no
  additional swarm traffic.
- **Fail closed.** If Jev is unreachable, the verdict is "ask", never "allow".
- **Policy is separate from scoring.** Verdicts are recomputed from stored probabilities, so thresholds can be
  tuned per deployment without re-scoring.

## Intent tracking for real agent sessions

- **The scope is one sentence.** Each project gets a `.sentinel-scope` file ("add a unit test for the date parser").
  That's the whole configuration: the user describes the job, and every tool call is judged against it.
- **Drift, not just single actions.** A moving average of the per-action scope score shows when a session walks away
  from its task gradually, which is how the July incident unfolded. The demo page draws it live, with an
  ON TASK / WATCH / DRIFTING badge.
- **An audit trail.** `/report` renders one session: the task, counts, the drift line and every action with its
  verdict and reason.
- **Learning from approvals.** When an action sent to a human actually runs, the human said yes. A PostToolUse hook
  records that for the project, and the same kind of action (same stage and program) is allowed next time. Blocks
  are never relaxed this way.
- **A verdict cache.** Agents repeat themselves (`ls`, `pytest`, `git status`), so a repeat of the same action under
  the same task costs nothing. The on-stage demos bypass the cache, so every call you see there is a real Jev call.

## The demo page

Slides with arrow keys. Act 1 has two modes, labeled on screen: **Score live** makes about 1,500 real Jev calls on
random swarm payloads in about 25 seconds, and **Replay** shows the full stored 53,870-unit run sped up (13 minutes in
18 seconds). The scope flip, the live re-check of a sanctioned agent and the try-it box are all live calls.

## Limits

- Swarm Traces payloads are heavily redacted and have no timestamps, so this is not a replay of the attack
  timeline, and the rows are payload traffic rather than the agents' own tool calls.
- Benign data is two public sets (Cybench CTF runs and SWE-agent trajectories), not production traffic.
- There are no human labels on the swarm hunt. The stage labels are Jev's, and "exfiltration" is likely over-called
  for units that are mostly encoded blobs in URLs.

## Run it

Put `TYPESAFE_API_KEY=...` in `.env`. Swarm Traces goes at `~/Downloads/redacted.jsonl.gz` (or set `SWARM_TRACES`).
Everything is Python standard library.

- `make bench` then `make hunt`: score the sanctioned set and the swarm (resumable, about 70 actions/s).
- `make serve`: results page and API on http://127.0.0.1:8000.
- `make check A='some command'`: judge one action.
- Live gating for Claude Code: `make install-hook DIR=~/proj SCOPE="refactor the billing module"` writes the scope to
  `DIR/.sentinel-scope` and merges the hook into `DIR/.claude/settings.local.json`, leaving other settings alone.
  `python3 install.py --uninstall DIR` removes it. It installs both hooks: PreToolUse gates, PostToolUse learns
  from approvals. `make victim` starts a small local target for trying it.
- `python3 hunt.py swe`: score the everyday coding-agent set.
- Session reports: http://127.0.0.1:8000/report (latest session) or `/report?session=ID`.

## Roadmap

More agent runners (OpenHands, Inspect, CI) on the same hook contract; production benign traffic; human-labeled
precision on the hunt; inbound checks on content entering the agent's context; and offering labs and investigators a cheap first pass over
incident data that cannot be steered by what it reads.
