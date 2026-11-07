# Bin_Han · openai-agents · mimo-v2.6-pro

Submitted: 2026-11-07 · chi-bench chi-bench-v1.0.0 · pass@1: **18.1%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 16.0% | 25 |
| pa_um | 36.4% | 22 |
| cm | 4.0% | 25 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
