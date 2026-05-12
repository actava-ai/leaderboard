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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Submit a packet to actava-ai/leaderboard.")
    parser.add_argument("packet", type=Path)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument("--no-fork", action="store_true")
    parser.add_argument("--no-open-pr", action="store_true")
    parser.add_argument("--on-conflict", choices=("abandon", "replace", "bump-date"))
    parser.add_argument("--leaderboard-repo", default=DEFAULT_REPO)
    args = parser.parse_args(argv)

    try:
        plan = plan_submission(args.packet, repo_root=args.repo_root)
    except SubmitError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"Planned: copy {plan.packet} → {plan.target_dir.relative_to(args.repo_root)}")
    print(f"         branch: {plan.branch_name}")
    print(f"         subject: {plan.commit_subject}")
    print("(git+gh steps land in Task 19.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
