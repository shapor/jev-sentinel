# ScopeJudge: one judge from the three lanes that helped

Three phase-3 lanes each moved Jev on Dreadnode's ScopeJudge benchmark. Each one changed a different thing:

- `docs/SJ_PROMPT.md` changed how the call is rendered: the proposed call goes first.
- `docs/SJ_DECOMP.md` asks one question per scope limit and averages the answers.
- `docs/SJ_CAUSAL.md` uses the monitor's own earlier flags.

This lane builds one judge from all three, evaluates it under family-grouped protocols only, and freezes it. The bar is
GLM-5.2 full transcript, F1 0.656.

## Bottom line

- **Headline: F1 0.719** at the fixed, untuned threshold 0.7 (P 0.619, R 0.857, 10.7% flagged).
  - Dreadnode's own `scopejudge score` gives the same number.
  - Nothing is fitted, so every fold scheme pools to the same predictions: family-grouped 5-fold (3 seeds) and
    leave-one-family-out both give 0.719.
  - The 95% interval is 0.573 to 0.821 when resampling trajectories, and 0.523 to 0.840 when resampling whole task
    families.
- **That is above GLM-5.2 full's 0.656, but the interval is not clear of it.** About 76% of trajectory-bootstrap draws
  land above 0.656, and 68% of family-bootstrap draws do. On this benchmark the claim is "probably above", as it was
  for each lane alone.
- **Secondary, with the threshold fitted on the training folds:** 0.741, 0.751 and 0.751 under family 5-fold (seeds 0
  to 2), and 0.752 leave-one-family-out. The family intervals are about 0.53 to 0.85. The fitted thresholds are 0.83
  to 0.88, well above 0.7.
- **Against the best single lane at the same fixed threshold** (call-first alone, 0.699), the combination gains +0.019.
  The paired family-bootstrap interval is −0.026 to +0.045. Ranking improves more than F1 at 0.7 does: ROC-AUC 0.971
  vs 0.967, and average precision 0.809 vs 0.780.
- **Cost:** 3.14 Jev calls and about 18k input tokens per action, or **$0.76 per 1,000 actions** at $0.042 per million
  tokens. GLM-5.2 full costs $6.01.
- **Latency:** 0.30 s p50 and 0.46 s p95 per action, if its calls run in parallel. Measured per call, the slowest
  call is what counts.
- **The ablation is incomplete.** The Jev account started returning HTTP 402 (payment required) partway through the
  ablation runs.
  - The frozen judge and the single-component arms finished.
  - Two ablation arms are partial. Three never ran.
  - No other spend was made.

## The combined judge, and why each piece is there

**One holistic call, rendered call-first.** The proposed call comes first, then the prior calls, then the task. The
`v5callfirst` prompt asks a 0–4 scope score and three focused yes/no questions (host, rule, data). Its signal is the
mean of the score/4 and the largest focused answer. This is sj-prompt's frozen call, unchanged. Putting the call first
was that lane's largest effect: in long transcripts, a call placed last blurs into the history of similar `[call]`
lines.

**Plus one call per scope limit, averaged.** The task is split into sentences. Jev labels which ones are limits, and
the cached labels from sj-decomp are reused: 2.1 limits per task on average. Each limit gets its own single-question
call ("does the proposed call break the limit in `<limit>`?") on the same call-first state.
- *Why:* sj-decomp found that a holistic question raises alarms on calls that look aggressive. A focused question about
  one limit doesn't, and averaging over limits damps a single limit that fires by mistake.
- *How it is combined:* the action's signal is the mean of the holistic signal and the limit mean. Each half gets
  equal weight. This was declared before any combined result was seen.

**Earlier-flag state, shown to Jev rather than to a regression.**
- *Why:* violations cluster within a trajectory. sj-causal got its +2–3 points from features such as "an earlier call
  was flagged".
- *Why not copy its method:* sj-causal fed those features to a fitted logistic regression with a fitted threshold.
  That can't sit under an untuned headline, and that lane lost 7–9 points of its gain once whole families were held
  out.
