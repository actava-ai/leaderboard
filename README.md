# CHI-Bench Leaderboard

[![Live Leaderboard](https://img.shields.io/badge/Live_Leaderboard-actava.ai-blue?style=for-the-badge)](https://actava.ai/benchmarks/leaderboards)
[![Submit Guide](https://img.shields.io/badge/Submit_Guide-walkthrough-ff5baf?style=for-the-badge)](https://actava.ai/benchmarks/submit)
[![License](https://img.shields.io/badge/License-Apache_2.0-purple?style=for-the-badge)](LICENSE)

[![Discord](https://img.shields.io/badge/Join_Our_Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/eQfMpUQtda)
[![Slack](https://img.shields.io/badge/Join_Our_Slack-4A154B?style=for-the-badge&logo=slack&logoColor=white)](https://join.slack.com/share/enQtMTExMTE4MDYyNTMzOTktMzZiMGE2MjYxYjRmNzYyMTFiMDVkZmJiNzZiYWUwNWMwNzJkMGRiZDIwYmU5ZWM5NDQyY2E2ZDEyNTcxZWQ1ZA)
[![WeChat](https://img.shields.io/badge/Join_Our_WeChat-07C160?style=for-the-badge&logo=wechat&logoColor=white)](https://drive.google.com/file/d/1FD93bxx4E9C9FZDCQW0o_KoQGi-i8WOa/view?usp=sharing)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-actava-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/company/actava/)

Public, data-only record of benchmark submissions for CHI-Bench.

We accept submissions via pull request. The full audit packet (manifest + per-trial verifier evidence + compressed trajectories) lives in git so reviewers can inspect any submission directly from the PR diff. 

The rendered leaderboard lives at **[actava.ai/benchmarks/leaderboards](https://actava.ai/benchmarks/leaderboards)** — and reads `results.csv` files out of this repo.

## Benchmarks tracked

| Benchmark | Producer repo | Current version | Submissions |
|---|---|---|---|
| [chi-bench](benchmarks/chi-bench/) | [actava-ai/chi-bench](https://github.com/actava-ai/chi-bench) | `chi-bench-v1.0.0` | see [submissions/](benchmarks/chi-bench/submissions/) |

## Submit a result

> [!TIP]
> Prefer reading on the web? The same flow with collapsible step UI lives at **[actava.ai/benchmarks/submit](https://actava.ai/benchmarks/submit)**, and a deeper reference is at **[actava.ai/benchmarks/docs/leaderboard](https://actava.ai/benchmarks/docs/leaderboard)**.

Two repos, one handoff:

1. **Producer** — run your trials and produce a packet with the benchmark's tooling. For chi-bench (see [actava-ai/chi-bench](https://github.com/actava-ai/chi-bench) for the full lifecycle, or [the web docs](https://actava.ai/benchmarks/docs/run)):

   ```bash
   uv run cb submission prepare -f configs/submissions/<id>.yaml
   # → logs/submissions/<id>/packet/YYYY-MM-DD-<id>/
   ```

   See chi-bench's [submission packet contract](https://github.com/actava-ai/chi-bench/blob/main/docs/submission-packet.md) for the directory shape.

2. **Leaderboard** (this repo) — fork this repo and open a PR adding that packet. Two paths below ([Quick](#quick-helper) / [Manual](#manual)) run the same CI validation (`.github/workflows/validate.yml`).

3. CI labels the PR `valid-submission` / `invalid-submission` / `needs-review` and posts a sticky report; a maintainer reviews and merges. Verified runs land on the **[live leaderboard](https://actava.ai/benchmarks/leaderboards)** within one business day.

> [!IMPORTANT]
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

### Claude Code

This repo ships a [`submit-to-leaderboard`](.claude/skills/submit-to-leaderboard/SKILL.md) skill that wraps the helper flow above with preflight checks, partial-failure recovery, and pointers to producer-side fixes when the validator complains. Open the repo in Claude Code, point it at your packet, and ask it to submit — it invokes the skill automatically.

```
> /submit-to-leaderboard /abs/path/to/packet/2026-05-12-<slug>/ to the leaderboard
```
### Codex

Codex reads [`AGENTS.md`](AGENTS.md) at the repo root, which points at the same [`submit-to-leaderboard`](.claude/skills/submit-to-leaderboard/SKILL.md) skill (the file is plain markdown — instructions are platform-agnostic; only the helper tool names differ from Claude Code's). From a Codex session in the repo:

```
> submit /abs/path/to/packet/2026-05-12-<slug>/ to the leaderboard
```

Codex picks up the AGENTS.md pointer, reads the skill, and follows the same flow.

### Helper script

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

### Manual submission

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

## Pre-PR sanity check

`scripts/validate.py` is a thin shim around the CI validator — same code path. Run it locally before opening a PR to catch problems early:

```bash
python scripts/validate.py benchmarks/chi-bench/submissions/2026-05-12-<slug>/
```

Exit 0 = validation passed. Exit 1 = errors (printed); fix and rerun.

## Inspecting a submission

Submission directories are plain files. Click into any one on GitHub to see the manifest, headline metrics (in the auto-generated README), and the per-trial tree. For a sortable, filterable view of every merged submission with PA/UM/CM breakdown columns, see the **[live leaderboard at actava.ai/benchmarks/leaderboards](https://actava.ai/benchmarks/leaderboards)**.

Trajectories are zstd-compressed JSONL:

```bash
zstdcat benchmarks/chi-bench/submissions/<dir>/trials/<domain>/<trial_id>/agent/trajectory.jsonl.zst | jq .
```

## Reviewer / maintainer notes

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## See also

- **[Live leaderboard](https://actava.ai/benchmarks/leaderboards)** — sortable table of every merged submission.
- **[CHI-Bench overview & authors](https://actava.ai/benchmarks/chi-bench)** — what the benchmark measures and why.
- **[Submission walkthrough](https://actava.ai/benchmarks/submit)** — the producer + leaderboard flow with collapsible step UI.
- **[Web docs · Leaderboard repo](https://actava.ai/benchmarks/docs/leaderboard)** — the same workflow this README describes, with deeper reviewer notes.
- **[Web docs · Run experiments](https://actava.ai/benchmarks/docs/run)** — producer-side commands that build the packet you submit here.
- **[Browse all 75 tasks](https://actava.ai/benchmarks/tasks)** — the task explorer.
- **[Producer repo (actava-ai/chi-bench)](https://github.com/actava-ai/chi-bench)** — the benchmark code that produces packets accepted here.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
