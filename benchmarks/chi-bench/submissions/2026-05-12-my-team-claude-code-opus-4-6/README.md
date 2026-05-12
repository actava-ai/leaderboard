# My Team · claude-code · anthropic/claude-opus-4-6

Submitted: 2026-05-12 · chi-bench chi-bench-v1.0.0 · pass@1: **28.0%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 20.0% | 25 |
| pa_um | 36.0% | 25 |
| cm | 28.0% | 25 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
