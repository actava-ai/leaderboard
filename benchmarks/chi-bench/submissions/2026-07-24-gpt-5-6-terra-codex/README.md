# Actava · codex · openai/gpt-5.6-terra

Submitted: 2026-07-24 · chi-bench chi-bench-v1.0.0 · pass@1: **13.3%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 12.0% | 25 |
| pa_um | 20.0% | 25 |
| cm | 8.0% | 25 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
