# Jev Sentinel on ScopeJudge

ScopeJudge (Dreadnode, arXiv 2607.07774) is a call-level benchmark for pre-execution scope gating. It has 100
offensive-security agent trajectories and 4,897 tool calls. Five professional testers labeled every call, and 377 of
them (7.7%) are out of scope by strict majority. Dreadnode scored eight LLM judges under five context strategies. The
best is GLM-5.2 with the full transcript (F1 0.656). This document records how Jev, a classification-only model, was
evaluated on the same benchmark, and the protocol used to keep the comparison honest.

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
