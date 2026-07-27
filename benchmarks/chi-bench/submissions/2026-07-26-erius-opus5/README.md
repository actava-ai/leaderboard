# Michael Johnson (MJ) · erius · anthropic/claude-opus-5

Submitted: 2026-07-27 · chi-bench chi-bench-v1.0.0 · pass@1: **54.7%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 72.0% | 25 |
| pa_um | 36.0% | 25 |
| cm | 56.0% | 25 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
