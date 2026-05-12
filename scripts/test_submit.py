"""Tests for scripts/submit.py — the optional one-command helper."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from submit import (  # noqa: E402
    SubmissionPlan,
    SubmitError,
    detect_benchmark,
    plan_submission,
)

FIXTURE_VALID = HERE.parent / ".github" / "scripts" / "_fixtures" / "valid_min" / "2026-05-12-fixture"


def test_detect_benchmark_reads_manifest(tmp_path: Path) -> None:
    pkt = tmp_path / "2026-05-12-x"
    shutil.copytree(FIXTURE_VALID, pkt)
    assert detect_benchmark(pkt) == "chi-bench"


def test_detect_benchmark_rejects_missing_manifest(tmp_path: Path) -> None:
    pkt = tmp_path / "x"
    pkt.mkdir()
    with pytest.raises(SubmitError):
        detect_benchmark(pkt)


def test_plan_submission_targets_correct_path(tmp_path: Path) -> None:
    pkt = tmp_path / "2026-05-12-myteam"
    shutil.copytree(FIXTURE_VALID, pkt)
    mf = pkt / "submission.json"
    data = json.loads(mf.read_text())
    data["submission"]["id"] = "myteam"
    mf.write_text(json.dumps(data))

    repo_root = tmp_path / "lb"
    (repo_root / "benchmarks" / "chi-bench" / "submissions").mkdir(parents=True)

    plan = plan_submission(pkt, repo_root=repo_root)
    assert plan.benchmark == "chi-bench"
    assert (
        plan.target_dir
        == repo_root / "benchmarks" / "chi-bench" / "submissions" / "2026-05-12-myteam"
    )
    assert plan.branch_name == "sub/chi-bench/2026-05-12-myteam"


def test_plan_submission_rejects_unknown_benchmark(tmp_path: Path) -> None:
    pkt = tmp_path / "2026-05-12-x"
    shutil.copytree(FIXTURE_VALID, pkt)
    mf = pkt / "submission.json"
    data = json.loads(mf.read_text())
    data["dataset"]["name"] = "ghost-bench"
    mf.write_text(json.dumps(data))

    repo_root = tmp_path / "lb"
    (repo_root / "benchmarks" / "chi-bench" / "submissions").mkdir(parents=True)

    with pytest.raises(SubmitError, match="ghost-bench"):
        plan_submission(pkt, repo_root=repo_root)


def test_plan_submission_detects_existing_target(tmp_path: Path) -> None:
    pkt = tmp_path / "2026-05-12-myteam"
    shutil.copytree(FIXTURE_VALID, pkt)
    mf = pkt / "submission.json"
    data = json.loads(mf.read_text())
    data["submission"]["id"] = "myteam"
    mf.write_text(json.dumps(data))

    repo_root = tmp_path / "lb"
    target = repo_root / "benchmarks" / "chi-bench" / "submissions" / "2026-05-12-myteam"
    target.mkdir(parents=True)

    plan = plan_submission(pkt, repo_root=repo_root)
    assert plan.target_exists is True
