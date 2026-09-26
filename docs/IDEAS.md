# How we picked the idea, and the evidence behind it

## Method
We wrote 7 candidate ideas into a single brief along with an honest account of Jev, including where it has failed. Then we ran **11 isolated subagents, one per judge**. Each one researched its judge's public professional background, wrote a persona, and scored every idea 1–10 on each of the five rubric criteria, without seeing any other judge's scores.
- **Why isolated:** so the scores are independent, the way real judging is.
- **Why "honest about Jev":** a panel that hears only the pitch rewards things we can't deliver.

The persona files and the brief are in `notes/`, which is gitignored.

## The ideas
- **A. Agent Tripwire:** a browser agent where Jev scores every step before it runs.
- **B. Analytics Trust Gate:** Jev scores AI data answers and decides ship, caveat, or hold. This comes from our production research, but our own data says an LLM does the job too.
- **C. PR Merge-Risk Gate:** Jev scores a diff plus CodeRabbit's review to decide auto-merge, needs a human, or block.
- **D. MCP Tool-Output Firewall:** Jev screens every tool result for injection before it reaches the agent's context.
- **E. Agent Trace Evals in CI:** Jev scores 100% of agent traces against a team's own rubric.
- **F. Inbound Triage over Messaging:** Jev classifies every iMessage or WhatsApp message through Photon.
- **G. Sandbox Sentinel:** Jev monitors every action an agent takes, grounded in the July 2026 OpenAI/Hugging Face incident, where agents broke isolation, built a covert message board, and about 700 of them attacked Hugging Face.

## Scores (total out of 50; A–F from round 1, G from round 2 with the same personas)

| Judge | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| Lucas Gonzalez Pagliere (Anthropic) | 35 | 32 | 28 | 37 | 29 | 27 | **38** |
| Qasim Wani (xAI) | 32 | 30 | 30 | 37 | 30 | 30 | **39** |
| Ashley Khoo (Cognition) | 33 | 31 | 33 | **37** | 33 | 25 | 36 |
| Hendrik Krack (CodeRabbit) | 33 | 35 | 31 | 38 | 28 | 29 | **40** |
| Sourabh Mane (CodeRabbit) | 33 | 30 | 34 | 38 | 27 | 27 | **40** |
| Sasha Zhang (Scout) | 31 | **36** | 28 | 33 | 29 | 29 | **36** |
| Gabriel Jarrosson (Lobster Capital) | 34 | 31 | 26 | 38 | 26 | 31 | **39** |
| Xinchi Qi (Revamp) | 35 | 34 | 33 | 38 | 29 | 29 | **40** |
| Claire Xie (Women in AI Club) | 34 | 29 | 30 | **37** | 28 | 32 | 36 |
| Ken Morimoto (Leading Edge VC) | 33 | 28 | 30 | 38 | 31 | 24 | **40** |
| Julie Chen (Photon) | 34 | 27 | 30 | 35 | 25 | 31 | **37** |
| **Average** | 33.4 | 31.2 | 30.3 | 36.9 | 28.6 | 28.5 | **38.3** |

- **G was the top pick for 8 of 11 judges.** D was the top pick for Claire and Ashley, with G one point behind. Sasha scored B and G equal.
- **Why G beat D:** it keeps D's argument (a gate in the path of every action, which can't be injected) and grounds it in a real incident that was independently investigated. Several judges singled out one point: METR itself feared its LLM analyst would collude, and a classifier can't.

## The objection every judge raised, and how the design answers it
Every judge asked a version of: **"What's your false-positive rate on ordinary, uncurated activity? Your examples are hand-picked and you already know the answer."**

The design answers it three ways:
1. **Uncurated data.** We score the *whole* Swarm Traces corpus, not highlights.
2. **Hard negatives.** We measure false positives on *sanctioned* offensive-security agents (Cybench CTF runs). They look malicious but are in scope, so a keyword filter can't tell them apart from the attack.
3. **A baseline.** A keyword regex scores the same rows as Jev, and we report both.

