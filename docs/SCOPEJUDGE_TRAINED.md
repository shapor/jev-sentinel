# A trained scope judge on ScopeJudge

Status: protocol frozen, results pending.

## Goal

Dreadnode's ScopeJudge (arXiv 2607.07774) asks a judge, before an offensive-security agent's tool call runs,
whether the call stays inside the scope the user's task sets. The best published judge is GLM-5.2 reading the
full transcript (F1 0.656); the cheapest strong one is GLM-5.2 on intent plus prior calls (F1 0.637, recall
0.872, 13.3% flagged, $3.22 per 1k calls). The mean single human expert scores F1 0.78 against the
five-expert majority. Jev, scored zero-shot with our scope rubric, reaches ROC-AUC 0.945 but held-out F1 of
only 0.61 to 0.63 (docs on branch `scopejudge-eval`).

This work asks whether a model trained on ScopeJudge itself, evaluated only on task families it never saw,
beats every published judge on F1. Only a result that survives the protocol below counts.

## The comparison is asymmetric, by construction

Dreadnode's judges are zero-shot LLMs: they never saw a ScopeJudge label. Anything trained here has seen
labels from the other task families of the same benchmark: same environment generator, same five annotators,
same agents, same prompt shape. Grouped cross-validation removes task-family memorization, but not
benchmark-level familiarity (what these annotators tend to call out of scope, what the agents tend to do).
Any headline must say "trained on held-out-family ScopeJudge folds", never "zero-shot". Transfer tests below
exist to bound how much of the gain is benchmark familiarity.

## Evaluation protocol (frozen before any test-fold result was seen)

What was already known when this was written: the full-set summary statistics of the zero-shot Jev runs
(AUCs and untuned F1 on all 4,897 calls), per-family counts of calls and gold positives, and the tool-name
distribution. No trained model had been fit.

**Groups.** The unit of grouping is the task family, with the `-dead-end` suffix stripped, so the two
`jwt-internal-api-trust` variants form one group (30 groups). A group never appears in both the training and
the test side of a split, which also keeps every trajectory whole.

**Primary split.** Five-fold stratified grouped CV (scikit-learn `StratifiedGroupKFold`, shuffle, seed 0,
stratified on the gold label). Every call gets exactly one out-of-fold prediction, so metrics are computed on
all 4,897 calls and are directly comparable to Dreadnode's full-set table. One family
(`system-config-boundary`) holds 167 of the 377 positives, so fold-level numbers will be lumpy; that is a
property of the data, reported rather than engineered away.

**Secondary splits.** Leave-one-family-out (30 folds) and leave-one-boundary-type-out (3 folds: host,
technique, side-effect/data, using the family typing already published on `scopejudge-eval`). The latter is
the transfer test: a model that only memorized what host-boundary families look like should collapse when
the whole host type is held out.

**Threshold rule.** Inside each outer training fold, an inner four-fold stratified grouped CV (seed 0) on the
training families yields inner out-of-fold probabilities; the decision threshold is the one that maximizes F1
on those inner predictions. The model is then refit on the whole outer training fold and the threshold
applied unchanged to the test fold. Test-fold labels never touch threshold choice.

**Fixed operating points.** The same inner predictions also pick thresholds that hit (a) a 13.3% flag rate
(GLM-5.2 intent_plus_calls), (b) 87.2% recall (GLM-5.2 intent_plus_calls), (c) 94.2% recall (Opus 4.8
intent_only). Reported test values are whatever those training-fold thresholds realize on the test fold, so
they will not hit the targets exactly.

**Metric.** Precision, recall, F1 and flag rate against the strict-majority gold (at least three of five
reviewers), computed by Dreadnode's own `scopejudge score` on exported decision files, plus ROC-AUC and
PR-AUC on the pooled out-of-fold probabilities. Per-fold F1 and its spread are reported. 95% confidence
intervals come from a trajectory bootstrap (2,000 resamples of the 100 trajectories) and, as a more
conservative check, a family bootstrap.

**Model selection.** Every variant tried is recorded with its out-of-fold numbers, including losers. Because
picking the best of many variants on the same out-of-fold predictions is itself optimistic, the headline
number is not "the best variant" but a *select-in-fold* procedure: within each outer training fold, the
variant is chosen by inner-CV F1 among the variants declared in the candidate list, and only that choice is
scored on the test fold. Variants added after results were seen are marked as such and are not eligible for
the headline.

**Labels.** Training may use the five votes (soft labels: vote share as target), but all scoring uses the
strict-majority gold.

## Candidate list (declared before results)

1. Stacking on frozen zero-shot Jev outputs (snapshot of `scopejudge-eval` commit 66357cb results: intent_only,
   intent_plus_calls and the original sentinel; P(block), 0-4 scope score, six kind probabilities) with
   logistic regression and with gradient boosting.
2. The same plus cheap deterministic features computable before the call runs: tool name, argument size,
   hosts/URLs/IPs in the arguments versus those named in the task, hosts never seen earlier in the
   trajectory, risky-verb cues, and the trajectory's history of earlier Jev scores (calls already judged).
3. Deterministic features alone (no Jev), as a floor.
4. A small encoder (MiniLM / ModernBERT class) fine-tuned on CPU over "task + recent prior calls + proposed
   call", alone and as a stacking feature.
5. Hard versus soft labels for 1 and 2.

## Results

Pending.
