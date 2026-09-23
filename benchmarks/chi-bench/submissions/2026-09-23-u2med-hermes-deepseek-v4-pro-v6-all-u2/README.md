# U2Med · U2MedFellow v6 · openai/deepseek-v4-pro

Submitted: 2026-09-23 · chi-bench chi-bench-v1.0.0 · pass@1: **37.3%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 24.0% | 25 |
| pa_um | 24.0% | 25 |
| cm | 64.0% | 25 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
