#!/usr/bin/env python3
"""One-command helper for submitting a packet to actava-ai/leaderboard.

Manual flow (no helper):
    cp -r <packet> benchmarks/<bench>/submissions/
    python scripts/validate.py benchmarks/<bench>/submissions/<dir>
    git checkout -b sub/<bench>/<dir>
    git add benchmarks/<bench>/submissions/<dir>/
    git commit -m "<bench>: <team> · <agent> · <model>"
    git push origin sub/<bench>/<dir>
    gh pr create --base main

This helper does the same steps with auto-detection of the benchmark from
the packet's submission.json:dataset.name, runs the validator before
committing, and handles fork-based PRs for outside contributors.

Usage:
    python scripts/submit.py <path-to-packet>
        [--no-fork]
        [--no-open-pr]
        [--on-conflict abandon|replace|bump-date]
        [--leaderboard-repo actava-ai/leaderboard]
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT_DEFAULT = Path(__file__).resolve().parent.parent
DEFAULT_REPO = "actava-ai/leaderboard"


class SubmitError(Exception):
    """User-facing error during submission. The message is printed verbatim."""


@dataclasses.dataclass
class SubmissionPlan:
    packet: Path
    benchmark: str
    target_dir: Path
    branch_name: str
    submission_id: str
    target_exists: bool
    commit_subject: str
    commit_body: str


def _read_manifest(packet: Path) -> dict:
    mf = packet / "submission.json"
    if not mf.is_file():
        raise SubmitError(f"Packet has no submission.json: {packet}")
    try:
        return json.loads(mf.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SubmitError(f"submission.json is malformed: {e}") from None


def detect_benchmark(packet: Path) -> str:
    manifest = _read_manifest(packet)
    ds = manifest.get("dataset") or {}
    name = ds.get("name")
    if not isinstance(name, str) or not name:
        raise SubmitError("submission.json:dataset.name is missing")
    return name


def _pct(v: object) -> str:
    return f"{v * 100:.1f}%" if isinstance(v, (int, float)) else "—"


def _short_sha(s: object) -> str:
    return s[:7] if isinstance(s, str) and len(s) >= 7 else "?"


def render_pr_body(manifest: dict, branch_name: str, target_rel: str) -> str:
    """Build a richly-formatted PR body from the packet's submission.json.

    The same string is used as the git commit body and the `gh pr create --body`
    payload (a long markdown-flavored commit message is fine; GitHub renders the
    PR body as markdown regardless).
    """
    sub = manifest.get("submission") or {}
    ds = manifest.get("dataset") or {}
    res = manifest.get("results") or {}
    prov = manifest.get("provenance") or {}

    overall = res.get("overall") or {}
    per_domain = res.get("per_domain") or {}
    domains_in_order = list(ds.get("domains") or per_domain.keys())

    bench = ds.get("name", "?")
    version = ds.get("version", "?")
    sid = sub.get("id", "?")
    submitted = (sub.get("submitted_at") or "?").split("T", 1)[0]

    # Results table
    table = [
        "| Domain | pass@1 | n_trials | n_tasks |",
        "|---|---:|---:|---:|",
        f"| **Overall** | **{_pct(overall.get('pass_at_1'))}** | "
        f"{overall.get('n_trials', '?')} | {overall.get('n_tasks', '?')} |",
    ]
    for dom in domains_in_order:
        score = per_domain.get(dom) or {}
        table.append(
            f"| {dom} | {_pct(score.get('pass_at_1'))} | "
            f"{score.get('n_trials', '?')} | {score.get('n_tasks', '?')} |"
        )

    # Run details
    mean_cost = res.get("mean_cost_usd")
    mean_walltime = res.get("mean_walltime_s")
    cost_str = f"${mean_cost:.2f} / trial" if isinstance(mean_cost, (int, float)) else "n/a"
    walltime_str = (
        f"{mean_walltime / 60:.1f} min / trial"
        if isinstance(mean_walltime, (int, float))
        else "n/a"
    )

    run_table = [
        "| | |",
        "|---|---|",
        f"| **Dataset** | `{version}` |",
        f"| **Mean cost** | {cost_str} |",
        f"| **Mean walltime** | {walltime_str} |",
        f"| **Judge** | `{prov.get('judge_model', '?')}` |",
        f"| **{bench} SHA** | `{_short_sha(prov.get('chi_bench_git_sha'))}` |",
        f"| **Harness version** | `{prov.get('harness_version', '?')}` |",
    ]
    image_digest = prov.get("image_digest")
    if image_digest:
        run_table.append(f"| **Image digest** | `{image_digest}` |")

    target_dir_name = target_rel.split("/")[-1]
    first_domain = domains_in_order[0] if domains_in_order else "<domain>"

    body = f"""## {bench} submission

