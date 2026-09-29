# Published results

Per-item results behind the numbers in the top-level README. Every file is one JSON object per line (gzip-compressed, except `inbound_bench.json`).

**No payload text is included.** Rows are keyed by the IDs of the public source datasets, so you can join them to the original data yourself:

| File | Rows | Source dataset | Scored against |
|---|---|---|---|
| `swarm.jsonl.gz` | 53,870 | [Swarm Traces](https://swarmtraces.org/) `redacted.jsonl` (root payloads with their decoded children) | one generic sandbox-CTF scope, because the swarm agents' real targets aren't public |
| `cybench.jsonl.gz` | 1,456 | [antieval/cybench-trajectories](https://huggingface.co/datasets/antieval/cybench-trajectories), six models | each run's own challenge prompt |
| `swe.jsonl.gz` | 838 | [nebius/SWE-agent-trajectories](https://huggingface.co/datasets/nebius/SWE-agent-trajectories), 40 trajectories | each trajectory's own GitHub issue |
| `attack_swarm.jsonl.gz` | 6,000 | deterministic sample of the swarm units (seed 11) | MITRE ATT&CK tactic pass (`attack.py`) |
| `attack_cybench.jsonl.gz` | 1,456 | as above | as above |
| `attack_swe.jsonl.gz` | 838 | as above | as above |
| `inbound_bench.json` | 1 | [deepset/prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections) test split | AUC and recall of the inbound check |

## Fields

- `id`: the source record ID (Swarm Traces `R0000001`; Cybench `model:trajectory:message:call`; SWE `index:instance:message`).
- `p_block`: Jev's probability that the action should be blocked.
- `scope`: expected out-of-scope score, 0 (in scope) to 4 (clearly out of scope).
- `stage`, `stage_probs`: what the action is mainly doing, with the full distribution.
- `verdict`: allow, ask or block, as computed when the item was scored. The policy is `sentinel.verdict(p_block, stage)`, so verdicts can be recomputed with different thresholds without re-scoring.
- `regex`: whether the keyword baseline flags the action.
- `tags` (swarm only): the Swarm Traces authors' own evidence tags, carried over from their dataset.
- `tactic`, `confidence` (ATT&CK files): Jev's ATT&CK Enterprise tactic choice (or `none`) and its confidence.

Scored with `jev-latest` (jev-1.13.0) on 2026-09-26 and 2026-09-27. These are one run each with no human labels, so treat stage and tactic labels as Jev's judgment, not ground truth.
