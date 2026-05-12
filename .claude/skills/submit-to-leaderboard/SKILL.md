---
name: submit-to-leaderboard
description: Submit a benchmark packet to actava-ai/leaderboard via pull request. Use when the user wants to submit, upload, post, or open a PR for a packet directory (e.g. produced by `cb submission prepare`) — covers local schema validation, the `scripts/submit.py` helper, recovery when the helper partially fails (fork disabled, network blip), and the manual `cp + git + gh` fallback.
---

# Submit to actava-ai/leaderboard

Run from a **clone of the user's fork** of this repo. External submitters do not have write access to `actava-ai/leaderboard` — submissions go via fork + PR. The producer (e.g. `actava-ai/chi-bench`) generates the packet; this skill takes a packet directory as input and ends with an open PR on `actava-ai/leaderboard`.

## Preflight

Confirm in one batch — fail fast if any check fails:

```bash
gh auth status                              # must be logged in
git config --get user.email                 # must be set
test -f <packet>/submission.json            # packet must exist + look like a packet
git remote -v | grep -q actava-ai/leaderboard || echo "WARN: cwd may not be a leaderboard fork clone"
```

If the user hasn't forked yet, the helper handles it (idempotent `gh repo fork`). If they don't have a local clone of the fork, get one first:

```bash
gh repo fork actava-ai/leaderboard --clone=true   # forks + clones in one shot
cd leaderboard
```

## Two-step flow

### 1. Validate the packet locally

The validator (`.github/scripts/validate_submission.py`, called by `scripts/validate.py`) imports `jsonschema`, `zstandard`, and `pyyaml` — none are installed by default. Inject them with `uv run --with`:

```bash
uv run --with jsonschema --with zstandard --with pyyaml \
  python scripts/validate.py /abs/path/to/<YYYY-MM-DD>-<slug>/
```

Expect `✅ <dir>: 0 error(s), 0 warning(s)`. Any errors here will also fail in CI — fix them on the producer side and re-prepare the packet (do **not** hand-edit packet files). See `references/producer-side-fixes.md` for common producer issues this surfaces.

### 2. Open the PR

```bash
uv run --with jsonschema --with zstandard --with pyyaml \
  python scripts/submit.py /abs/path/to/<YYYY-MM-DD>-<slug>/
```

The helper auto-detects the benchmark from `submission.json:dataset.name`, copies the packet into `benchmarks/<bench>/submissions/`, runs the validator again, creates branch `sub/<bench>/<dir>`, commits with a rich PR body, ensures the user has a fork of `actava-ai/leaderboard` (idempotent), pushes the branch to that fork, and opens the PR with head `<user>:<branch>`.

On success, the PR URL is printed. Pass that back to the user.

> `--no-fork` exists for maintainers with direct push access on `actava-ai/leaderboard`. External submitters should never need it — leave it off.

## Recovery: helper failed partway

The helper is **not transactional**. When it fails after copying the packet (validator, push, or `gh pr create`), it leaves valid intermediate state behind — finish manually rather than re-running:

| Failure | What's already done | What to do |
|---|---|---|
| Validator failed after copy | target dir copied | helper already cleaned up; fix producer + retry (see `references/producer-side-fixes.md`) |
| `git push` failed | branch + commit created locally | retry the push, then `gh pr create` (below) |
| `gh pr create` failed | branch pushed | rerun `gh pr create` only |

Check current state before doing anything: `git status -sb`, `git log -1 --oneline`, `gh pr list -R actava-ai/leaderboard --head <branch>`.

The commit message the helper wrote is exactly the PR title+body it would have used — reuse it:

```bash
USER=$(gh api user -q .login)
SUBJECT=$(git log -1 --pretty=format:'%s')
BODY=$(git log -1 --pretty=format:'%b')

# Push directly to the fork by URL (avoids any local-remote-naming guesswork)
git push "https://github.com/$USER/leaderboard.git" sub/<bench>/<YYYY-MM-DD>-<slug>

gh pr create -R actava-ai/leaderboard --base main \
  --head "$USER:sub/<bench>/<YYYY-MM-DD>-<slug>" \
  --title "$SUBJECT" --body "$BODY"
```

The `<user>:<branch>` head ref is required for cross-fork PRs.

## Conflict resolution: target dir already exists

A prior submission with the same `<YYYY-MM-DD>-<slug>` is on `main` or in a local branch. Pass `--on-conflict`:

- `bump-date` — recompute the dir name with today's UTC date (preferred for re-submits)
- `replace` — overwrite the existing dir (typically a maintainer action)
- `abandon` — exit cleanly

## Post-merge cleanup

After the PR merges (CI re-runs the same validator on every PR), sync the user's fork against upstream and drop the local branch:

```bash
gh repo sync <user>/leaderboard --source actava-ai/leaderboard --branch main
git checkout main && git pull --ff-only origin main
git branch -d sub/<bench>/<YYYY-MM-DD>-<slug>
```

## Manual flow (no helper)

If `scripts/submit.py` is unavailable or the user wants explicit control, see `references/manual-flow.md`.

## Inspecting a packet

Trajectories are zstd-compressed JSONL:

```bash
zstdcat <packet>/trials/<domain>/<trial_id>/agent/trajectory.jsonl.zst | jq .
```

Headline metrics are in `submission.json:results.overall` and the auto-generated `README.md`.
