# U2Med · hermes · u2-flash

Submitted: 2026-11-06 · chi-bench chi-bench-v1.0.0 · pass@1: **68.0%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 72.0% | 25 |
| pa_um | 48.0% | 25 |
| cm | 84.0% | 25 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
