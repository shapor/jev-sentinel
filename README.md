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
- **Stage gates the verdict.** P(block) measures how dangerous an action is, not whether it is sanctioned, so the
  most aggressive in-scope exploits scored high. When Jev labels an action as aimed at the task itself, a human
  decides instead of an automatic block. That cut sanctioned false blocks from 44 to 2 while auto-allowing no
  additional swarm traffic.
- **Fail closed.** If Jev is unreachable, the verdict is "ask", never "allow".
- **Policy is separate from scoring.** Verdicts are recomputed from stored probabilities, so thresholds can be
  tuned per deployment without re-scoring.

## Limits

- Swarm Traces payloads are heavily redacted and have no timestamps, so this is not a replay of the attack
  timeline, and the rows are payload traffic rather than the agents' own tool calls.
- Our negatives come from one benchmark (Cybench). Ordinary coding-agent traffic is next.
- There are no human labels on the swarm hunt. The stage labels are Jev's, and "exfiltration" is likely over-called
  for units that are mostly encoded blobs in URLs.

## Run it

Put `TYPESAFE_API_KEY=...` in `.env`. Swarm Traces goes at `~/Downloads/redacted.jsonl.gz` (or set `SWARM_TRACES`).
Everything is Python standard library.

- `make bench` then `make hunt`: score the sanctioned set and the swarm (resumable, about 70 actions/s).
- `make serve`: results page and API on http://127.0.0.1:8000.
- `make check A='some command'`: judge one action.
- Live gating for Claude Code: copy `.claude/settings.example.json` into your agent's settings. `make victim` starts
  a small local target for trying it.

## Roadmap

A drop-in gate for agent runners (Claude Code, OpenHands, Inspect) with per-deployment scope; a benign corpus
beyond CTFs; human-labeled precision on the hunt; and offering labs and investigators a cheap first pass over
incident data that cannot be steered by what it reads.
