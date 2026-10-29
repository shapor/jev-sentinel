# A causal, score-only monitor on ScopeJudge

## Question

Can a runtime monitor that remembers its own earlier verdicts beat the stateless per-call Jev judge on ScopeJudge? A
real gate sees the trajectory up to the current call. It may use earlier calls and its own earlier scores, but never
future calls or labels. Violations cluster: once an agent drifts out of scope it tends to stay out. A monitor that
reacts to its own earlier alarms should therefore gain recall without paying much precision. The target is GLM-5.2
full transcript, F1 0.656. Stateless Jev scores 0.61 to 0.63.

## What the monitor sees

Only signals Jev has already produced, plus one structural bit. No new Jev calls were made.

- **Current-call Jev scores.** These are the violation probability under intent only (v1) and under intent plus calls
  (v1, or v4 in the lean setup). We also use the mean 0–4 scope score of the two conditions, the max of v4's three
  focused questions, and the "off target" mass of the kind distribution (everything but on-target and own-workspace).
- **History of the monitor's own signal.** The signal is max(intent-only p, plus-calls p). From earlier steps we take
  the running max, an EMA (weight 0.3), and the previous step's value.
- **Flag state.** A prior flag means an earlier step's signal reached 0.7, the untuned September threshold. From that
  we take the number of earlier flagged calls (log scale), whether any exists, and the steps since the first flag. Two
  interaction terms let the current score's weight change after a flag. This is hysteresis learned rather than
  hand-set. We also ran an explicit two-threshold hysteresis rule as a variant.
- **Position.** The log of the step index.
- **Other host.** Does the call text name a URL host other than the hosts in the scope text's URLs? This is a plain
  hostname comparison and nothing else.

**Causality.** A call's step index is the number of calls in earlier steps, which is how scopejudge.py builds the
transcript. History uses strictly earlier steps. Calls in the same step never see each other, and the state updates
only after a whole step is scored. No feature touches labels, future calls or tool outputs.

Content-pattern features were tried at the start and dropped by a coordinator decision. They were never evaluated, so
no result here depends on them.

**Combiner.** An L2 logistic regression (λ = 1) fit by Newton's method in plain Python, with eight to fourteen
weights. The F1-maximising threshold is fit on the same training folds.

## Protocol

- The five shared folds (`scopejudge-folds.json`, grouped by trajectory and stratified by family) are used throughout.
- Every weight, threshold and feature-set choice is fit on four folds and applied to the fifth. The fold metrics are
  then pooled over all 4,897 calls.
- The headline rows were exported in Dreadnode's decision format and scored with `uv run scopejudge score`. The
  numbers match ours exactly.
- The 95% interval resamples whole trajectories (1,000 draws).
- "−big" is F1 with the largest family (system-config-boundary, 167 of 377 violations) removed.

The feature set is not picked by looking at the table. The **nested select** row picks among six candidate sets by an
inner 4-fold CV inside each outer training split. Its out-of-fold number is the honest estimate of the whole procedure.

## Results (out of fold, all 4,897 calls)

| Variant | Jev calls | P | R | F1 | Flag | 95% CI | F1 −big | Per-fold F1 |
|---|---|---|---|---|---|---|---|---|
| intent-only p alone | 1 | .514 | .759 | .613 | 11.4% | .46–.74 | .498 | .53 .77 .50 .60 .45 |
| plus-calls p alone | 1 | .659 | .584 | .619 | 6.8% | .50–.70 | .549 | .45 .69 .50 .68 .73 |
| v4 focused max alone | 1 | .695 | .610 | .650 | 6.8% | .53–.73 | .569 | .38 .73 .56 .72 .67 |
| max of the two conditions (rule) | 2 | .547 | .716 | .620 | 10.1% | .49–.73 | .537 | .53 .77 .48 .63 .49 |
| hysteresis rule (two thresholds) | 2 | .551 | .748 | .634 | 10.5% | .48–.77 | .521 | .51 .79 .49 .62 .50 |
| LR, current v1 scores | 2 | .565 | .623 | .593 | 8.5% | .47–.69 | .544 | .50 .72 .43 .61 .51 |
| + history (max, EMA, previous) | 2 | .560 | .605 | .582 | 8.3% | .46–.68 | .518 | .49 .70 .43 .58 .53 |
| + flag state | 2 | .641 | .674 | .657 | 8.1% | .46–.81 | .547 | .48 .82 .35 .73 .61 |
| + history + flag state | 2 | .663 | .658 | .660 | 7.6% | .46–.81 | .555 | .47 .84 .34 .72 .60 |
| + other host | 2 | .621 | .695 | .656 | 8.6% | .56–.73 | .598 | .60 .75 .57 .63 .62 |
| all current scores (v1 + v4) | 3 | .664 | .671 | .668 | 7.8% | .53–.77 | .584 | .49 .78 .51 .75 .63 |
| full (all groups) | 3 | .761 | .703 | .731 | 7.1% | .58–.83 | .621 | .55 .87 .54 .76 .65 |
| **nested select** (3 calls) | 3 | .717 | .727 | **.722** | 7.8% | .57–.83 | .614 | .55 .86 .54 .70 .67 |
| lean, current + host | 2 | .633 | .692 | .662 | 8.4% | .56–.74 | .610 | .61 .77 .54 .64 .62 |
| lean full | 2 | .731 | .692 | .711 | 7.3% | .55–.82 | .604 | .55 .85 .49 .76 .60 |
| lean full without history | 2 | .730 | .719 | .725 | 7.6% | .57–.83 | .616 | .54 .86 .52 .75 .66 |
| lean full without flag state | 2 | .717 | .719 | .718 | 7.7% | .58–.82 | .614 | .52 .84 .58 .68 .71 |
| lean full without host | 2 | .703 | .671 | .687 | 7.4% | .51–.82 | .571 | .47 .83 .46 .73 .63 |
| lean, all current scores | 2 | .655 | .695 | .674 | 8.2% | .55–.77 | .589 | .51 .77 .54 .76 .62 |
| lean hysteresis rule | 2 | .550 | .740 | .631 | 10.4% | .48–.76 | .523 | .51 .79 .48 .62 .51 |
| **lean nested select** | 2 | .719 | .719 | **.719** | 7.7% | .57–.83 | .607 | .54 .86 .52 .75 .60 |