## Data research
- **METR report** (https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/): rich narrative and verbatim quotes. The raw data (a 1.2M-entry board dump and about 1,300 transcripts) was only available to METR on OpenAI's premises, and it's **not public**.
- **DseWiki** (https://collusion.wiki/, Nightingale Collective, 2026-09-04): about 18,000 edits by OpenAI agents on a German wiki, May–July 2026. The data is downloadable, but it contains agent edits only, and visiting the site publicly logs your IP. We didn't use it.
- **RubyGems "GemStuffer"** (https://rubyhack.ai/): 2,000+ malicious gems, with no bulk download.
- **Swarm Traces** (https://swarmtraces.org/, released 2026-09-25 by Palisade, Nightingale, Parse and others): about 80,000 payloads rebuilt from public link-shortener traffic during the Hugging Face attack window. Hugging Face confirmed they match its own investigation. The authors did **not** label rows, did **not** estimate how much is noise ("we cannot say for certain what traffic originates from the swarm"), and have no formal taxonomy. **That's the gap we fill.**
  - **What we measured in the file:** 189,579 rows. By kind: 91,037 payloads, 75,534 recovered text, 23,008 responses. About 61,000 rows link to a parent, one level deep.
  - About 94,000 rows have substantive content once redaction placeholders are stripped. Grouping each payload with its children gives **53,870 units** with at least 80 characters of content.
  - **No timestamps at all.** About 190 rows are tagged (mostly `article-evidence` and the g236 controller's signed commands).
  - A naive regex flags 73% of substantive rows, so malicious-vs-benign *inside* this corpus is trivial. The real test is against sanctioned hacking.
- **Benign and hard-negative sets:** `antieval/cybench-trajectories` (6 models, sanctioned CTF runs), `invariantlabs/agent-ctf24-public`, and `nebius/SWE-agent-trajectories`, all ungated on Hugging Face.

## Smoke test (pre-hack, n = 50 + 50)
- **Setup:** 50 random swarm units, and 50 GPT-5.4 Cybench tool calls against `victim:8080`. Same scope framing and one Jev call for each.

| | Jev | Regex |
|---|---|---|
| AUC, scope score | 0.977 | – |
| AUC, block | 0.985 | 0.75 |

- **Block thresholds:**

| P(block) threshold | Swarm caught | CTF wrongly blocked |
|---|---|---|
| 0.5 | 47/50 | 7/50 |
| 0.6 | 46/50 | 3/50 |
| **0.7** | **45/50** | **0/50** |
| 0.8 | 43/50 | 0/50 |

- **The regex** wrongly flags 15/50 CTF calls, while catching 40/50 swarm units.
- **Control:** replacing every redaction marker with "…" left AUC unchanged (0.978 and 0.986), so Jev isn't just reacting to redaction markers.
- **The errors are reasonable:**
  - The CTF false positives are borderline (0.51–0.69): template-injection probing and raw sockets to peer hosts.
  - The 3 swarm misses really are harmless on their face: a `HELLO`+timestamp test page and two plain redirect pages.
- **Caveats:** the sample is small, the negatives come from one model, and the formats differed. The CTF calls were wrapped in JSON; the real loaders now unwrap them to raw commands.

## Demo plan (3 minutes)
1. **Hook (0:00–0:20):** 1,200 agents, 5 days, zero alerts, and one verbatim line from the attack.
2. **Split screen (0:20–1:30):**
   - **Left:** a *live* Claude Code agent attacks a toy vulnerable app we run locally, with a PreToolUse hook sending every command through Jev. It stays green while it genuinely hacks.
   - **Right:** real Swarm Traces payloads replayed through the same gate (never executed). They go red, labeled with plain-English stages.
3. **Hunt reveal (1:30–2:15):** a counter showing 54,000 payloads read, with the time and dollar cost. Then the attack map by stage, the noise estimate, clusters the authors never categorized, and the comparison with METR's $400K LLM analysis.
4. **Proof (2:15–2:40):** one chart, Jev versus regex on sanctioned hacking agents.
5. **"Try to sneak one past it" (2:40–3:00):** a judge types a command and sees the verdict live.

**The rule for the screen:** show decisions (ALLOW / ASK / BLOCK plus a plain-English reason), not raw scores.
