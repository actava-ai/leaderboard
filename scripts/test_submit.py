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
    render_pr_body,
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


def test_render_pr_body_includes_table_and_metadata() -> None:
    manifest = {
        "submission": {
            "id": "team-x",
            "team": "Team X",
            "contact": "x@example.com",
            "agent": "claude-code",
            "model": "anthropic/claude-opus-4-7",
            "submitted_at": "2026-05-12T14:03:11Z",
        },
        "dataset": {
            "name": "chi-bench",
            "version": "chi-bench-v1.0.0",
            "domains": ["pa_provider", "pa_um", "cm"],
        },
        "results": {
            "overall": {"pass_at_1": 0.28, "n_trials": 75, "n_tasks": 75},
            "per_domain": {
                "pa_provider": {"pass_at_1": 0.304, "n_trials": 25, "n_tasks": 25},
                "pa_um": {"pass_at_1": 0.316, "n_trials": 25, "n_tasks": 25},
                "cm": {"pass_at_1": 0.220, "n_trials": 25, "n_tasks": 25},
            },
            "mean_cost_usd": 4.21,
            "mean_walltime_s": 612.0,
        },
        "provenance": {
            "chi_bench_git_sha": "f926f8f47a748872",
            "image_digest": "sha256:abc",
            "judge_model": "claude-opus-4-7",
            "harness_version": "0.1.0",
        },
    }
    body = render_pr_body(
        manifest,
        branch_name="sub/chi-bench/2026-05-12-team-x",
        target_rel="benchmarks/chi-bench/submissions/2026-05-12-team-x",
    )
    # Headline
    assert "## chi-bench submission" in body
    assert "**Team:** Team X" in body
    assert "**Model:** `anthropic/claude-opus-4-7`" in body
    # Table: header + overall + 3 domains
    assert "| Domain | pass@1 | n_trials | n_tasks |" in body
    assert "| **Overall** | **28.0%** | 75 | 75 |" in body
    assert "| pa_provider | 30.4% | 25 | 25 |" in body
    assert "| pa_um | 31.6% | 25 | 25 |" in body
    assert "| cm | 22.0% | 25 | 25 |" in body
    # Run details
    assert "`chi-bench-v1.0.0`" in body
    assert "$4.21 / trial" in body
    assert "10.2 min / trial" in body
    assert "`f926f8f`" in body          # short SHA
    assert "`claude-opus-4-7`" in body  # judge
    # Inspect snippet uses the branch + first domain
    assert "git checkout sub/chi-bench/2026-05-12-team-x" in body
    assert "trials/pa_provider/" in body
    # Producer pointer
    assert "actava-ai/chi-bench" in body


def test_render_pr_body_handles_missing_optional_fields() -> None:
    manifest = {
        "submission": {
            "id": "x", "team": "T", "contact": "c", "agent": "a", "model": "m",
            "submitted_at": "2026-05-12T00:00:00Z",
        },
        "dataset": {"name": "chi-bench", "version": "v1", "domains": ["pa_provider"]},
        "results": {
            "overall": {"pass_at_1": 0.5, "n_trials": 25, "n_tasks": 25},
            "per_domain": {"pa_provider": {"pass_at_1": 0.5, "n_trials": 25, "n_tasks": 25}},
        },
        "provenance": {},  # all keys missing
    }
    body = render_pr_body(manifest, branch_name="b", target_rel="t")
    # Doesn't crash, leaves '?' / 'n/a' placeholders for missing fields
    assert "**Mean cost** | n/a" in body
    assert "**Mean walltime** | n/a" in body
    assert "`?`" in body
    # Optional image_digest row omitted when missing
    assert "Image digest" not in body


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


# ── git + fork + gh plumbing ─────────────────────────────────────────────────

import subprocess

from submit import (  # noqa: E402
    commit_packet,
    preflight_tools,
    resolve_conflict,
)


def test_preflight_tools_reports_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """If a required tool is absent, preflight returns a non-empty diagnostic list."""
    monkeypatch.setattr("shutil.which", lambda x: None)
    diagnostics = preflight_tools()
    assert any("git" in d for d in diagnostics)
    assert any("gh" in d for d in diagnostics)


def test_resolve_conflict_abandon() -> None:
    assert resolve_conflict(True, "abandon", interactive=False) == "abandon"


def test_resolve_conflict_replace() -> None:
    assert resolve_conflict(True, "replace", interactive=False) == "replace"


def test_resolve_conflict_no_conflict() -> None:
    assert resolve_conflict(False, None, interactive=False) == "proceed"


def test_resolve_conflict_requires_choice_in_noninteractive() -> None:
    with pytest.raises(SubmitError, match="on-conflict"):
        resolve_conflict(True, None, interactive=False)


def test_commit_packet_in_git_repo(tmp_path: Path) -> None:
    """Smoke test of the git plumbing inside a throwaway repo."""
    repo = tmp_path / "lb"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    (repo / ".gitkeep").touch()
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)

    target = repo / "benchmarks" / "chi-bench" / "submissions" / "2026-05-12-x"
    shutil.copytree(FIXTURE_VALID, target)

    plan = SubmissionPlan(
        packet=target,
        benchmark="chi-bench",
        target_dir=target,
        branch_name="sub/chi-bench/2026-05-12-x",
        submission_id="x",
        target_exists=False,
        commit_subject="chi-bench: T",
        commit_body="body",
    )
    commit_packet(plan, repo_root=repo)
    log = subprocess.run(
        ["git", "log", "-1", "--format=%s"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert log == "chi-bench: T"
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert branch == "sub/chi-bench/2026-05-12-x"
