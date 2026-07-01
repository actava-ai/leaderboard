# unisound · hermes · openai/qwen3.5_27b_sft_0609

Submitted: 2026-07-01 · chi-bench chi-bench-v1.0.0 · pass@1: **22.7%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 4.0% | 25 |
| pa_um | 4.0% | 25 |
| cm | 60.0% | 25 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
