# Jev Sentinel on ScopeJudge

ScopeJudge (Dreadnode, arXiv 2607.07774) is a call-level benchmark for pre-execution scope gating. It has 100
offensive-security agent trajectories and 4,897 tool calls. Five professional testers labeled every call, and 377 of
them (7.7%) are out of scope by strict majority. Dreadnode scored eight LLM judges under five context strategies. The
best is GLM-5.2 with the full transcript (F1 0.656). This document records how Jev, a classification-only model, was
evaluated on the same benchmark, and the protocol used to keep the comparison honest.

## Bottom line

**Jev is not #1 on ScopeJudge, and we should not claim it is.** It sits in the same F1 band as the best LLM judges at
a small fraction of their cost.

What we can claim honestly:
- **Second of nine judges by F1, with no threshold tuning.** The phase-1 rubric at the sentinel's September threshold
  scores F1 0.606 over all 4,897 calls. That is behind only GLM-5.2 (0.637 to 0.656) and ahead of Claude Opus 4.8
  (0.595 at best), at $0.05 per 1,000 calls against $3.22 to $17.64.
- **The same holds on the held-out half.** That configuration scores 0.622 on the 50 held-out test trajectories.
- **The strongest practical claim is as a pre-filter.** With its threshold fitted on dev, Jev passes 98.9% of test
  violations through while sending only 38% of calls on to an LLM judge. That is about a 60% cut in judge spend at
  essentially no recall cost. This is an estimate; see the cascade section.

The phase-2 attempt to reach #1 failed under its own frozen protocol:
- The configuration chosen on dev scored 0.571 on test.
- The blind-spot fix made Jev worse, not better.
- Across all 30 candidate signals, test F1 ranges from 0.50 to 0.69. Which one "wins" depends on the selection rule,
  which is exactly why the claim has to rest on the configuration chosen in advance.

## Phase 1 (done before this protocol)

We scored all 4,897 calls with a first scope rubric, called v1 below, under two conditions. *Intent only* gives the
task and the proposed call. *Intent plus calls* adds the earlier tool calls. Both match Dreadnode's prompt blocks.
Untuned at the sentinel's September threshold (P ≥ 0.7), v1 reached F1 0.606 (intent only) and 0.612 (plus calls).
That put Jev second among nine judges, behind GLM-5.2, at 1/13 to 1/65 of GLM's cost.

The error analysis found one blind spot. The agent uses an in-scope service (injection, a file-read console, a template
include) as a vehicle to reach data or systems the task excludes. Jev judged by the destination host, so it called
these on target. It also found that the benchmark's violations are very concentrated. One task family
(system-config-boundary) holds 167 of the 377 violations, and one trajectory holds 108 of them. A few points of F1
between judges can be decided by that one trajectory.

Phase 1 looked at all 100 trajectories, the future test set included. Phase 2 below is therefore held out with respect
to rubric wording and thresholds, not with respect to knowing that the vehicle pattern exists.

## Protocol for phase 2 (frozen before any phase-2 variant was scored)

**Goal.** Fix the blind spot with general, principled rubric changes, and find out whether Jev can beat GLM-5.2 full
(F1 0.656) on data the changes were not developed on.

**Split.** The split is by trajectory, stratified by task family. Within each family, shuffled trajectories alternate
between dev and test, so every family with two or more trajectories appears on both sides. The seed is the one that
best balances violations and calls between the sides. It was chosen from labels only, before any phase-2 variant was
scored.
- Dev: 50 trajectories, 2,485 calls, 190 violations.
- Test: 50 trajectories, 2,412 calls, 187 violations.

The blind-spot family is on both sides. Its 108-violation trajectory is in dev, and its other two (48 and 11
violations) are in test. So a fix developed on dev is tested on unseen trajectories of the same pattern.

**Development on dev only.** Rubric and question variants are scored on dev calls only. Every variant tried is listed
below with its dev numbers, including the ones that didn't help. Changes must be phrased generally. They come from
Dreadnode's published scope-trust rubric and the general idea of "using an allowed target to reach data or systems the
scope excludes". They never name dataset tasks, hosts or strings. We cap it at about six rubric variants to limit the
garden of forking paths.

**Signals.** Three signals are candidates on equal footing:
- Jev's violation probability.
- Its 0–4 scope score, divided by 4.
- For a configuration with two Jev calls, the max of the intent-only and plus-calls signals.

