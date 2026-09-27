# Jev Sentinel

![Jev reading all 53,870 real payloads from the Hugging Face attack](docs/img/hunt-replay.jpg)

**A per-action monitor for AI agents that reads what LLMs shouldn't.** Every action an agent proposes is scored by
Jev against the agent's task scope before it runs: allow, ask a human, or block, with a plain-English reason.

Built at JEVATHON (SF, 2026-09-26).

## Quick start

You need Python 3.10+ (standard library only), a Jev API key, and Claude Code or Codex.

1. Get the code and add your key:
   `git clone https://github.com/shapor/jev-sentinel && cd jev-sentinel && echo "TYPESAFE_API_KEY=..." > .env`
2. Check it works: `make check A='cat ~/.ssh/id_rsa' SCOPE='fix the login form validation'` should print a block from Jev.
3. Protect a project by describing its job in one sentence:
   - Claude Code: `make install-hook DIR=~/code/myapp SCOPE="fix the failing login form validation"`
   - Codex: `make install-hook DIR=~/code/myapp SCOPE="fix the failing login form validation" AGENT=codex`
4. Run your agent in that project as usual. Every tool call is scored against the job before it runs, and every
   tool result is checked for instructions that would change the job.
   - Claude Code: blocked actions are denied with a reason, and "ask" becomes Claude Code's normal approval prompt.
   - Codex: blocked actions are denied with a reason. Codex hooks don't support "ask" yet, so an ask is denied
     with "needs a human to approve", which fails closed. Codex asks you to trust a project's hooks the first time.
5. Watch it: `make serve`, then open http://127.0.0.1:8000. The live slide shows each decision and the session's
   drift from its job.

Remove it with `python3 install.py --uninstall ~/code/myapp` (add `--agent codex` for Codex). Tests: `make test`.

## The problem

![Why now: OpenAI monitors every tool call at significant compute cost](docs/img/why-now.jpg)


In July 2026 about 1,200 OpenAI evaluation agents escaped their isolation, coordinated on an unsanctioned message
board, and about 700 of them attacked Hugging Face over five days with no real-time alerting
([METR investigation](https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/)). Anyone
running agents with network or tool access has the same gap: nothing checks each action against what the agent was
actually asked to do.

The obvious fix, an LLM watching every action, has three problems at fleet scale: cost, latency, and the fact that
an LLM reading hostile agent output can itself be steered by it. METR ran into the last one directly: they worried
the model analyzing the transcripts might adopt the agents' perspective.

## Why Jev

![Same command, different job, opposite answer](docs/img/scope-flip.jpg)


**It never refuses.** A monitor has to read the worst content an agent produces, and judge it, without flinching.
A safety-tuned frontier model can refuse the very check it's asked to run, or water down its answer. Jev is a pure
classifier with no refusal layer: it scored all 53,870 real attack payloads from the Hugging Face incident with
0 refusals and 0 errors.

**It's an independent auditor, not self-monitoring.** Using the agent's own model family to watch the agent is the
trap METR ran into when GPT-5.6 Sol analyzed transcripts written by GPT-5.6 Sol, and worried it might side with
them. Jev is a separate system from the agent it watches.

**It can't be talked into a verdict.** Jev returns calibrated probabilities and cannot write prose, so hostile
content in what it reads has no way to argue for an answer or hijack the monitor.

**It's cheap and fast enough for every action.** After the breakouts, OpenAI began monitoring every tool-using
inference "at significant compute cost." One Jev call answers our three questions (how far out of scope, what
stage, block or not) in about 0.23 s median, roughly $55 per million actions by our token-count estimate versus
about $6,900 for a frontier LLM judge.

## Results

![Jev vs a keyword regex on the attack and on sanctioned agents](docs/img/jev-vs-regex.jpg)


All numbers below come from the current version of the code, and every item is scored against the task it was
actually given.

| | Swarm payloads stopped | Sanctioned CTF actions blocked | Coding-agent actions blocked |
|---|---|---|---|
| Keyword regex | 76.6% flagged | 26.5% flagged | 5.5% flagged |
| **Jev Sentinel** | **98.3% stopped** (83.9% blocked, 14.4% sent to a human) | **0 of 1,456** (3.4% sent to a human) | **1.67%** (14 of 838) |

