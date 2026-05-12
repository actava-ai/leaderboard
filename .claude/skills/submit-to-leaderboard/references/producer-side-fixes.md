# Producer-side fixes for validator failures

When `scripts/validate.py` errors out on a packet, the producer drifted from the leaderboard schema. **Fix it on the producer, then re-prepare the packet** — do not hand-edit packet files (the trajectories, scorecards, and manifest are an audit record).

## Where the schema lives

Per-benchmark, in this repo: `benchmarks/<bench>/schema/submission-v1.json`.

The chi-bench schema requires (non-exhaustive):

- `dataset.name` = `"chi-bench"` (literal)
- `dataset.version` matches `^chi-bench-v[0-9]+\.[0-9]+\.[0-9]+$`
- `submission.submitted_at` is an RFC3339 timestamp
- `results.overall` and `results.per_domain` are **nested** under `results`
- `provenance` contains `chi_bench_git_sha`, `image_digest`, `judge_model`, `harness_version`
- Directory name matches `^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9_-]{0,63}$` and the slug equals `submission.id`

## Common drift

| Symptom | Likely cause | Fix |
|---|---|---|
| `dataset.name is missing` / `results.overall is missing` / `provenance.chi_bench_git_sha is missing` | Packet produced before the producer's schema-translation commit | Pull the producer, re-run `cb submission prepare --force` |
| `Directory name does not match required pattern` | Producer wrote a date-less or wrong-format dir | Re-run prepare; the producer auto-prefixes today's UTC date |
| `Directory slug does not match submission.id` | Manifest's `submission.id` was edited but dir name wasn't | Re-run prepare from the canonical config |
| `submission.notes` is `null` | Old producer emitted nulls for optional fields | Re-run prepare (current producer drops nulls) |

## Re-preparing a chi-bench packet

The raw `submission run` output stays on disk under `<output_root>/{pa_provider,pa_um,cm}/...`. Re-running prepare reuses those trials and only rewrites the packet:

```bash
# In the producer repo (chi-bench), not this repo:
uv run cb submission prepare -f configs/submissions/<id>.yaml --force
```

The new packet lands at `<output_root>/packet/<YYYY-MM-DD>-<id>/`. Run the leaderboard validator against that path, then resume the submission flow.
