# Actava · codex · openai/gpt-5.6-sol

Submitted: 2026-07-24 · chi-bench chi-bench-v1.0.0 · pass@1: **25.3%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 36.0% | 25 |
| pa_um | 28.0% | 25 |
| cm | 12.0% | 25 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
