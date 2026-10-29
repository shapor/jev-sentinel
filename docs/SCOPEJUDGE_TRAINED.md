# A trained scope judge on ScopeJudge

Status: done. Protocol frozen and pushed (commit d967d76) before any model was fit; results below.

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

### Verdict

**Not an honest #1.** Under the frozen primary protocol (5-fold family-grouped CV, seed 0, variant chosen
inside each fold), the trained judge scores **F1 0.650** (precision 0.660, recall 0.639, flag rate 7.5%,
95% trajectory-bootstrap CI 0.549 to 0.724), just under GLM-5.2's 0.656 on the full transcript. Every other
honest view of the same procedure lands above GLM-5.2, but none of them clears it by more than the noise:

| Pre-declared procedure (select-in-fold) | F1 | P | R | flag | 95% CI (trajectory) |
|---|---|---|---|---|---|
| 5-fold by family, seed 0 (frozen headline) | 0.650 | 0.660 | 0.639 | 7.5% | 0.549 to 0.724 |
| 5-fold by family, mean of seeds 0 to 9 | 0.685 | | | | seeds range 0.650 to 0.720 |
| Leave one family out (30 folds) | 0.706 | 0.736 | 0.679 | 7.1% | 0.627 to 0.765 |
| Leave one boundary type out (3 folds) | 0.693 | 0.688 | 0.698 | 7.8% | 0.590 to 0.763 |
| Coordinator's shared split (by trajectory; families shared) | 0.763 | 0.735 | 0.793 | 8.3% | 0.645 to 0.845 |

For comparison, GLM-5.2 full transcript is 0.656 and GLM-5.2 intent_plus_calls 0.637; the mean single
expert is 0.78. Dreadnode did not publish per-call decisions, so no paired test against GLM is possible;
an unpaired CI that wide (about plus or minus 0.08) cannot separate 0.65 from 0.70.

What can be said honestly: a cheap stacker on zero-shot Jev outputs, trained on other task families, is
statistically indistinguishable from the best published judge at roughly a tenth of its cost
(about $0.34 per 1k calls for the three Jev calls, versus $3.22 for GLM-5.2 intent_plus_calls and $6.01
for full transcript), and it does so without reading tool outputs. Two further points in its favour, and
one against:

- Even with no training at all, Jev's own 0-4 scope score on intent_plus_calls, with only its threshold
  chosen on the training families, scores 0.659 on every one of ten reseeded splits (0.657 to 0.659). That
  one-parameter judge already ties GLM-5.2.
- A post-hoc equal-weight average (tree stacker, linear stacker, Jev scope score) is the most stable
  variant: 0.692 on the frozen split, 0.711 mean over seeds, 0.718 LOFO, 0.763 leave-one-type-out. It was
  assembled after seeing which components worked, so it is not eligible for the headline; it is the thing
  to test first on any fresh data.
- At the fixed operating points the picture is mixed. Matched to GLM-5.2's 13.3% flag rate, LOFO gives F1
  0.659 at recall 0.862 and 12.4% flagged (GLM: 0.637 at 0.872), but the frozen 5-fold split gives 0.567
  at 14.5% flagged. Matched to 87.2% recall, 5-fold gives 0.508 (LOFO 0.678 at 81.7% realized recall).
  Matched to Opus 4.8's 94.2% recall, 0.36 to 0.50, versus Opus's 0.547. Thresholds picked on other
  families overshoot or undershoot in the high-recall regime, so the trained judge is not better than the
  LLMs when the operator wants near-total recall.

### Why the gain over raw Jev is real but small

Jev already ranks calls well (ROC-AUC 0.94 to 0.95); what it lacks is a decision rule. The stacker mainly
does three things: it combines the intent-only and with-history views (at Jev's native thresholds intent-only
flags 13% of calls and with-history 9%, and they err on different calls), it uses Jev's own verdicts on the trajectory's
earlier calls (an agent that has already crossed a boundary tends to keep crossing it), and it learns which
of Jev's "kind" categories the ScopeJudge annotators actually treat as violations. Deterministic features
alone are near useless (ROC-AUC 0.6 to 0.77); hostname and verb heuristics do not capture scope. Frozen
sentence embeddings of task and call add nothing (AUC 0.72 alone), and a fine-tuned MiniLM cross-encoder
screened on the first outer fold reached ROC-AUC 0.66 after 35 CPU minutes, so it was abandoned:
the reading comprehension has to come from a large model, and the training data (30 families) is too
small to teach a small encoder what scope means.

