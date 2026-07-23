# Actava · claude-code · anthropic/claude-fable-5

Submitted: 2026-07-22 · chi-bench chi-bench-v1.0.0 · pass@1: **24.0%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 24.0% | 25 |
| pa_um | 24.0% | 25 |
| cm | 24.0% | 25 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