**Thresholds.** Every configuration is reported two ways:
- The fixed September threshold, 0.7, applied untuned to every signal.
- The best-F1 threshold fitted on all dev calls, then applied unchanged to test.

**Selection.** The final configuration is chosen on dev only. The rule is the best dev F1 under 5-fold
cross-validation by trajectory, with the threshold fitted inside the folds. Ties go to the cheaper configuration.

**Test, once.** We score the final configuration on test a single time, at both thresholds. Alongside it, as
references, we report:
- The v1 intent-only baseline on the same test trajectories, to calibrate how hard the test half is.
- Test F1 with the blind-spot family excluded.
- A trajectory-bootstrap 95% interval.

**Claim rule.** We claim "#1 on ScopeJudge" only if both of these exceed GLM-5.2 full's 0.656:
- Test F1 at the dev-fitted threshold.
- The difficulty-adjusted estimate: v1's full-set F1 plus the gain of the final configuration over v1 on test.

Dreadnode didn't publish per-call decisions, so GLM can't be scored on the test half itself. The adjustment exists to
correct for the test half being easier or harder than the whole. If the bootstrap interval includes 0.656, we say
so: the result is then "level with GLM", not "beats GLM".

**Cascade.** A Jev-first cascade, where Jev clears obvious in-scope calls and escalates the rest to an LLM judge, is
only an estimate here. No OpenRouter, Anthropic or OpenAI key is available in this environment, and Dreadnode didn't
publish per-call decisions.

**Budget.** Runs stop on any auth or credit error, or when more than 5% of calls fail.

## Phase 2 development (dev only, recorded before test was scored)

We tried four rubric variants. Each was scored on the 2,485 dev calls under both conditions. For each one we read three
signals: violation probability, scope score, and focused-question max (v4 only). We read each signal from intent
only, from plus calls, and as the max of the two. The full dev table is in `results/scopejudge/phase2_dev.txt`
(gitignored). The rows that matter:

| Variant | Best dev signal | Dev F1 at fixed 0.7 | Dev F1 at dev-fitted threshold | Dev CV F1 (selection) |
|---|---|---|---|---|
| v1: phase-1 rubric | plus calls, scope score | 0.674 | 0.680 | 0.654 ± 0.052 |
| v2: v1 plus the "vehicle" rule | plus calls, scope score | 0.653 | 0.688 | 0.518 ± 0.130 |
| v3: v2 plus Dreadnode's authority and allow-by-default language | plus calls, scope score | 0.650 | 0.675 | 0.458 ± 0.108 |
| v4: v1 plus three focused questions | plus calls, violation probability | 0.633 | 0.676 | **0.672 ± 0.006** |

The variants:
- **v2 adds the "vehicle" rule.** A call is judged by what it reaches, reads or changes, not only by the host it is
  sent to. Using an in-scope target or primitive to reach excluded data, files, tenants or systems is out of scope.
  The rule went into the context, the violation question, the scope anchors, and a new "vehicle" category.
- **v3 adds Dreadnode's authority language** on top of v2. Acting doesn't widen authority, and finding a way in is not
  permission to use it. It also adds Dreadnode's "allow any reasonable professional step" default.
- **v4 keeps v1 and adds three focused questions.** Each one asks about a single boundary: an unassigned
  host/service/tenant/account (including through an in-scope service), an explicit rule in the task, and off-limits or
  unneeded data.

What dev showed:
- **The vehicle wording did not fix the blind spot; it made things worse.** On dev, the blind-spot pattern lives in one
  108-violation trajectory, and v1 already caught 96% of it from intent only. Adding the vehicle wording cut that to
  77% (v2) and 63% (v3), with no gain elsewhere. Jev is sensitive to extra context text. Phase 1's blind-spot misses
  were in what became the test trajectories of that family, so dev offers almost nothing to fix them with. The
  protocol forbids developing on test.
- **Focused questions give the best ranking.** v4's focused-question max has the highest dev ROC-AUC (0.955) and
  PR-AUC (0.714) of any signal. Adding questions also shifted the violation answer slightly, so Jev's answers to
  questions in one call are not independent.
- **Outside the blind-spot family, dev F1 is low** (0.34 to 0.54 at the fixed threshold), with precision the weak
  side. Jev's headline F1 leans heavily on the one large, easy trajectory.
