# chi-Bench Leaderboard · claude-code · anthropic/claude-opus-4-7

Submitted: 2026-04-30 · chi-bench chi-bench-v1.0.0 · pass@1: **24.4%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 24.0% | 75 |
| pa_um | 17.3% | 75 |
| cm | 32.0% | 75 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
