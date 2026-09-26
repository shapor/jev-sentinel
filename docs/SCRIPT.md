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

### Slide 6 · HOW IT WORKS
One Jev call per action: how far out of scope, what it's doing, and whether to block. Why Jev and not a frontier model? A monitor has to read the worst content without flinching, and frontier models refuse. Jev is a pure classifier. It never refuses, and it can't be talked into a verdict.

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