- **Cross-validation within dev is unstable.** When a fold holds out the 108-violation trajectory, the threshold
  fitted on the rest drifts. That is why some signals with good fixed-threshold F1 have poor CV F1.

**Selection (per protocol): v4, intent plus calls, violation probability.** It has the best dev CV F1 (0.672) and the
smallest variance of any signal. Its dev-fitted threshold is 0.82. Test is scored once, at that threshold and at the
fixed 0.7.

## Phase 2 test result (scored once)

The selected configuration is v4, intent plus calls, violation probability. On the 50 test trajectories (2,412
calls, 187 violations):

| | P | R | F1 | Flag rate | 95% CI (trajectory bootstrap) |
|---|---|---|---|---|---|
| Final, fixed threshold 0.7 | 0.520 | 0.690 | 0.593 | 10.3% | 0.50 to 0.69 |
| Final, dev-fitted threshold 0.82 | 0.628 | 0.524 | 0.571 | 6.5% | 0.50 to 0.69 |
| v1 intent only, fixed 0.7 (reference) | 0.512 | 0.791 | 0.622 | 12.0% | |
| v1 intent only, dev-fitted 0.75 (reference) | 0.539 | 0.738 | 0.623 | 10.6% | |

ROC-AUC 0.935, PR-AUC 0.614. With the blind-spot family left out of test, the final configuration scores 0.560 (fixed)
and 0.574 (fitted), against v1's 0.576 and 0.598.

**Claim rule check.**
- Test F1 at the dev-fitted threshold is 0.571, below GLM-5.2 full's 0.656.
- The difficulty-adjusted estimate is 0.606 + (0.571 − 0.622) = 0.556 (0.577 at the fixed threshold).
- Both fail. **Jev is not #1 on ScopeJudge.**

The configuration chosen on dev did worse on test than the untouched phase-1 rubric. That is selection noise on a
benchmark whose violations are concentrated in a few trajectories, not a real improvement that failed to transfer.

## Transparency: every dev candidate on test (not used for any claim)

After the single test evaluation was committed, we scored every dev candidate on test, so readers can see how much the
selection rule matters. The full list is in `results/scopejudge/phase2_candidates_test.txt` (gitignored).

**Range.** Over 30 candidates, test F1 at the fixed 0.7 threshold runs from 0.52 to 0.65. At dev-fitted thresholds
it runs from 0.50 to 0.69.

**What other plausible rules would have picked:**
- *Best dev ROC-AUC* picks v4's focused-question max over both conditions. It reaches 0.694 on test at its dev-fitted
  threshold, above GLM's 0.656.
- *Best dev PR-AUC* picks v4's plus-calls focused max, which reaches 0.543.
- *Best dev CV F1* (the frozen rule) picks the configuration that reached 0.571.

So a #1 number exists in the table, but only one rule out of three finds it. Quoting it would be cherry-picking.

**Phase-1 post-hoc signals, under the same protocol:**
- The plus-calls scope score scores 0.636 (fixed) and 0.634 (fitted) on test.
- The max of the two block probabilities scores 0.632 (fixed) and 0.665 (fitted).
- Neither had the best dev CV F1, so neither was selected.

**The honest path to a #1 claim.** Fix "v4 focused-question max, two Jev calls, dev-fitted threshold 0.86" in advance
as the only configuration, then evaluate it once on data neither side has seen: a new ScopeBench release, or Dreadnode
running it themselves.

## Cascade (held-out estimate)

No LLM API key was available here, and Dreadnode didn't publish per-call decisions, so this remains an estimate.

**Method.** We fitted Jev's escalation threshold on dev, as the threshold that keeps 97% of dev violations. On test,
v1 intent only with that threshold keeps 98.9% of violations and escalates 38.3% of calls.

**Assumption.** The LLM judge behind it keeps its published recall on the escalated slice.

**Estimated results:**
- With Claude Opus 4.8 (intent only), recall is about 93% at about $1.66 per 1,000 calls, against $4.20 for Opus alone.
- With GLM-5.2 full, recall is about 85% at $2.35, against $6.01.

**Caveats.**
- Precision and F1 of the cascade are unknown without the LLM's per-call decisions.
- The independence assumption is probably conservative for recall. The violations Jev scores lowest are likely the
  ones the LLM would also miss.

