# CHI-Bench Leaderboard

Public, data-only record of benchmark submissions for CHI-Bench.

This repo accepts submissions via pull request. The full audit packet (manifest + per-trial verifier evidence + compressed trajectories) lives in git so reviewers can inspect any submission directly from the PR diff. The rendered leaderboard lives elsewhere — at [actava.ai/benchmarks](https://actava.ai/benchmarks) — and reads `results.csv` files out of this repo.

## Benchmarks tracked

| Benchmark | Producer repo | Current version | Submissions |
|---|---|---|---|
| [chi-bench](benchmarks/chi-bench/) | [actava-ai/chi-bench](https://github.com/actava-ai/chi-bench) | `chi-bench-v1.0.0` | see [submissions/](benchmarks/chi-bench/submissions/) |

## Submit a result

Two repos, one handoff:

1. **Producer** — run your trials and produce a packet with the benchmark's tooling. For chi-bench (see [actava-ai/chi-bench](https://github.com/actava-ai/chi-bench) for the full lifecycle):

   ```bash
   uv run cb submission prepare -f configs/submissions/<id>.yaml
   # → logs/submissions/<id>/packet/YYYY-MM-DD-<id>/
   ```

   See chi-bench's [submission packet contract](https://github.com/actava-ai/chi-bench/blob/main/docs/submission-packet.md) for the directory shape.

2. **Leaderboard** (this repo) — fork this repo and open a PR adding that packet. Two paths below ([Quick](#quick-helper) / [Manual](#manual)) run the same CI validation (`.github/workflows/validate.yml`).

3. CI labels the PR `valid-submission` / `invalid-submission` / `needs-review` and posts a sticky report; a maintainer reviews and merges.

> Each submission PR must touch **only** one new directory under `benchmarks/<bench>/submissions/<YYYY-MM-DD>-<slug>/`. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the scope rule and reviewer policy.

### One-time setup

Before your first submission you need a fork of this repo. Either:

```bash
# Option A — via the gh CLI (recommended; also handles auth)
gh auth login                          # authenticate to GitHub
gh repo fork actava-ai/leaderboard --clone=false
git config --global user.email "you@example.com"   # if not already set
```

…or open <https://github.com/actava-ai/leaderboard> in your browser and click **Fork** at the top-right.

After forking, clone *your* fork (not actava-ai's directly):

```bash
git clone https://github.com/<you>/leaderboard && cd leaderboard
```

Subsequent submissions reuse this same fork — no need to re-fork.

### Quick (helper)

```bash
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

From your fork clone (see [One-time setup](#one-time-setup) above):

```bash
cp -r /path/to/packet/2026-05-12-<slug>/ benchmarks/<bench>/submissions/
python scripts/validate.py benchmarks/<bench>/submissions/2026-05-12-<slug>/
git checkout -b sub/<bench>/2026-05-12-<slug>
git add benchmarks/<bench>/submissions/2026-05-12-<slug>/
git commit -m "<bench>: <team> · <agent> · <model>"
git push origin sub/<bench>/2026-05-12-<slug>
gh pr create -R actava-ai/leaderboard --base main
```

Both flows go through the same CI validation (`.github/workflows/validate.yml`).

### Claude Code

This repo ships a [`submit-to-leaderboard`](.claude/skills/submit-to-leaderboard/SKILL.md) skill that wraps the helper flow above with preflight checks, partial-failure recovery, and pointers to producer-side fixes when the validator complains. Open the repo in Claude Code, point it at your packet, and ask it to submit — it invokes the skill automatically.

### Codex

Codex reads [`AGENTS.md`](AGENTS.md) at the repo root, which points at the same [`submit-to-leaderboard`](.claude/skills/submit-to-leaderboard/SKILL.md) skill (the file is plain markdown — instructions are platform-agnostic; only the helper tool names differ from Claude Code's). From a Codex session in the repo:

```
> /submit-to-leaderboard /abs/path/to/packet/2026-05-12-<slug>/ to the leaderboard
```

Codex picks up the AGENTS.md pointer, reads the skill, and follows the same flow.

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