### Why the numbers move so much between splits

One family, `system-config-boundary`, holds 167 of the 377 gold violations (44%). Whether a split's
training side contains it, and whether the inner threshold search sees it, decides most of the F1. Linear
stackers are hit hardest: their inner-CV threshold collapses when the inner fold without that family
under-scores it (lr_jev ranges 0.38 to 0.67 across seeds). Excluding that family, the frozen headline
falls to F1 0.601 and LOFO to 0.676. The benchmark's F1 is effectively half one family's F1, which makes
any single-split claim fragile, ours and the published ones alike.

The gap between the family-grouped splits (0.65 to 0.71) and the coordinator's trajectory-grouped split
(0.76) is the memorization premium: when other trajectories of the same family are in training, the model
learns that family's boundary. A number from a trajectory-grouped split should not be compared with
zero-shot judges.

### Transfer

Leave-one-boundary-type-out (train on host and technique families, test on side-effect/data families, and
so on) gives 0.693, no worse than random family folds, so the stacker is not leaning on a boundary type it
has seen. On 268 calls from 30 sanctioned Cybench CTF trajectories (all in scope, offensive-looking; scored
fresh with the same three Jev conditions), every stacker fit on all of ScopeJudge flagged 0 calls at its
deployment threshold, as did raw Jev. That shows no out-of-distribution false-positive blow-up but is a
weak test: those calls are easy negatives with no positives to find.

### Every variant

`jev` = Jev intent_only, intent_plus_calls and sentinel outputs plus Jev's verdicts on earlier calls;
`det` = deterministic features; `all` = both; `emb` = frozen bge-small embeddings; `soft` = vote-share
targets; `bal` = class-balanced weights; `raw_*` = a single Jev score, thresholded in-fold (references, not
candidates). Post-hoc variants were added after the first results and are not eligible for the headline.
F1 is at the in-fold F1-max threshold; reseeded means are over cv5 seeds 0 to 9.

