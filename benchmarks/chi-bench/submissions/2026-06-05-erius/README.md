# Michael Johnson (MJ) · erius · anthropic/claude-opus-4-8

Submitted: 2026-06-05 · chi-bench chi-bench-v1.0.0 · pass@1: **37.3%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 40.0% | 25 |
| pa_um | 16.0% | 25 |
| cm | 56.0% | 25 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
