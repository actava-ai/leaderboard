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
    overall = ((manifest.get("results") or {}).get("overall") or {}).get("pass_at_1")
    pct_str = f"pass@1: {overall * 100:.1f}%" if isinstance(overall, (int, float)) else "(no metric)"

    return SubmissionPlan(
        packet=packet,
        benchmark=benchmark,
        target_dir=target_dir,
        branch_name=branch,
        submission_id=sid,
        target_exists=target_dir.exists(),
        commit_subject=f"{benchmark}: {team} · {agent} · {model}",
        commit_body=(
            f"Submission `{sid}` — {pct_str}\n\n"
            f"Validated locally with scripts/validate.py."
        ),
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
