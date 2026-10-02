# HG-Market-System · hg-closure-codex · openai/gpt-5.4-mini

Submitted: 2026-10-02 · chi-bench chi-bench-v1.0.0 · pass@1: **21.3%**

| Domain | pass@1 | n_trials |
|---|---|---|
| pa_provider | 44.0% | 25 |
| pa_um | 16.0% | 25 |
| cm | 4.0% | 25 |

Inspect a trajectory:

    zstdcat trials/pa_provider/<trial_id>/agent/trajectory.jsonl.zst | jq .

See `submission.json` for the full manifest, `provenance.json` for reproducibility info.
