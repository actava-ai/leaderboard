# Actava · openai-agents · z-ai/glm-5.2

Submitted: 2026-07-06 · chi-bench chi-bench-v1.0.0 · pass@1: **18.7%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 20.0% | 25 |
| pa_um | 32.0% | 25 |
| cm | 4.0% | 25 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
