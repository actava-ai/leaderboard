# MedArise · pa-codex-agent · openai/gpt-5.5

Submitted: 2026-06-09 · chi-bench chi-bench-v1.0.0 · pass@1: **68.0%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 68.0% | 25 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
