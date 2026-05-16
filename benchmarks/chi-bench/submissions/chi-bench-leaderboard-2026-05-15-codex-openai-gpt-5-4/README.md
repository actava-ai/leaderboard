# chi-Bench Leaderboard · codex · openai/gpt-5.4

Submitted: 2026-04-30 · chi-bench chi-bench-v1.0.0 · pass@1: **16.0%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 24.0% | 75 |
| pa_um | 17.3% | 75 |
| cm | 6.7% | 75 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
