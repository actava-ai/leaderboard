# chi-Bench Leaderboard · gemini-cli · google/gemini-3-pro-preview

Submitted: 2026-04-30 · chi-bench chi-bench-v1.0.0 · pass@1: **7.1%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 14.7% | 75 |
| pa_um | 6.7% | 75 |
| cm | 0.0% | 75 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