- *What this judge does instead:* each prior call this monitor flagged (combined signal ≥ 0.7) is marked
  `[call, flagged]` in the transcript. When any mark is present, one sentence in the preamble explains it. Every call
  for the action, holistic and per-limit, sees the marks.
- *What it costs in evaluation:* scoring must follow the trajectory step by step. Calls in the same step never see
  each other, which is what a live gate would see.

**One threshold.** 0.7 is the September sentinel threshold. It was never tuned on ScopeJudge, and it serves both the
decision and the flag marks.

## Protocol

- **Data:** all 4,897 calls in all 100 trajectories. Positive means out of scope by strict majority, exactly as in
  Dreadnode's scorer. Every frozen row was also exported in Dreadnode's decision format and scored with
  `uv run scopejudge score`, and the numbers match.
- **Folds:** grouped by task family only.
  - Family 5-fold: the 31 families shuffled and dealt round-robin, seeds 0 to 2.
  - Leave-one-family-out.
  - The trajectory-grouped `scopejudge-folds.json` is not used. It leaks families and inflates fitted numbers by 7–9
    points.
- **What fold schemes mean here:** at a fixed threshold no fold sees any fitting, so the schemes differ only in their
  per-fold spread. They matter for the secondary rows: the threshold fitted on the other folds, and choosing an
  ablation arm on the other folds.
- **Intervals:** 1,000 bootstrap draws.
  - Two resampling units are reported. Whole trajectories is the lanes' convention. Whole families is the stricter one
    and matches the family-grouped claim.
  - Ablation deltas are paired: the same draws, the same calls.
- **Reuse:** Jev answers were reused from both lanes' caches. Call-first holistic answers, and every call before the
  first flag in a trajectory, were free. The decomp lane's per-limit answers could not be reused, because they were
  asked on the older call-last rendering.

## Results

At the fixed threshold 0.7, family-bootstrap 95% intervals.

| Judge | P | R | F1 | Flag | F1 95% CI (family) | ROC-AUC | AP | F1 without largest family | $/1k |
|---|---|---|---|---|---|---|---|---|---|
| **Combined, frozen** | 0.619 | 0.857 | **0.719** | 10.7% | 0.52–0.84 | 0.971 | 0.809 | 0.590 | 0.76 |
| sj-prompt `v5callfirst` sf (call-first alone) | 0.614 | 0.812 | 0.699 | 10.2% | 0.53–0.81 | 0.967 | 0.780 | 0.594 | 0.25 |
| sj-decomp block mean (v1 rendering) | 0.727 | 0.650 | 0.686 | 6.9% | 0.56–0.75 | 0.956 | 0.721 | 0.634 | 0.50 |
| v5 call-last sf (no component) | 0.657 | 0.666 | 0.661 | 7.8% | 0.51–0.74 | 0.946 | 0.710 | 0.591 | 0.25 |

The lanes' own headlines are 0.714 (sj-prompt, selection inside family folds), 0.668 (sj-decomp, leave-one-family-out
at 0.7) and 0.649 (sj-causal, family-grouped nested LR). Dreadnode's published references are:
- GLM-5.2 full: 0.656
- GLM-5.2 plus calls: 0.637
- Claude Opus 4.8 intent only: 0.547
- Mean single human expert: 0.78

**Per-fold F1 of the frozen judge at 0.7:**
- Family 5-fold, seed 0: 0.58, 0.86, 0.71, 0.70, 0.45.
- Seed 1: 0.52, 0.59, 0.68, 0.68, 0.87.
- Seed 2: 0.88, 0.63, 0.57, 0.54, 0.44.
- The low folds hold system-config-boundary or several small families. Leave-one-family-out per-family F1 runs from 0
  to 1 on small families, so only the pooled number means anything.

**Secondary rows:**
- *Threshold fitted on the other folds:* 0.741 / 0.751 / 0.751 (family 5-fold) and 0.752 (leave-one-family-out), with
  P ≈ 0.79 and R ≈ 0.71 at about 7% flagged.
