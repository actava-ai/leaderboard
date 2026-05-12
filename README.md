# actava-ai/leaderboard

Public, data-only record of benchmark submissions for actava-ai benchmarks.

This repo accepts submissions via pull request. The full audit packet (manifest + per-trial verifier evidence + compressed trajectories) lives in git so reviewers can inspect any submission directly from the PR diff. The rendered leaderboard lives elsewhere — at [actava.ai/benchmarks](https://actava.ai/benchmarks) — and reads `results.csv` files out of this repo.

## Benchmarks tracked

| Benchmark | Producer repo | Current version | Submissions |
|---|---|---|---|
| [chi-bench](benchmarks/chi-bench/) | [actava-ai/chi-bench](https://github.com/actava-ai/chi-bench) | `chi-bench-v1.0.0` | see [submissions/](benchmarks/chi-bench/submissions/) |

To add a new benchmark, see [`benchmarks/README.md`](benchmarks/README.md).

## Submit a result

You produce a **packet** on the producer side (e.g. `cb submission prepare` for chi-bench) and open a PR adding it to this repo. Two paths, both equivalent.

### Quick (helper)

```bash
# Prereqs: gh CLI authenticated; git user.email configured; you forked this repo on GitHub.
git clone https://github.com/<you>/leaderboard && cd leaderboard
python scripts/submit.py /path/to/packet/2026-05-12-<slug>/
```

The helper:

1. Reads the packet's `submission.json:dataset.name` to route it to the right benchmark subtree.
2. Runs `scripts/validate.py` against the proposed directory.
3. Copies the packet into `benchmarks/<bench>/submissions/<dir>/`.
4. Creates a branch `sub/<bench>/<dir>`, commits, pushes to your fork (or directly, with `--no-fork`).
5. Opens a PR via `gh pr create`. Prints the PR URL.

Flags: `--no-fork`, `--no-open-pr`, `--on-conflict {abandon,replace,bump-date}`, `--leaderboard-repo <slug>`.

### Manual

```bash
git clone https://github.com/<you>/leaderboard && cd leaderboard
cp -r /path/to/packet/2026-05-12-<slug>/ benchmarks/<bench>/submissions/
python scripts/validate.py benchmarks/<bench>/submissions/2026-05-12-<slug>/
git checkout -b sub/<bench>/2026-05-12-<slug>
git add benchmarks/<bench>/submissions/2026-05-12-<slug>/
git commit -m "<bench>: <team> · <agent> · <model>"
git push origin sub/<bench>/2026-05-12-<slug>
gh pr create --base main
```

Both flows go through the same CI validation (`.github/workflows/validate.yml`).

## Pre-PR sanity check

`scripts/validate.py` is a thin shim around the CI validator — same code path. Run it locally before opening a PR to catch problems early:

```bash
python scripts/validate.py benchmarks/chi-bench/submissions/2026-05-12-<slug>/
```

Exit 0 = validation passed. Exit 1 = errors (printed); fix and rerun.

## Inspecting a submission

Submission directories are plain files. Click into any one on GitHub to see the manifest, headline metrics (in the auto-generated README), and the per-trial tree.

Trajectories are zstd-compressed JSONL:

```bash
zstdcat benchmarks/chi-bench/submissions/<dir>/trials/<domain>/<trial_id>/agent/trajectory.jsonl.zst | jq .
```

## Reviewer / maintainer notes

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

Apache-2.0. See [`LICENSE`](LICENSE).
