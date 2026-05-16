# chi-Bench Leaderboard · hermes · openrouter/qwen/qwen3-6-max-preview

Submitted: 2026-05-04 · chi-bench chi-bench-v1.0.0 · pass@1: **16.4%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 9.3% | 75 |
| pa_um | 26.7% | 75 |
| cm | 13.3% | 75 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
