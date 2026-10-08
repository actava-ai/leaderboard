# KouMurase · chi-harness · anthropic/claude-opus-4-7

Submitted: 2026-10-08 · chi-bench chi-bench-v1.0.0 · pass@1: **94.7%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 100.0% | 25 |
| pa_um | 96.0% | 25 |
| cm | 88.0% | 25 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