| Variant | post hoc | cv5 F1 (P/R) | cv5 AUC | cv5 reseeded mean | LOFO F1 | type F1 | shared F1 |
|---|---|---|---|---|---|---|---|
| avg_gbm_lr_scope | yes | 0.692 (0.74/0.65) | 0.949 | 0.711 | 0.718 | 0.763 | 0.773 |
| gbm_all |  | 0.668 (0.69/0.65) | 0.940 | 0.698 | 0.702 | 0.668 | 0.776 |
| gbm_all_bal | yes | 0.665 (0.70/0.63) | 0.937 |  | 0.686 | 0.665 | 0.767 |
| raw_ipc_scope |  | 0.659 (0.71/0.61) | 0.940 | 0.658 | 0.659 | 0.652 | 0.646 |
| gbm_jev |  | 0.654 (0.67/0.64) | 0.926 | 0.673 | 0.652 | 0.632 | 0.748 |
| gbm_all_soft |  | 0.653 (0.65/0.66) | 0.959 | 0.667 | 0.683 | 0.708 | 0.764 |
| gbm_jev_bal | yes | 0.638 (0.69/0.59) | 0.932 |  | 0.661 | 0.637 | 0.750 |
| raw_ipc |  | 0.612 (0.64/0.59) | 0.936 | 0.614 | 0.625 | 0.611 | 0.619 |
| gbm_all_emb_soft | yes | 0.611 (0.57/0.66) | 0.955 |  | 0.708 | 0.711 | 0.756 |
| gbm_jev_soft_bal | yes | 0.596 (0.61/0.59) | 0.946 |  | 0.677 | 0.644 | 0.759 |
| gbm_jev_soft |  | 0.591 (0.57/0.61) | 0.946 | 0.609 | 0.682 | 0.657 | 0.759 |
| lr_jev_soft_bal | yes | 0.579 (0.51/0.66) | 0.933 |  | 0.710 | 0.691 | 0.743 |
| gbm_all_soft_bal | yes | 0.571 (0.57/0.57) | 0.950 |  | 0.664 | 0.666 | 0.774 |
| lr_all_soft |  | 0.545 (0.47/0.65) | 0.948 | 0.626 | 0.776 | 0.733 | 0.769 |
| lr_jev_soft |  | 0.520 (0.43/0.65) | 0.945 | 0.636 | 0.733 | 0.726 | 0.755 |
| lr_all_soft_bal | yes | 0.510 (0.49/0.53) | 0.940 |  | 0.762 | 0.708 | 0.762 |
| raw_io |  | 0.422 (0.41/0.44) | 0.945 |  | 0.428 | 0.609 | 0.613 |
| lr_jev_bal | yes | 0.422 (0.43/0.41) | 0.928 |  | 0.630 | 0.685 | 0.733 |
| lr_jev |  | 0.382 (0.42/0.35) | 0.929 | 0.528 | 0.711 | 0.687 | 0.749 |
| lr_all_bal | yes | 0.352 (0.36/0.34) | 0.879 |  | 0.563 | 0.594 | 0.761 |
| lr_all |  | 0.337 (0.31/0.37) | 0.920 | 0.448 | 0.660 | 0.625 | 0.752 |
| lr_all_emb_soft | yes | 0.279 (0.22/0.37) | 0.878 |  | 0.304 | 0.275 | 0.705 |
| lr_det_soft |  | 0.252 (0.17/0.46) | 0.767 | 0.188 | 0.174 | 0.168 | 0.363 |
| gbm_emb_soft | yes | 0.167 (0.09/0.72) | 0.717 |  | 0.172 | 0.203 | 0.567 |
| lr_emb_soft | yes | 0.164 (0.12/0.28) | 0.725 |  | 0.109 | 0.166 | 0.574 |
| gbm_det_soft |  | 0.113 (0.07/0.43) | 0.650 | 0.107 | 0.105 | 0.172 | 0.255 |
| lr_det |  | 0.107 (0.07/0.26) | 0.679 | 0.102 | 0.095 | 0.168 | 0.317 |
| gbm_det |  | 0.098 (0.06/0.44) | 0.609 | 0.097 | 0.107 | 0.167 | 0.264 |

Soft labels help linear stackers (the vote share is a smoother target than a hard majority) and slightly
hurt trees. Class balancing, added to fix the linear stackers' threshold collapse, did not.

### Cost and latency

Inference is three Jev calls (intent_only, intent_plus_calls, the original sentinel) that can run in
parallel, about 8,100 input tokens per call in total, roughly $0.34 per 1k calls at the published Jev
price and p50 latency of about 0.3 s (the slowest of the three), plus a sub-millisecond tabular model. Whether the sentinel call can be dropped was not ablated.

### Caveats

- Asymmetric comparison: the trained judge saw labels from 29 other ScopeJudge families; Dreadnode's judges
  saw none. Family grouping removes family memorization, not benchmark familiarity.
- The Jev rubric used as input was written by someone who had read the ScopeJudge paper (it names SSRF and
  pivoting through in-scope services). Its outputs were frozen before this work, but the rubric itself is
  not a blind instrument. Rubrics now being tuned on ScopeJudge on other branches are not used here.
- 377 positives, 44% from one family: CIs are wide, and the frozen seed happens to be the least favourable
  of ten.
- Dreadnode's numbers are single runs of stochastic LLM APIs on a dataset that has since been sanitized
  slightly; their own run-to-run spread is unknown.

### Reproducing

`train/features.py` builds the feature table from the frozen Jev snapshot, `train/run.py` runs every
variant under every split (`SPLITS=` env selects splits), `train/summarize.py` computes select-in-fold,
bootstrap CIs and reseeded means and scores the exported decisions with Dreadnode's `scopejudge score`
(which reproduces the harness metrics exactly), `train/transfer.py` runs the Cybench check, and
`train/embed.py` / `train/encoder.py` hold the embedding and encoder experiments.
