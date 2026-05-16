# chi-Bench Leaderboard · hermes · openrouter/deepseek/deepseek-v4-pro

Submitted: 2026-05-04 · chi-bench chi-bench-v1.0.0 · pass@1: **13.8%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 8.0% | 75 |
| pa_um | 25.3% | 75 |
| cm | 8.0% | 75 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
