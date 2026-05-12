# Contributing

Thanks for submitting to an actava-ai benchmark leaderboard.

## How submissions work

1. You produce a **packet** with your benchmark's official tooling (e.g. `cb submission prepare` for chi-bench). See the producer repo for instructions.
2. You open a PR adding the packet under `benchmarks/<bench>/submissions/<YYYY-MM-DD>-<slug>/`. The PR must touch **only** that one new directory.
3. CI (`.github/workflows/validate.yml`) runs schema and integrity checks; it labels the PR `valid-submission`, `invalid-submission`, or `needs-review` and leaves a sticky comment summarizing checks.
4. A maintainer reviews the PR and merges if validation passed and the submission is plausible.

For the exact submission flow (manual or via `scripts/submit.py`), see the main [README](README.md).

## What CI catches

- Directory naming + date validity
- Required files (`submission.json`, `results.csv`, `sub.yaml`, `provenance.json`, `README.md`, ≥1 trial result)
- No unexpected files (`.zip`, `.bak`, hidden files except `.gitkeep`)
- `submission.json` schema validation (per `benchmarks/<bench>/schema/submission-v<N>.json`)
- `results.csv` rows match the manifest exactly
- `provenance.json` has required keys
- Per-trial integrity: required files, valid zstd, valid JSONL per line
- Trial counts match `results.per_domain.<domain>.n_trials`
- Size limits (per-file and total)

Soft warnings (not failures): unknown dataset version, duplicate `submission.id`.

## What reviewers do beyond CI

- Sanity-check headline metrics for plausibility (a 99% pass@1 on a benchmark where state-of-the-art is 30% warrants a closer look).
- Spot-inspect one or two trajectories (`zstdcat trials/<dom>/<id>/agent/trajectory.jsonl.zst | jq .`).
- Confirm the producer repo and dataset version look right.
- For resubmissions (same `submission.id`, new date): decide whether to keep the old submission alongside the new one or remove it in a follow-up cleanup PR.

CI does **not** re-judge submissions in v1 (trust-the-evidence model). Maintainers may manually re-judge a random trial via the producer's tooling if a submission looks suspicious.

## Resubmission policy

- A new submission with a fresh date prefix is always acceptable, even if the slug is identical to an existing submission.
- Old submissions are kept by default for historical record. If you want an old run removed (e.g. it was broken), say so in the PR body of your new submission.

## PR scope

Submission PRs must touch **only** files under `benchmarks/*/submissions/*/`. Changes to schemas, READMEs, workflows, or other benchmarks require a separate PR (or the maintainer-applied `meta:` label, which bypasses the CI scope check).

## Adding a new benchmark

See [`benchmarks/README.md`](benchmarks/README.md).

## Code of conduct

Be excellent to each other. Reviewers can close PRs that don't follow the contract; you can reopen after fixing.