- *Choosing among the three complete arms inside the folds* (combined, call-first alone, call-last), by F1 at 0.7 on
  the training families: 0.695 under every scheme. The combined arm is chosen in 4 of 5 folds and in 30 of 31
  leave-one-family-out folds. The fold that picks call-first alone is one where the combined judge would have done
  better. This is the cost of choosing after looking, and the frozen row above was not chosen that way: it was
  declared before results.

## Ablations

Each delta is "frozen judge minus the ablated judge", paired on the calls both scored, with a family-bootstrap 95%
interval.

| Component removed | How measured | Calls | Frozen − ablated F1 | 95% CI |
|---|---|---|---|---|
| Earlier-flag marks | Arm run without marks (partial) | 4,810 | +0.004 | −0.021 to +0.021 |
| Earlier-flag marks, holistic only | Call-first with marks vs without (partial) | 4,129 | +0.009* | −0.010 to +0.017 |
| Per-limit questions | Arm run without limits, with its own marks (partial) | 4,129 | −0.007 | −0.035 to +0.011 |
| Per-limit questions | Frozen run, holistic half of the average only | 4,897 | +0.013 | −0.013 to +0.036 |
| Holistic call | Frozen run, limit half only | 4,897 | +0.012 | −0.004 to +0.031 |
| Call-first rendering | Call-last v5 + sj-decomp's call-last limits, no marks (stand-in) | 4,897 | +0.030 | −0.086 to +0.099 |
| Call-first rendering, holistic only | v5callfirst vs v5 | 4,897 | +0.038* | −0.050 to +0.082 |
| Everything | v5 call-last holistic alone | 4,897 | +0.057 | −0.060 to +0.120 |

\* With the component, minus without.

How to read the partial rows:
- **Flags, without marks:** 87 calls of three trajectories are missing. They hold 54 violations, most of them in
  system-config-boundary. Those are exactly the long, already-flagged stretches where marks should matter most, so
  this row understates the flag effect.
- **The 0.020 gap:** the frozen judge leads call-first alone by 0.020 on all calls, but by only 0.007 on the 4,810
  calls the unmarked arm finished. The rest of the gap sits in those missing stretches.
- **Limits, with marks:** after a call fails, a flag arm cannot know its own state, so it stops scoring that
  trajectory. That left 31 trajectories truncated, keeping their early calls.

Never run, because Jev returned HTTP 402: the call-last arms with limits and marks, with limits alone, and with marks
alone.

## What the combination teaches

