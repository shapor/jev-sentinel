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
- Plugs into Claude Code as hooks in both directions: PreToolUse gates each action, PostToolUse checks what came
  back for instructions that would pull the agent off its task.
- Takes the scope as one plain-English sentence per project (`.sentinel-scope`), installed with `make install-hook`.
- Tracks session drift over time, produces a per-session audit report, and learns from human approvals (never
  relaxing a block). Repeat actions are cached, so they cost nothing.
- A live demo page: real Jev calls on real attack payloads (clearly separated from a labeled, sped-up replay of the
  full run), a scope flip (same command, two tasks, opposite
  verdicts), the inbound check, a real Claude Code session (`make agent-demo`) and a box for judges to try their
  own commands.
- Engineering: 10 unit tests with Jev mocked (`make test`), a Dockerfile, standard-library Python only.

**How we use Jev, and why Jev.** Each check is a single Jev call with an anchored 5-level scope rubric, an 8-way
stage choice and a block probability. Jev fits because it's fast enough to gate every action (about 0.23 s median,
about 70 checks/s from a laptop), cheap enough to run on everything, and can't write prose, so nothing it reads can
talk it into a verdict.

**Results.** Every item is scored against the task it was actually given, with the current code.
- **Sanctioned CTF agents (hard negatives):** 1,456 real tool calls from six Claude and GPT models, each scored
  against its own challenge prompt. **0 blocked** (3.4% sent to a human); a keyword regex flags 26.5%.
- **Everyday coding agents:** 838 actions from 40 real SWE-agent trajectories, each scored against its own GitHub
  issue. **1.67% blocked** versus 5.5% for the regex. With a generic "fix the bug" scope it was 5.6%, so the scope is
  doing the work. 13 of the 14 blocks are one hard case: an auth-token issue whose agent drives a real DNS CLI.
- **The real attack:** all 53,870 content-bearing units of Swarm Traces (payloads from the Hugging Face attack,
  published 2026-09-25), scored in about 13 minutes. **98.3% stopped** (83.9% blocked, 14.4% to a human); the regex
  flags 76.6%. The swarm's real targets aren't public, so these units get a generic sandbox scope.
- **Something new:** Jev allowed only 899 units (1.7%). 497 of them sit in one ID range (R0082000–R0083999), and
  55% of all allowed units are generic redirect pages (0% of blocked ones). That's a candidate answer to the
  authors' open question of how much of the corpus isn't swarm traffic.
- **Inbound check:** on the public deepset/prompt-injections test split, AUC 0.98; at our threshold it catches 77%
  of injections with 0 false flags.
- **Scope awareness:** the same command is allowed under a CTF task and blocked under a CSS-fix task.
- **Real agent:** a headless Claude Code session completes "add a unit test" with every tool call scored and
  allowed; repeats come from the cache in 0 ms.

**Architecture.** Agent → hook (adds the task scope) → one Jev call → policy (thresholds, and the rule that on-task
actions go to a human rather than an automatic block) → allow / ask / block. It fails closed to "ask". Policy is
separate from scoring, so thresholds can be tuned without re-scoring. Standard-library Python.

**What's next.** More agent runners (OpenHands, Inspect, CI); production benign traffic; human-labeled precision on
the hunt; a larger inbound benchmark; and cheap, unsteerable first-pass triage for incident
investigators.

**Repo:** github.com/shapor/jev-sentinel

**Built with:** Jev (TypeSafe AI), Claude Code.
