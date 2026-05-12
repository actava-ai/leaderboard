"""Tests for the leaderboard's submission validator."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

# Make the validator importable
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_submission import (  # noqa: E402
    ValidationReport,
    check_directory_naming,
    check_no_unexpected_files,
    check_required_files,
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
    report = validate_packet(valid_packet)
    assert not report.has_errors(), report.errors