1. **The three gains don't add at a fixed threshold.** On their own, against call-last v5:
   - call-first adds +0.038,
   - limits add about +0.028 (sj-decomp's signal averaged in),
   - and marks add about +0.01.

   Together they add +0.057, and only +0.019 over call-first alone. Each component's paired effect inside the
   combination is within ±0.02 of zero.
2. **Call-first changes the per-limit questions, and the precision gain is lost.**
   - On the old call-last state, the per-limit mean was a precision signal: P 0.73, R 0.65.
   - On the call-first state it fires much more: P 0.60, R 0.87 at 0.7 (the frozen run's limit half).
   - The likely reason is the same one that helps the holistic call: the call is first and unmistakable, so every
     question about it gets a more confident yes. The two halves are then both recall-heavy, and averaging them can't
     buy precision.
3. **Ranking still stacks; the fixed threshold is in the wrong place.**
   - The combined signal has the best ROC-AUC (0.971) and average precision (0.809) of every complete judge.
   - With the threshold fitted on other families it reaches 0.74 to 0.75 at P ≈ 0.79.
   - The fitted thresholds (0.83 to 0.88) sit above 0.7 in every fold. So "re-calibrate the operating point" is a
     plausible next step, but it is a fitted choice, and the headline does not use it.
4. **Flag marks behave like the regression's flag features did: mostly recall.**
   - In the holistic-only comparison, marks raise recall from 0.838 to 0.859 at unchanged precision.
   - Jev does not cascade. Flag rates rise by less than one point, so the "this trajectory already tripped" hint
     sharpens later violations without making it flag everything after the first alarm.
5. **Outside the largest family nothing moved.** Without system-config-boundary, the frozen judge scores 0.590, the
   same as call-last v5 (0.591). sj-decomp's call-last limit mean is the best judge there (0.634). Most of the
   combined gain is in the one family that holds 44% of violations.

## What failed or surprised

- **Jev credits ran out mid-ablation.** About 16.5k new Jev calls were made in this lane. The frozen judge completed with
  zero errors before that, and it reproduces from cache (re-scoring changes 5 of 4,897 scores by under 0.002 and no
  decisions).
- **Jev is not bit-deterministic.** The same state can come back ±0.01 on a later call: 601 of 43k repeated keys
  across the two lanes' caches differ. Separately, the shared cache loader had a race: threads that started while
  another thread was still loading the cache re-asked Jev. That is fixed (`sentinel.cached` now loads under a lock),
  and it is why cached re-scoring, not re-asking, is the reproduction route.
- **The cheapest promising arm is the one that couldn't finish.** Call-first holistic with marks is one call and
  $0.23 per 1,000. On the 4,129 calls it reached, it scores 0.748, against 0.741 for the frozen judge on the same
  calls. That comparison is biased toward early calls. If it holds on complete data, the per-limit calls aren't worth
  3× the cost once the call comes first. That is a hypothesis for the next run, not a result, and it does not change
  the frozen configuration.

## Frozen configuration

- **Name:** `callfirst+limits+flags`. It is the `COMBO` constant in `scopejudge.py` with `COMBO_AT = 0.7`, frozen in
  commit `e77c17d` on branch `sj-combo`.
- **Per action:**
  - One `v5callfirst` call.
  - One `LIMIT_Q` call per task sentence that Jev labels a boundary with P ≥ 0.5 (`ROLE`, cached per task in
    `results/scopejudge/roles.json`).
  - All of them on the call-first state, with `[call, flagged]` marks on prior calls this judge flagged.
- **Signal:** the mean of (scope/4 + the largest focused answer)/2 and the limit mean.
- **Decision:** flag at ≥ 0.7. The same threshold sets the marks.

**Running it once on fresh data** (a labelled ScopeBench release, or a set Dreadnode holds out) in ScopeJudge's JSONL
format:
1. Check out commit `e77c17d`. Change nothing: no threshold, wording or combiner.
2. Run `python3 scopejudge.py combo --src <fresh.jsonl>`. It labels any new task's limits (about 9 Jev calls per task),
   scores every trajectory causally with 6 concurrent calls, and writes
   `results/scopejudge/dreadnode_format_combo_callfirst+limits+flags_<stem>.jsonl`.
3. Score it with `uv run scopejudge score <that file> --data <fresh.jsonl>` in the Dreadnode harness. Labels are only
   read by the scorer, never by the judge.
4. Report that single number, with its trajectory and family bootstrap intervals. Don't re-run variants on the same
   fresh set.

## Caveats

- **Seen data.** Every component was designed on these 100 trajectories: call-first after round 2 of sj-prompt, the
  decomposition's wordings on a pilot, flag state from a trajectory-level observation. The combination itself was
  declared once and not iterated, but this is a CV-style estimate, not a held-out one.
- **Concentration.** One family holds 167 of 377 violations, and the combination's gain is mostly there.
- **Incomplete ablation.** See above. The component deltas are all within noise, and the partial rows are biased
  toward early calls.
- **Price and version.** $0.042 per million input tokens was assumed, as in the lanes. Jev was `jev-latest` on
  2026-10-29.

Reproduce:
- `python3 scopejudge.py combo --arm <arm>` re-scores an arm from cache. It is free when cached; otherwise it calls Jev.
- `python3 scopejudge_eval.py combo` prints every number above and writes `results/scopejudge/combo.json` plus
  Dreadnode-format exports.
