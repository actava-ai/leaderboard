# chi-Bench Leaderboard · claude-code · anthropic/claude-sonnet-4-6

Submitted: 2026-04-30 · chi-bench chi-bench-v1.0.0 · pass@1: **26.2%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 24.0% | 75 |
| pa_um | 34.7% | 75 |
| cm | 20.0% | 75 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