**Team:** {sub.get('team', '?')}
**Contact:** {sub.get('contact', '?')}
**Agent:** `{sub.get('agent', '?')}`
**Model:** `{sub.get('model', '?')}`
**Submitted:** {submitted}
**Submission id:** `{sid}`

### Results — pass@1

{chr(10).join(table)}

### Run details

{chr(10).join(run_table)}

### Validation

- ✅ Validated locally with `python scripts/validate.py {target_rel}` before opening this PR.
- CI runs the identical checks (`.github/workflows/validate.yml`); see the sticky comment for the full report.

### Inspect a trajectory

```bash
git fetch && git checkout {branch_name}
zstdcat {target_rel}/trials/{first_domain}/<trial_id>/agent/trajectory.jsonl.zst | jq .
```

The packet is committed as plain files; click into [`{target_rel}/`]({target_rel}/) on the **Files changed** tab to browse the manifest, headline metrics (auto-generated `README.md`), and the per-trial tree directly from the PR.

### Producer

Generated by [actava-ai/chi-bench](https://github.com/actava-ai/chi-bench) via `cb submission prepare`. See [`docs/submission-packet.md`](https://github.com/actava-ai/chi-bench/blob/main/docs/submission-packet.md) for the cross-benchmark packet contract.

---
<details>
<summary>Submitter checklist (auto-checked by <code>scripts/submit.py</code>)</summary>

- [x] Packet produced with the benchmark's official tooling
- [x] Local validator passed before opening this PR
- [x] Dataset version matches the data revision actually used
- [x] Pass@1 only (extra trials, if any, kept locally)
</details>
"""
    return body


def plan_submission(packet: Path, repo_root: Path = REPO_ROOT_DEFAULT) -> SubmissionPlan:
    manifest = _read_manifest(packet)
    sub = manifest.get("submission") or {}
    sid = sub.get("id")
    if not isinstance(sid, str):
        raise SubmitError("submission.json:submission.id is missing")

    benchmark = detect_benchmark(packet)
    bench_root = repo_root / "benchmarks" / benchmark
    if not bench_root.is_dir():
        raise SubmitError(
            f"Benchmark '{benchmark}' is not registered in this leaderboard "
            f"(no {bench_root} directory). Register it first or fix dataset.name."
        )
    submissions_root = bench_root / "submissions"
    submissions_root.mkdir(parents=True, exist_ok=True)

    dir_name = packet.name
    target_dir = submissions_root / dir_name
    branch = f"sub/{benchmark}/{dir_name}"

    team = sub.get("team", "?")
    agent = sub.get("agent", "?")
    model = sub.get("model", "?")

    target_rel = str(target_dir.relative_to(repo_root))
    commit_body = render_pr_body(manifest, branch_name=branch, target_rel=target_rel)

    return SubmissionPlan(
        packet=packet,
        benchmark=benchmark,
        target_dir=target_dir,
        branch_name=branch,
        submission_id=sid,
        target_exists=target_dir.exists(),
        commit_subject=f"{benchmark}: {team} · {agent} · {model}",
        commit_body=commit_body,
    )


def copy_packet(plan: SubmissionPlan) -> None:
    if plan.target_dir.exists():
        shutil.rmtree(plan.target_dir)
    shutil.copytree(plan.packet, plan.target_dir)


def _run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)


def preflight_tools() -> list[str]:
    """Return human-readable diagnostics for missing/misconfigured tools.

    Empty list = ready to submit.
    """
    diagnostics: list[str] = []
    for tool in ("git", "gh"):
        if shutil.which(tool) is None:
            diagnostics.append(f"missing tool: {tool} (install and retry)")
    try:
        _run(["gh", "auth", "status"])
    except (FileNotFoundError, subprocess.CalledProcessError):
        diagnostics.append("gh CLI not authenticated — run `gh auth login`")
    try:
        out = _run(["git", "config", "--get", "user.email"]).stdout.strip()
        if not out:
            diagnostics.append(
                "git user.email not set — run `git config --global user.email <you>`"
            )
    except (FileNotFoundError, subprocess.CalledProcessError):
        diagnostics.append(
            "git user.email not set — run `git config --global user.email <you>`"
        )
    return diagnostics


def resolve_conflict(target_exists: bool, on_conflict: str | None, interactive: bool) -> str:
    """Decide what to do when the target submission directory already exists.

    Returns: 'proceed' (no conflict), 'abandon' (exit), 'replace' (overwrite),
    'bump-date' (recompute the target with today's date).
    """
    if not target_exists:
        return "proceed"
    if on_conflict is not None:
        return on_conflict
    if not interactive:
        raise SubmitError(
            "target directory already exists; pass --on-conflict abandon|replace|bump-date"
        )
    choice = input("Target exists. [a]bandon / [r]eplace / [b]ump-date? ").strip().lower()
    return {"a": "abandon", "r": "replace", "b": "bump-date"}.get(choice, "abandon")


def _bump_date(plan: SubmissionPlan) -> SubmissionPlan:
    today = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
    new_name = f"{today}-{plan.submission_id}"
    new_target = plan.target_dir.parent / new_name
    new_branch = f"sub/{plan.benchmark}/{new_name}"
    return dataclasses.replace(
        plan,
        target_dir=new_target,
        branch_name=new_branch,
        target_exists=new_target.exists(),
    )


def _run_validator(packet_dir: Path, repo_root: Path) -> None:
    """Run the CI validator against the (already-copied) packet; raise on failure."""
    proc = subprocess.run(
        [
            sys.executable,
            str(repo_root / ".github" / "scripts" / "validate_submission.py"),
            str(packet_dir),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SubmitError(f"validation failed:\n{proc.stderr}")


def commit_packet(plan: SubmissionPlan, repo_root: Path) -> None:
    """Create the branch, stage the submission subtree, commit."""
    _run(["git", "checkout", "-b", plan.branch_name], cwd=repo_root)
    rel_target = plan.target_dir.relative_to(repo_root)
    _run(["git", "add", str(rel_target)], cwd=repo_root)
    _run(
        ["git", "commit", "-m", plan.commit_subject, "-m", plan.commit_body],
        cwd=repo_root,
    )


def _ensure_fork(repo_slug: str) -> str:
    """gh repo fork (idempotent). Returns the fork's owner/repo slug."""
    proc = _run(["gh", "api", "user", "-q", ".login"])
    user = proc.stdout.strip()
    _run(["gh", "repo", "fork", repo_slug, "--clone=false", "--remote=false"])
    return f"{user}/{repo_slug.split('/')[-1]}"


def push_and_open_pr(
    plan: SubmissionPlan,
    repo_root: Path,
    leaderboard_repo: str,
    no_fork: bool,
    no_open_pr: bool,
) -> str | None:
    """Push the branch (to fork or directly) and open a PR. Returns the PR URL or None."""
    if no_fork:
        push_target_url = f"https://github.com/{leaderboard_repo}.git"
        head_ref = plan.branch_name
    else:
        fork_slug = _ensure_fork(leaderboard_repo)
        push_target_url = f"https://github.com/{fork_slug}.git"
        head_ref = f"{fork_slug.split('/')[0]}:{plan.branch_name}"

    _run(["git", "push", push_target_url, plan.branch_name], cwd=repo_root)
    if no_open_pr:
        return None

    proc = _run(
        [
            "gh", "pr", "create",
            "-R", leaderboard_repo,
            "--base", "main",
            "--head", head_ref,
            "--title", plan.commit_subject,
            "--body", plan.commit_body,
        ],
        cwd=repo_root,
    )
    return proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Submit a packet to actava-ai/leaderboard.")
    parser.add_argument("packet", type=Path)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument("--no-fork", action="store_true")
    parser.add_argument("--no-open-pr", action="store_true")
    parser.add_argument("--on-conflict", choices=("abandon", "replace", "bump-date"))
    parser.add_argument("--leaderboard-repo", default=DEFAULT_REPO)
    args = parser.parse_args(argv)

    diagnostics = preflight_tools()
    if diagnostics:
        print("ERROR: cannot submit. Resolve before retrying:", file=sys.stderr)
        for d in diagnostics:
            print(f"  [✗] {d}", file=sys.stderr)
        return 1

    try:
        plan = plan_submission(args.packet, repo_root=args.repo_root)
    except SubmitError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    decision = resolve_conflict(
        target_exists=plan.target_exists,
        on_conflict=args.on_conflict,
        interactive=sys.stdin.isatty(),
    )
    if decision == "abandon":
        print("Abandoned (no changes made).")
        return 0
    if decision == "bump-date":
        plan = _bump_date(plan)
        if plan.target_exists:
            print(f"ERROR: bumped target also exists: {plan.target_dir}", file=sys.stderr)
            return 1

    copy_packet(plan)
    try:
        _run_validator(plan.target_dir, args.repo_root)
    except SubmitError as e:
        shutil.rmtree(plan.target_dir, ignore_errors=True)
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    commit_packet(plan, repo_root=args.repo_root)
    try:
        url = push_and_open_pr(
            plan,
            repo_root=args.repo_root,
            leaderboard_repo=args.leaderboard_repo,
            no_fork=args.no_fork,
            no_open_pr=args.no_open_pr,
        )
    except subprocess.CalledProcessError as e:
        print(f"ERROR: git/gh failed:\n{e.stderr}", file=sys.stderr)
        return 1

    print(f"✅ Submitted: {plan.target_dir.relative_to(args.repo_root)}")
    if url:
        print(f"   PR: {url}")
    else:
        print("   (PR not opened; pass without --no-open-pr to open one.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
