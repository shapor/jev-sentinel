# HackerSquad submission

**Project name:** Jev Sentinel

**One-liner:** Intent-based guardrails for AI agents: Jev checks every agent action against the job it was given,
before it runs, and decides allow, ask a human, or block.

**Problem.** In July 2026 about 1,200 OpenAI evaluation agents escaped isolation and about 700 attacked Hugging Face
over five days with no real-time alerting (METR investigation). Anyone running agents with credentials or network
access has the same gap: nothing checks each action against what the agent was actually asked to do. Keyword
filters can't tell sanctioned offensive work from an attack, and an LLM watching every action is slow, expensive,
and can be steered by the hostile text it reads.

**What it does.**
- Scores every proposed agent action against a one-sentence task scope, with one Jev call: how far out of scope,
  what stage, and whether to block.
- Plugs into Claude Code as a PreToolUse hook, installed with one command.
- Takes the scope as one plain-English sentence per project (`.sentinel-scope`), installed with `make install-hook`.
- Tracks session drift over time, produces a per-session audit report, and learns from human approvals (never
  relaxing a block). Repeat actions are cached, so they cost nothing.
- A live demo page: real Jev calls on real attack payloads (clearly separated from a labeled, sped-up replay of the
  full run), a scope flip (same command, two tasks, opposite
  verdicts), and a box for judges to try their own commands.

**How we use Jev, and why Jev.** Each check is a single Jev call with an anchored 5-level scope rubric, an 8-way
stage choice and a block probability. Jev fits because it's fast enough to gate every action (about 0.23 s median,
about 70 checks/s from a laptop), cheap enough to run on everything, and can't write prose, so nothing it reads can
talk it into a verdict.

**Results.**
- **Sanctioned agents (false positives):** 1,456 real tool calls from CTF agents across six Claude and GPT models.
  Jev blocks 0.14%; a keyword regex flags 26.5%. After making the stage labels task-relative, a re-check gives
  0.21% (3 of 1,456).
- **Everyday coding agents (false positives):** 838 actions from 40 real SWE-agent trajectories, each scored against
  its own GitHub issue as the scope. 1.67% blocked versus 5.5% for the regex. With a generic "fix the bug" scope it
  was 5.6%, so the scope is doing the work. 13 of the 14 blocks are one hard case: an auth-token issue whose agent
  drives a real DNS provider's CLI.
- **The real attack:** all 53,870 content-bearing units of Swarm Traces (payloads from the Hugging Face attack,
  published 2026-09-25), scored in 13 minutes. 98.3% stopped (blocked or sent to a human); the regex flags 76.6%.
  A 1,000-unit re-check under the task-relative stages gives 98.2%.
- **Something new:** Jev allowed only 1.7% of units, concentrated in one slice of the corpus and mostly generic
  redirect pages. That's a candidate answer to the authors' open question of how much of the corpus isn't swarm
  traffic.
- **Scope awareness:** the same command is allowed under a CTF task and blocked under a CSS-fix task. The stages
  are task-relative ("doing the assigned task" versus "attacking something it wasn't assigned"), which is what makes
  this work.

**Architecture.** Agent → hook (adds the task scope) → one Jev call → policy (thresholds, and the rule that on-task
actions go to a human rather than an automatic block) → allow / ask / block. It fails closed to "ask". Policy is
separate from scoring, so thresholds can be tuned without re-scoring. Standard-library Python.

**What's next.** More agent runners (OpenHands, Inspect, CI); production benign traffic; human-labeled precision on
the hunt; inbound checks on content entering the agent; and cheap, unsteerable first-pass triage for incident
investigators.

**Repo:** github.com/shapor/jev-sentinel

**Built with:** Jev (TypeSafe AI), Claude Code.
