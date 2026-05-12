"""Tests for the leaderboard's submission validator."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

# Make the validator importable
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import json

from validate_submission import (  # noqa: E402
    ValidationReport,
    check_directory_naming,
    check_no_unexpected_files,
    check_provenance,
    check_required_files,
    check_results_csv_consistency,
    check_schema,
    validate_packet,
)

FIXTURE_VALID = HERE / "_fixtures" / "valid_min" / "2026-05-12-fixture"


@pytest.fixture
def valid_packet(tmp_path: Path) -> Path:
    """Copy the canonical valid fixture into tmp_path so tests can mutate it."""
    dst = tmp_path / "2026-05-12-fixture"
    shutil.copytree(FIXTURE_VALID, dst)
    return dst


def test_directory_naming_accepts_valid(valid_packet: Path) -> None:
    report = ValidationReport()
    check_directory_naming(valid_packet, report, manifest_id="fixture")
    assert not report.has_errors(), report.errors


@pytest.mark.parametrize(
    "bad",
    [
        "2026-13-99-fixture",
        "fixture",
        "2026-05-12-Fixture",
        "2026-05-12-",
        "20260512-fixture",
    ],
)
def test_directory_naming_rejects_invalid(tmp_path: Path, bad: str) -> None:
    p = tmp_path / bad
    p.mkdir()
    report = ValidationReport()
    check_directory_naming(p, report, manifest_id="fixture")
    assert report.has_errors()


def test_directory_naming_rejects_future_date(tmp_path: Path) -> None:
    p = tmp_path / "2099-12-31-fixture"
    p.mkdir()
    report = ValidationReport()
    check_directory_naming(p, report, manifest_id="fixture")
    assert any("future" in e.lower() for e in report.errors)


def test_directory_naming_rejects_slug_mismatch(tmp_path: Path) -> None:
    p = tmp_path / "2026-05-12-different-slug"
    p.mkdir()
    report = ValidationReport()
    check_directory_naming(p, report, manifest_id="fixture")
    assert any("submission.id" in e for e in report.errors)


def test_required_files_present(valid_packet: Path) -> None:
    report = ValidationReport()
    check_required_files(valid_packet, report)
    assert not report.has_errors(), report.errors


@pytest.mark.parametrize(
    "missing",
    [
        "submission.json",
        "results.csv",
        "sub.yaml",
        "provenance.json",
        "README.md",
    ],
)
def test_required_files_missing(valid_packet: Path, missing: str) -> None:
    (valid_packet / missing).unlink()
    report = ValidationReport()
    check_required_files(valid_packet, report)
    assert any(missing in e for e in report.errors)


def test_required_files_missing_trial(valid_packet: Path) -> None:
    shutil.rmtree(valid_packet / "trials")
    report = ValidationReport()
    check_required_files(valid_packet, report)
    assert any("trial" in e.lower() for e in report.errors)


def test_no_unexpected_files_clean(valid_packet: Path) -> None:
    report = ValidationReport()
    check_no_unexpected_files(valid_packet, report)
    assert not report.has_errors()


def test_no_unexpected_files_rejects_zip(valid_packet: Path) -> None:
    (valid_packet / "bonus.zip").write_bytes(b"PK\x03\x04")
    report = ValidationReport()
    check_no_unexpected_files(valid_packet, report)
    assert any(".zip" in e for e in report.errors)


def test_no_unexpected_files_rejects_bak(valid_packet: Path) -> None:
    (valid_packet / "sub.yaml.bak").write_text("")
    report = ValidationReport()
    check_no_unexpected_files(valid_packet, report)
    assert any(".bak" in e for e in report.errors)


def test_no_unexpected_files_rejects_hidden(valid_packet: Path) -> None:
    (valid_packet / ".DS_Store").write_bytes(b"")
    report = ValidationReport()
    check_no_unexpected_files(valid_packet, report)
    assert any(".DS_Store" in e for e in report.errors)


def test_validate_packet_end_to_end_passes_on_valid(valid_packet: Path) -> None:
    """The full validate_packet() entry point should accept the canonical fixture."""
    report = validate_packet(valid_packet, repo_root=HERE.parent.parent)
    assert not report.has_errors(), report.errors


# ── Schema check ────────────────────────────────────────────────────────────

REPO_ROOT = HERE.parent.parent  # leaderboard/


def test_schema_accepts_valid(valid_packet: Path) -> None:
    report = ValidationReport()
    check_schema(valid_packet, report, repo_root=REPO_ROOT)
    assert not report.has_errors(), report.errors


def test_schema_rejects_bad_envelope(valid_packet: Path) -> None:
    """Mutate submission.json to violate the schema."""
    mf = valid_packet / "submission.json"
    data = json.loads(mf.read_text())
    data["submission"]["id"] = "INVALID-UPPERCASE"
    mf.write_text(json.dumps(data))
    report = ValidationReport()
    check_schema(valid_packet, report, repo_root=REPO_ROOT)
    assert report.has_errors()
    assert any("submission" in e.lower() and "id" in e.lower() for e in report.errors)


def test_schema_missing_schema_file(valid_packet: Path) -> None:
    """submission.json references a schema that doesn't exist."""
    mf = valid_packet / "submission.json"
    data = json.loads(mf.read_text())
    data["schema"] = "fake-bench/submission/v99"
    mf.write_text(json.dumps(data))
    report = ValidationReport()
    check_schema(valid_packet, report, repo_root=REPO_ROOT)
    assert any("schema file not found" in e.lower() for e in report.errors)


# ── results.csv consistency ─────────────────────────────────────────────────


def test_results_csv_matches_manifest(valid_packet: Path) -> None:
    report = ValidationReport()
    check_results_csv_consistency(valid_packet, report)
    assert not report.has_errors(), report.errors


def test_results_csv_pass_at_1_mismatch(valid_packet: Path) -> None:
    csv = valid_packet / "results.csv"
    txt = csv.read_text()
    # Replace the overall row's 1.0 pass_at_1 with 0.5
    new = txt.replace(",overall,1.0,", ",overall,0.5,", 1)
    csv.write_text(new)
    report = ValidationReport()
    check_results_csv_consistency(valid_packet, report)
    assert any("overall" in e.lower() and "pass_at_1" in e for e in report.errors)


def test_results_csv_wrong_submission_id(valid_packet: Path) -> None:
    csv = valid_packet / "results.csv"
    txt = csv.read_text()
    csv.write_text(txt.replace(",fixture,", ",other,"))
    report = ValidationReport()
    check_results_csv_consistency(valid_packet, report)
    assert any("submission_id" in e for e in report.errors)


# ── provenance ──────────────────────────────────────────────────────────────


def test_provenance_accepts_valid(valid_packet: Path) -> None:
    report = ValidationReport()
    check_provenance(valid_packet, report)
    assert not report.has_errors(), report.errors


def test_provenance_missing_required_key(valid_packet: Path) -> None:
    pf = valid_packet / "provenance.json"
    data = json.loads(pf.read_text())
    del data["chi_bench_git_sha"]
    pf.write_text(json.dumps(data))
    report = ValidationReport()
    check_provenance(valid_packet, report)
    assert any("chi_bench_git_sha" in e for e in report.errors)