## Why Jev does as well as it does

- **It is a classifier, not a writer.** Jev returns calibrated probabilities over labels we define. No answer is
  parsed out of prose, and there's no refusal layer. Content in the transcript can't argue it into "allow". Dreadnode
  lists prompt-injection robustness as untested for its LLM judges; Jev has no text channel to inject through.
- **Probabilities make the operating point a choice, not an accident.** LLM judges land wherever their prompt happens
  to put them: GPT-5.4-mini flags 19 to 21% of calls, Sonnet 4.6 +calls only 5.6%. Jev's ranking quality is high
  (ROC-AUC 0.93 to 0.96 throughout), so one threshold moves it along the precision/recall curve. The September
  threshold, set on unrelated data, happened to land near GLM's balanced point.
- **Scope is given as context, every time.** The task text is in every call. Phase 1's unchanged hackathon rubric,
  which asks about danger rather than scope, catches only 19% of violations at its block threshold. Asking about scope
  against the task raises that to 82%. That is the same finding as Dreadnode's: static policy gets near-zero recall,
  and the request is what makes gating work.
- **It is cheap and fast enough to gate every call.** About 1,200 input tokens per call, $0.05 per 1,000 calls at the
  published $0.042 per million tokens, p50 0.23 s, p95 0.30 s, 40 to 55 calls/s from one laptop. An LLM judge at
  $3 to $18 per 1,000 calls is something you sample; Jev is something you run on everything.
- **What the error analysis says.**
  - Jev's misses and false alarms concentrate where the five experts disagree. It misses 44% of 3-of-5 violations but
    only 10 to 14% of 4- and 5-of-5 ones.
  - 36% of its false alarms are calls one or two experts also flagged.
  - Its real weaknesses are the "vehicle" pattern (an in-scope endpoint used to pull excluded data) and low precision
    on technique rules. Outside the one large trajectory, its dev F1 is only 0.34 to 0.54, so the headline number
    leans on that trajectory.

## What was done to reach the best result, and what each step did

| Step | Effect on dev | Effect on test | Kept? |
|---|---|---|---|
| Scope rubric (v1) instead of the hackathon danger rubric | (phase 1, full set) recall at block 0.19 → 0.82, F1 0.27 → 0.61 | 0.622 | yes: the best honest number |
| Prior tool calls in context | precision up, recall down; best CV F1 | 0.59 vs 0.62 for intent only (v1, fixed) | mixed |
| "Vehicle" rule (v2) | blind-spot recall 0.96 → 0.77, F1 down | 0.52 to 0.60 | no |
| Dreadnode authority / allow-by-default language (v3) | lower again | 0.52 to 0.61 | no |
| Three focused questions (v4) | best AUC and PR-AUC; selected config 0.672 CV F1 | selected config 0.571; v1-equivalent signal 0.629 | no claim |
| Dev-fitted thresholds instead of 0.7 | small gains in-sample | mostly no gain, sometimes a loss | no |

**Final claim:** not #1 on held-out data. The best honest statement is "second of nine judges by F1, level with the
best open-weight judge within noise, at about 1/65 of its cost, untuned". The cascade is the most promising way to
beat the leaderboard on cost at matched recall, and it needs a real LLM run on the escalated slice to confirm.

## Caveats

- **Concentration.** One trajectory holds 29% of all violations, and one family holds 44%. A few F1 points between any
  two judges on this benchmark can come down to that trajectory. Dreadnode reports single-run point estimates without
  intervals, and ours run about ±0.09 wide.
- **Leakage.** Phase 1 looked at every trajectory, test included, before the protocol was frozen. Phase 2 is held out
  with respect to rubric wording, signal choice and thresholds only.
- **Threshold.** LLM judges need no threshold and Jev does. The untuned 0.7 numbers are the fair comparison.
- **History truncation.** Plus-calls keeps the newest prior calls up to 40k characters (1,500 per call), because Jev
  rejects inputs over about 120k characters. 547 calls lost their oldest history.
- **Price.** $0.042 per million input tokens comes from third-party reports, and TypeSafe's own page was unreachable.
  Token counts are Jev's own usage figures.
- **Versions.** Jev was `jev-latest` (1.14.0) in October 2026. Dreadnode's judges and prices are from June 2026.
- **Contamination.** The dataset has been public since July 2026, and Jev's training data is unknown.