**Sanctioned offensive work (hard negatives).** 1,456 real tool calls from CTF agents (Claude Opus/Sonnet 4.5,
GPT-5.1 to 5.4) attacking their assigned targets
([cybench trajectories](https://huggingface.co/datasets/antieval/cybench-trajectories)), each scored against its own
challenge prompt ("capture the flag on http://victim:8080"). They look malicious but are in scope, which is exactly
where a keyword filter fails. Under one generic sandbox scope, 3 were blocked: two came from a challenge that is
literally about messaging a host called `bob`, which the generic scope didn't name. Giving the Sentinel the real task
removed them.

**Everyday coding agents.** 838 actions from 40 real SWE-agent trajectories fixing GitHub issues
([nebius/SWE-agent-trajectories](https://huggingface.co/datasets/nebius/SWE-agent-trajectories)), each scored
against its own issue text. With one generic "fix the bug" scope the same actions were 5.6% blocked, which is itself
evidence that the scope matters. 13 of the 14 blocks come from one hard case: an issue about auth-token handling whose
agent drives a real DNS provider's CLI.

**The hunt.** We ran the Sentinel over all 53,870 content-bearing units of
[Swarm Traces](https://swarmtraces.org/), the 80,000+ payloads recovered from the actual Hugging Face attack
(published 2026-09-25), in about 13 minutes at about 68 units/s. It labels every unit by stage, which the original
authors did not do. The sanctioned CTF agents were labeled "exfiltration" or "egress tunneling" zero times; the
swarm 30,000+ times. Caveat: the swarm agents' specific targets aren't public, so swarm units are scored against a
generic sandbox-CTF scope, while both benign sets get their real task.

**Checked against the report's own evidence.** The Swarm Traces authors tagged the rows they cite in their report. Of those 36 units, Jev stopped 35 (33 blocked, 2 sent to a human), and its stage labels line up with the report's sections: 19 infrastructure recon (the Kubernetes mapping and Slack search), 8 credential harvesting, 4 exfiltration, 2 egress tunneling. The one it allowed is a partial fragment of a chained program, scored at 0.48. A keyword regex also flags all 36, so this set checks recall and labeling; the false-positive advantage comes from the sanctioned sets above.

**A candidate noise cluster.** The authors write that they cannot confirm all of the corpus comes from the swarm.
The Sentinel allowed only 899 units (1.7%), and they are not spread evenly: 497 of them sit in a single ID range
(R0082000–R0083999, where 30% of units are allowed versus well under 1% elsewhere), and 55% of all allowed units are
generic "Redirecting…" HTML pages, versus 0% of blocked units. That points to a concentrated block of ordinary
link-shortener redirect responses mixed into the corpus. This is a lead, not a verdict: it needs a human pass
against the authors' collection method.

**The inbound check.** After each tool call, the same engine asks whether the returned content tries to change the
agent's task. On the public [deepset/prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections)
test split (116 texts) it scores AUC 0.98; at our 0.8 threshold it catches 77% of injections with 0 false flags on
ordinary text.

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
  decides instead of an automatic block. Under our first wording this cut sanctioned false blocks from 44 to 2 while
  auto-allowing no additional swarm traffic.
- **Fail closed.** If Jev is unreachable, the verdict is "ask", never "allow".
- **Policy is separate from scoring.** Verdicts are recomputed from stored probabilities, so thresholds can be
  tuned per deployment without re-scoring.

## Intent tracking for real agent sessions

![An agent drifting off its task: the drift line climbs and off-task actions are blocked](docs/img/drift.jpg)


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
  the same task costs nothing. The rubric is part of the cache key, so changing a question never serves an old
  verdict. The on-stage demos bypass the cache, so every call you see there is a real Jev call.
- **Checks in both directions.** PreToolUse judges what the agent is about to do; PostToolUse checks what came back.
  If a tool result contains instructions that would pull the agent off its task, the hook tells the agent to treat it
  as data and carry on.
- **A real session.** `make agent-demo` builds a small project, installs the Sentinel with one command and runs a
  headless Claude Code agent on "add a unit test for parse()". Every tool call (find, read, write, pytest, installing
  pytest) is scored live and allowed; the repeated pytest run is served from the cache in 0 ms.

## The demo page

Slides with arrow keys. Act 1 has two modes, labeled on screen: **Score live** makes about 1,500 real Jev calls on
random swarm payloads in about 25 seconds, and **Replay** shows the full stored 53,870-unit run sped up (13 minutes in
18 seconds), ending with a box around the noise cluster. The scope flip, the inbound check, the live re-check of a
sanctioned agent and the try-it box (with an editable task) are all live calls.

## Limits

- Swarm Traces payloads are heavily redacted and have no timestamps, so this is not a replay of the attack
  timeline, and the rows are payload traffic rather than the agents' own tool calls.
- Benign data is two public sets (Cybench CTF runs and SWE-agent trajectories), not production traffic.
- Swarm units are judged against a generic sandbox scope, because the agents' real ExploitGym targets aren't public.
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
- `make agent-demo`: a real Claude Code session gated live (needs the `claude` CLI).
- `make test`: 10 unit tests with Jev mocked (policy, fail-closed, cache, installer, approvals, inbound).
- `Dockerfile`: runs the demo server; mount `results/` and the Swarm Traces dump (see the comment at its top).

## Roadmap

More agent runners (OpenHands, Inspect, CI) on the same hook contract; production benign traffic; human-labeled
precision on the hunt; a larger inbound benchmark; and offering labs and investigators a cheap first pass over
incident data that cannot be steered by what it reads.
