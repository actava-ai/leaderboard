# chi-Bench Leaderboard · codex · openai/gpt-5.4-mini

Submitted: 2026-05-01 · chi-bench chi-bench-v1.0.0 · pass@1: **8.4%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 10.7% | 75 |
| pa_um | 13.3% | 75 |
| cm | 1.3% | 75 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
