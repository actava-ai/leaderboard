# chi-Bench Leaderboard · deepagents · openrouter/deepseek/deepseek-v4-pro

Submitted: 2026-05-05 · chi-bench chi-bench-v1.0.0 · pass@1: **10.7%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 14.7% | 75 |
| pa_um | 10.7% | 75 |
| cm | 6.7% | 75 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
