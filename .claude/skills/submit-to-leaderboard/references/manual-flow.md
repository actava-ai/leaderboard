# Manual submission flow (no helper)

Use when `scripts/submit.py` is unavailable, broken, or the user wants explicit control over each step. The CI validator runs the same code path either way.

Assumes cwd is a clone of the user's fork of `actava-ai/leaderboard` (if not, `gh repo fork actava-ai/leaderboard --clone=true` first).

```bash
PACKET=/abs/path/to/<YYYY-MM-DD>-<slug>
BENCH=$(python -c "import json; print(json.load(open('$PACKET/submission.json'))['dataset']['name'])")
DIRNAME=$(basename "$PACKET")
BRANCH="sub/$BENCH/$DIRNAME"
USER=$(gh api user -q .login)

cp -r "$PACKET" "benchmarks/$BENCH/submissions/"

uv run --with jsonschema --with zstandard --with pyyaml \
  python scripts/validate.py "benchmarks/$BENCH/submissions/$DIRNAME"

git checkout -b "$BRANCH"
git add "benchmarks/$BENCH/submissions/$DIRNAME/"

# Match the helper's commit-message format:
#   subject: <bench>: <team> · <agent> · <model>
#   body:    markdown PR body (rendered as the PR body too)
TEAM=$(python -c "import json; print(json.load(open('$PACKET/submission.json'))['submission']['team'])")
AGENT=$(python -c "import json; print(json.load(open('$PACKET/submission.json'))['submission']['agent'])")
MODEL=$(python -c "import json; print(json.load(open('$PACKET/submission.json'))['submission']['model'])")
git commit -m "$BENCH: $TEAM · $AGENT · $MODEL"   # add -m "<body>" if writing a rich body

# Push to the fork (by URL, no local remote-naming assumptions) and open a cross-fork PR
git push "https://github.com/$USER/leaderboard.git" "$BRANCH"
gh pr create -R actava-ai/leaderboard --base main --head "$USER:$BRANCH"
```

For a rich PR body matching what the helper emits, copy from `scripts/submit.py:render_pr_body()` — it's the source of truth.
