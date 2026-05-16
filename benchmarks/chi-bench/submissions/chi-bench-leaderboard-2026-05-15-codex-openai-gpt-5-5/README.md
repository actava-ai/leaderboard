# chi-Bench Leaderboard · codex · openai/gpt-5.5

Submitted: 2026-04-30 · chi-bench chi-bench-v1.0.0 · pass@1: **20.9%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 29.3% | 75 |
| pa_um | 32.0% | 75 |
| cm | 1.3% | 75 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
