# JEVATHON: event facts, rules, rubric

The source of truth is the organizers' Notion page. This is our copy so decisions can be checked against the rules without needing the browser.

## Event
- **What:** JEVATHON, the first community hackathon for Jev, by TypeSafe AI × The AI Collective, hosted by CodeRabbit.
- **When:** Saturday 2026-09-26, 10:00–16:00 PT, with a rooftop afterparty until 20:00.
- **Where:** CodeRabbit HQ, 201 Spear St, 12th floor, San Francisco.
- **Agenda:**

| Time | What |
|---|---|
| 10:00 | Doors open |
| 10:30 | Keynote and Jev DevRel talk |
| 11:15 | Team formation |
| **11:30** | **Hacking starts** |
| **14:30** | **Hard stop**, then demos and live judging |
| 15:30 | Awards |

- **Submitting:** register the team and submit on HackerSquad under `./project.sh` **before 14:30**. Late submissions can't be judged. Tool feedback in `./tools+feedback.sh` enters you for an extra prize.

## Participation rules (key points, from the Participation Rules page)
- **Team size:** 2–5. Individuals are welcome but encouraged to form teams.
- **Main track:** "Projects must be built with Jev." Partner tools are encouraged and qualify for sponsor awards.
- **Allowed tools:** any open-source or commercial tools, frameworks and libraries with proper licenses. Pre-trained models are fine, but the project "must demonstrate original application or modification."
- **Original work:** "All submissions must be original work created during the hackathon. Pre-existing projects or unauthorized use of others' work is prohibited."
  - **What this means for us:** no code carried over from qs-app or `experimental`. What we learned there, and public datasets, are fine. The repo's history starts during the event.
- **Public repo:** not required anywhere we read. The CodeRabbit "best use" prize requires a public post.

## Judge rubric (each category scored independently, then discussed)
1. **Problem relevance and real-world value.** A real, recurring problem for a defined user, with evidence that it exists, and value stated in 1–2 sentences. Loses points for abstract demos, novelty apps, or "it's cool."
2. **Technical execution and engineering quality.** Running software end to end, logic beyond prompting, deliberate handling of edge cases. Loses points for mocked flows, hard-coded responses, or manual steps.
3. **Architecture and system design.** Sensible separation of components, AI used where it adds leverage, awareness of latency, cost and scale. Loses points for a monolithic script or pipelines over-engineered for no reason.
4. **Production readiness and feasibility.** A path to deployment, known limits, scope that fits 3 hours. Loses points for fragile hacks or ignoring reliability and security.
5. **Clarity of vision and continuation.** A believable roadmap, conviction, "the start of a real product." Loses points for "built only to win a prize."

**Overall principle:** "working systems over presentations, clarity over complexity, real-world usefulness over novelty … the first version of something real, not the last version of a demo."

## Judges
Ashley Khoo (Cognition), Lucas Gonzalez Pagliere (Anthropic, computer use and agentic systems), Qasim Wani (xAI), Sasha Zhang (Scout, YC), Gabriel Jarrosson (Lobster Capital), Xinchi Qi (Revamp, YC S23), Hendrik Krack (CodeRabbit, the organizer), Claire Xie (Women in AI Club), Ken Morimoto (Leading Edge VC), Julie Chen (Photon), Sourabh Mane (CodeRabbit design engineering). Persona research is in `notes/judges/`, which is gitignored because it profiles real people.

## Prizes
- **Main track (Devin credits from Cognition):** 1st $4,000, 2nd $2,000, 3rd $1,000.
- **CodeRabbit:**
  - $1,000 for the best project built with the CodeRabbit Coding Agent.
  - $500 for the best use of CodeRabbit (you must post publicly).
  - $300 for the most Coding Agent feedback in their Discord.
  - **Free Coding Agent minutes:** sign up at coderabbit.ai, go to Billing → Usage → Agent usage → Redeem Coupon (you must be the workspace billing admin), then enter the coupon ID.
- **GMI Cloud:** $300 for the best use; code `GMIJEV` at console.gmicloud.ai.
- **Other:** Browserbase, Whop and LlamaIndex prizes are still to be confirmed. Photon gives a free month with `HACKWITHPHOTON`. ElevenLabs and Cognition give credits to everyone.

## Links
- Notion: https://app.notion.com/p/coderabbit/JEVATHON-Jev-Hackathon-SF-3e796e76cda18143b74af9944bc5cddc
- Luma: https://luma.com/aic-jev
- Discord: https://discord.gg/NuJMa6VEa (channel #jevathon-at-coderabbit)
- HackerSquad: https://hackersquad.io/builders/dashboard/events/cmuhxoc83006kpl0k7au0d7ro/builder#project
- Questions: hendrik@coderabbit.ai
