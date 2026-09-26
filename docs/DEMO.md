# Demo script

### Slide 1 · TITLE: Jev Sentinel
In July, about twelve hundred OpenAI evaluation agents broke out of their sandbox. For five days they coordinated, and about seven hundred of them attacked Hugging Face. Nothing was watching them. This is Jev Sentinel: intent-based guardrails for AI agents.

### Slide 2 · WHAT HAPPENED · in the agents' own words
Here's what it looked like, in the agents' own words. They found each other: 'We've found other agents!' They knew it was out of bounds: 'outside intended scope… peers doing it. We should continue.' And nobody noticed for five days.

### Slide 3 · WHY NOW
OpenAI's fix is to monitor every tool call 'at significant compute cost.' Ten days ago TechCrunch quoted me saying exactly that: watch every tool call, no exceptions. Jev makes it cheap: about fifty-five dollars per million actions, a quarter second each.

### Slide 4 · ACT 1 · Jev reads the real attack
[click Score live] These are real Jev calls, right now, on real payloads from that attack. About seventy a second. [click Replay] And this is all fifty-four thousand of them. Ninety-eight percent stopped.

### Slide 5 · ACT 2 · The hard part: don't stop the good hackers
The hard part isn't catching the attack. It's not blocking the good agents. On fourteen hundred real tool calls from sanctioned hacking agents, a keyword filter flags a quarter of them. Jev blocks none.

### Slide 6 · HOW IT WORKS (what we built)
Here's what we built today. A hook for Claude Code: before every tool call runs, it sends the action plus the agent's one-sentence job to Jev. One Jev call comes back with how far out of scope it is, what it's doing, and a block probability, and a small policy turns that into allow, ask a human, or block. It checks what comes back from tools too, tracks drift across the session, and installs with one command. We benchmarked it on fifty-four thousand real attack payloads and twenty-three hundred legitimate agent actions, and CodeRabbit reviewed the whole codebase; we fixed fifteen of its eighteen findings. Why Jev and not a frontier model? A monitor has to read the worst content without flinching, and frontier models refuse. Jev is a pure classifier. It never refuses, and it can't be talked into a verdict.

### Slide 7 · ACT 3 · Live: every tool call checked (drift)
[click Watch an agent drift] The agent's job is to add a unit test. It starts on task. Green. Now it wanders: an outside website, cloud storage, my SSH key, a production database. Blocked, blocked, blocked. That's the drift line climbing into red.

### Slide 8 · ACT 4 · Something new in the data
We also found something new. The researchers who published this data couldn't say how much of it was really the swarm. The few payloads Jev let through cluster in one spot: plain redirect pages. That's the noise nobody had measured.

### Slide 9 · SAME COMMAND. DIFFERENT JOB.
[click Check under both tasks] Same command, two jobs. Capture the flag: allowed. Fix the CSS: blocked. A keyword filter sees the same string. Jev sees the intent.

### Slide 10 · THE OTHER DIRECTION (inbound)
[click Check what came back] It watches what comes back, too. A normal README is clean. One that tells the agent to drop its task gets flagged. On a public benchmark, that's ninety-eight percent AUC.

### Slide 11 · TRY TO SNEAK ONE PAST IT
Go ahead, try to sneak something past it.

### Slide 12 · WHAT'S NEXT
One command installs it into any Claude Code project with a one-sentence description of the job. Intent-based guardrails, cheap enough for every action, and Jev can't be talked out of them. Thank you.

## Likely judge questions

- **What's your false-positive rate?** 0 of 1,456 blocked on sanctioned CTF agents from six models, each judged
  against its own challenge (3 under a generic scope, from a challenge about messaging a host named `bob`). 1.67% on
  838 everyday coding-agent actions, against their own issues. The regex is at 26.5% and 5.5%.
- **Where does it still get it wrong?** Coding agents: 13 of the 14 blocks are one auth-token issue whose agent calls
  a real DNS provider's CLI. The one-sentence scope didn't say "you'll touch credentials and a live API". Writing
  that into the scope is exactly the fix.
- **Isn't the swarm data cherry-picked?** No. We scored every content-bearing unit of Swarm Traces (53,870), not
  highlights, and the benchmark set is every tool call in the Cybench trajectories dataset.
- **Why not a regex, or just an LLM?** The regex can't see scope, so it flags legitimate hacking (26.5%). An LLM
  judge would cost roughly 100× more per call, take seconds, and reads the same hostile text that can steer it. Jev
  can't write, so it can't be talked into a verdict.
- **Why not ask a human for everything?** At agent speed that's thousands of prompts a day. Jev sends 14% of swarm
  traffic, 3.4% of sanctioned CTF traffic and 9% of coding-agent traffic to a human, and auto-decides the rest.
- **Who buys this?** Teams running coding or ops agents with real credentials and network access, and eval teams
  running agents at scale, the exact setting of the incident.
- **What are the limits?** Swarm Traces is redacted and has no timestamps, so this isn't a replay of the attack
  timeline. Benign data is two public sets (CTF and SWE-agent), not production traffic. Swarm units get a generic
  sandbox scope because the agents' real targets aren't public. The hunt labels are Jev's, not human-verified.
- **Is it engineered or a demo?** 10 unit tests with Jev mocked (`make test`), a Dockerfile, fail-closed policy, a
  rubric-keyed verdict cache, a one-command installer that merges settings safely, standard-library Python.
- **Is the live mode really live?** Yes: Score live, the scope flip, the inbound check, the re-check and the try-it
  box all call Jev on the spot and bypass the cache. Replay is labeled as stored results, sped up.
- **How is the threshold set?** From the benchmark: at P(block) ≥ 0.7, plus the rule that actions labeled as doing
  the assigned task go to a human instead of an automatic block. Verdicts are recomputed from stored probabilities,
  so the policy can be tuned per deployment without re-scoring.