"Lean" reads the plus-calls signals from the v4 run instead of v1. The v4 run asks v1's questions plus the three
focused ones on the same state, so two Jev calls per tool call cover every feature.

**Ablation of the 3-call full model** (F1 when a group is removed; full = .731):
- current v1 scores: .713
- other current scores: .714
- history: .746
- flag state: .718
- position: .737
- other host: .698

Nested selection picked "full without history" in 3 of 5 outer folds (lean: 4 of 5). The other picks were "full" and,
once, "full without flag state".

**Cost.** Mean Jev input per tool call is about 7,100 tokens for lean (intent only about 1,170, plus calls with v4
about 5,960). At $0.042 per million tokens that is **$0.30 per 1,000 calls**. The 3-call model adds a v1 plus-calls run
and comes to about $0.54. GLM-5.2 full costs $6.01. The plus-calls history dominates the cost.

## Findings

1. **The gain comes from state and context, not from re-weighting the current score.** A logistic regression on the
   two current probabilities alone does worse than either probability alone (.593). Flag state adds about 6 points,
   and adding the extra current signals with the host bit adds about 6 more.
   - The fitted weights tell a specific story. The count of earlier flags has a strong positive weight. Steps since
     the first flag have a negative weight. So violations come in bursts right after the monitor first fires, and the
     effect decays.
   - Smooth history (running max, EMA) adds nothing, or hurts by 1–1.5 points. What matters is a discrete "this
     trajectory has already tripped" state, not a moving average.
   - A hand-set two-threshold hysteresis rule gains only about 1 point over the max rule. It lowers the bar after a
     flag, which raises recall but also raises false positives. The regression instead learns to raise precision
     inside flagged trajectories.
2. **The host bit is a correction to Jev, not a detector.** It fires on 241 calls, 44 of them violations (18% against
   a 7.7% base rate). Yet its weight is strongly negative once Jev's scores are in the model.
   - Jev already reacts to a foreign host in the call and over-reacts. The regression uses the bit to discount those
     alarms.
   - It is the largest single ablation (−3.3 points). It is also the only feature that clearly helps outside the
     largest family: F1 −big goes from .571 to .621 in the full model, and adding it to the current-score model lifts the worst fold from .43 to .57.
3. **The result is above GLM-5.2 full, but the interval is wide and concentrated.**
   - Nested out-of-fold F1 is .722 (3 calls) and .719 (lean). The trajectory-bootstrap 95% intervals are .57–.83, and
     both include .656.
   - Fold 1, which holds the 108-violation trajectory, scores .86. Folds 0 and 2 score .52 to .55.
   - Without the largest family, F1 is .61, against .50 to .55 for stateless Jev, so the gain is not only that
     trajectory. But it is far from GLM-level outside it. We don't know GLM's F1 without that family.

## Frozen configuration (for one test on fresh data)

**lean, full without history.**
- Two Jev calls per tool call:
  - v1 rubric, intent only.
  - v4 rubric, intent plus calls.
- Features:
  - Logit of both violation probabilities.
  - Mean scope score.
  - Logit of the v4 focused-question max.
  - Off-target kind mass from the plus-calls call.
  - Flag state (count of earlier flags, flagged-ever, steps since first flag; flag = an earlier step's max of the two
    probabilities ≥ 0.7).
  - Log step index.
  - Other-URL-host bit.
  - The two current-score × flagged interactions.
- L2 logistic regression with λ = 1, threshold at best F1.
- On fresh data, fit weights and threshold on all 4,897 ScopeJudge calls, freeze them, and score the new trajectories
  once.

This is what the nested procedure picked most often. Its own out-of-fold row (.725) is a selected number. Quote .719,
the lean nested estimate, as the expected value.

## Leakage and its limits

- **The approach itself.** All 100 trajectories had been studied before (phase 1). The idea of using flag state comes
  from knowing violations cluster within trajectories, which is a property of this benchmark. If fresh data has more
  isolated, one-off violations, flag state will help less.
- **No content rules.** No feature reads call contents beyond URL hostnames, so there are no hand-written rules fit to
  these trajectories' commands. The host comparison is the one generic rule the coordinator allowed, fixed in advance.
  The flag threshold (0.7) and EMA weight (0.3) were fixed before any result, never tuned.
- **Upstream selection.** The Jev rubrics themselves were developed with the whole set in view: v4 on the dev half,
  and v1 after reading all of it. That upstream selection is not removed by our folds.
- **Variant count.** Every variant run is in the table above (`results/scopejudge/causal_variants.txt`, gitignored).
  There are 27 rows, 21 of them shown in full, and no unlisted runs. The headline is the nested row, so picking the
  best row of the table is not the claim.
- **Fold layout.** The shared folds put the biggest trajectory in fold 1. Per-fold spread (.52 to .87) is the more
  honest measure of uncertainty than the pooled point.

## Reproducing

`python3 sj_causal.py "lean nested select"` recomputes every row from `results/scopejudge/*.jsonl`. Any variant name
given as an argument is also exported in Dreadnode's format and scored with their CLI.
