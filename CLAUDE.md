# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Self-improvement protocol

This file is a living document. Whenever a session in this repo would have gone smoother
with a note here, **edit CLAUDE.md before ending the turn** — don't wait to be asked.

Add or update an entry when:

- The user corrects an approach or says "again, like I said before". Capture the rule and
  the **why** (the reason given).
- You re-discover something already explained earlier — one repeat is enough.
- A command, path, or convention was non-obvious (required grep / multiple file reads).
- A command in **Commands** turned out to be wrong, stale, or missing a flag — fix it.

Keep entries one-line rules with optional **Why:** / **How to apply:** clauses. Repo-specific
facts only — nothing discoverable from `--help`, code, or `git log`. The file is read in full
each session; entries past line ~200 lose weight, so prune cruft.

## What this repo is

`actava-ai/leaderboard` — public, **data-only** record of benchmark submissions. Submissions
land as PRs under `benchmarks/<bench>/submissions/<YYYY-MM-DD>-<slug>/`; CI validates schema +
trial integrity and labels the PR `valid-submission` / `invalid-submission` / `needs-review`.
The rendered leaderboard lives at <https://actava.ai/benchmarks> and reads `results.csv` files
out of this repo — not generated here.

This repo is **not** the producer. Packets are produced by the benchmark's tooling (e.g.
`cb submission prepare` in [`actava-ai/chi-bench`](https://github.com/actava-ai/chi-bench));
this repo only accepts and validates them.

Source-of-truth docs:

- `README.md` — user-facing submission workflow.
- `CONTRIBUTING.md` — what CI catches, reviewer protocol, resubmission policy.
- `.claude/skills/submit-to-leaderboard/SKILL.md` — non-obvious friction points (cross-fork PR
  head refs, validator dep injection, conflict resolution) for AI agents.
- `benchmarks/README.md` — how to add a new benchmark.

Keep README/CONTRIBUTING/SKILL.md in sync with any change to the submission flow or validator.

`AGENTS.md` is a symlink to this file — Codex and other AGENTS.md-aware tools read the same
guidance Claude Code does. Don't recreate it as a separate file; edit `CLAUDE.md` only.

## Submission workflow

When the user asks to submit, upload, post, or open a PR for a packet directory (e.g. produced
by `cb submission prepare`), follow the workflow in
[`.claude/skills/submit-to-leaderboard/SKILL.md`](.claude/skills/submit-to-leaderboard/SKILL.md).

That file is the source of truth for: preflight checks, local validation (which needs
`jsonschema`/`zstandard`/`pyyaml` injected via `uv run --with`), the `scripts/submit.py`
helper, partial-failure recovery, and the manual `cp + git + gh` fallback. Reference files in
the same directory cover the producer-side fixes and the manual flow in detail.

Read SKILL.md before running any submission steps — it captures non-obvious friction points
(cross-fork PR head refs, validator dep injection, conflict resolution) that aren't visible
from the source tree alone.

For ordinary repo navigation, file edits, and PR review work, the standard tools
(`Read`, `Edit`, `Bash`, `Grep`, `git`, `gh`) are sufficient — no special workflow needed.

## Commands

The validator depends on `jsonschema`, `zstandard`, `pyyaml` — **not** declared in any
`pyproject.toml` here (this repo has no Python package). Inject them with `uv run --with`:

```bash
# Validate a single packet locally (same code path as CI)
uv run --with jsonschema --with zstandard --with pyyaml \
  python scripts/validate.py /abs/path/to/<YYYY-MM-DD>-<slug>/

# Submit a packet (validates + commits + pushes to fork + opens PR)
uv run --with jsonschema --with zstandard --with pyyaml \
  python scripts/submit.py /abs/path/to/<YYYY-MM-DD>-<slug>/
#   flags: --no-fork  --no-open-pr  --on-conflict abandon|replace|bump-date
#          --leaderboard-repo actava-ai/leaderboard

# Run the unit tests for the validator and helper
uv run --with jsonschema --with zstandard --with pyyaml --with pytest \
  pytest .github/scripts/test_validate_submission.py scripts/test_submit.py
```

There is **no** lint/format config in this repo; don't add one without asking.

`scripts/validate.py` is a thin shim that re-execs `.github/scripts/validate_submission.py`
(the CI entry point) so local and CI behavior stay identical — when fixing the validator,
edit only `.github/scripts/validate_submission.py`.

## Architecture cheatsheet

```
.
├── benchmarks/
│   └── <bench>/                          # one subdirectory per benchmark, self-contained
│       ├── README.md
│       ├── schema/
│       │   ├── submission-v<N>.json      # JSON Schema for submission.json
│       │   └── known-versions.txt        # accepted dataset versions, one per line
│       └── submissions/
│           └── <YYYY-MM-DD>-<slug>/      # one dir per accepted submission
├── scripts/
│   ├── submit.py                         # fork + branch + commit + push + PR helper
│   ├── validate.py                       # local shim → .github/scripts/validate_submission.py
│   └── test_submit.py
├── .github/
│   ├── workflows/
│   │   ├── validate.yml                  # PR-time validator (read-only); uploads report artifact
│   │   └── pr-comment.yml                # workflow_run: posts comment + applies label (read-write)
│   └── scripts/
│       ├── validate_submission.py        # CI entry point + all check functions
│       ├── test_validate_submission.py
│       └── _fixtures/valid_min/2026-05-12-fixture/   # canonical valid packet
└── .claude/skills/submit-to-leaderboard/  # also pointed at by AGENTS.md (Codex)
```

Submission flow:

1. User has a packet from the producer tool (e.g. `cb submission prepare`).
2. `scripts/submit.py` reads `submission.json:dataset.name` to route into `benchmarks/<bench>/submissions/`.
3. Branch `sub/<bench>/<dir>` is created, packet committed, branch pushed to user's fork.
4. PR opened with head `<fork-owner>:<branch>` (cross-fork PRs require the `owner:branch` form).
5. CI re-runs the same validator (`.github/workflows/validate.yml` → `validate_submission.py`),
   which uploads a `pr-comment-payload` artifact (report.md/json + PR number). A second workflow
   (`pr-comment.yml`, `on: workflow_run`) downloads it and posts the sticky comment + applies the
   label. The split is mandatory: a `pull_request` run from a **fork** only gets a read-only
   GITHUB_TOKEN, so commenting/labelling from `validate.yml` fails with `Resource not accessible
   by integration` (only `workflow_run`, running trusted default-branch code, gets a write token).

The PR-diff scope check (`validate_pr_diff` in `validate_submission.py`) uses **three-dot diff**
(`base...head`) so a stale PR base SHA can't bleed in commits that have since landed on main.

## Things to remember

- **Packets are copied verbatim**, never hand-edited. If validation surfaces a producer-side
  issue (e.g. wrong dataset version pin, missing provenance key), fix it in the producer repo
  and re-prepare the packet. See `.claude/skills/submit-to-leaderboard/references/producer-side-fixes.md`.
- **Fork PRs need the two-workflow split (`validate.yml` + `pr-comment.yml`).** `workflow_run`
  always runs the **default-branch** copy of `pr-comment.yml`, so any change to the comment/label
  logic only takes effect once merged to `main`, and never comments retroactively on a run that
  finished before the merge. To label/comment an existing PR after a fix lands, re-run its validate
  workflow (`gh run rerun <id>`) or push a commit. If you rename `validate.yml`'s `name:`, update
  `pr-comment.yml`'s `workflows: ["validate submission"]` to match or the trigger silently breaks.
- **PR scope = exactly one submission dir.** PRs that touch schemas, READMEs, workflows, or
  multiple submissions fail the scope check. Meta-changes go in separate PRs (maintainers can
  apply the `meta:` label to bypass — there's no automation for that, it's a manual override
  the workflow's diff-scope check doesn't see).
- **Validator dependency injection.** `jsonschema`, `zstandard`, `pyyaml` are CI-only; running
  `python scripts/validate.py` directly will `ImportError`. Always wrap with
  `uv run --with jsonschema --with zstandard --with pyyaml ...` locally — CI installs them in
  the workflow step.
- **Cross-fork PR head ref.** When recovering from a partial helper failure, pass
  `--head "<user>:<branch>"` to `gh pr create`. Plain `<branch>` only works for same-repo PRs.
- **Validator is shared between CI and local.** Both run `validate_submission.py`. When changing
  validator behavior, run `pytest .github/scripts/test_validate_submission.py scripts/test_submit.py`
  before pushing — CI failures here block every open submission PR until fixed.
- **The fixture `_fixtures/valid_min/2026-05-12-fixture/` is the contract.** It must always
  pass `validate_packet` with zero errors. When evolving the schema or required files, update
  the fixture in the same commit; otherwise the test suite regresses.
- **Trial trajectories** are zstd-compressed JSONL. Inspect with
  `zstdcat <packet>/trials/<domain>/<id>/agent/trajectory.jsonl.zst | jq .` — line 1 is the
  ATIF header, subsequent lines are agent steps.
- **`--no-fork` is for maintainers only.** External submitters always go fork → PR; the
  helper's default does this correctly.
- **Never bypass commit hooks** (`--no-verify`, `--no-gpg-sign`). There are no commit hooks in
  this repo currently; if one is added, fix the underlying issue rather than skipping it.
