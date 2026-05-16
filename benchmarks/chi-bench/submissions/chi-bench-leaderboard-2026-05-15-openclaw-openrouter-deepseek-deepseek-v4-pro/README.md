# chi-Bench Leaderboard · openclaw · openrouter/deepseek/deepseek-v4-pro

Submitted: 2026-05-04 · chi-bench chi-bench-v1.0.0 · pass@1: **11.1%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 14.7% | 75 |
| pa_um | 12.0% | 75 |
| cm | 6.7% | 75 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
