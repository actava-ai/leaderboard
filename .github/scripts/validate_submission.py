#!/usr/bin/env python3
"""Submission validator for actava-ai/leaderboard.

Runs both in CI (.github/workflows/validate.yml) and locally via
scripts/validate.py. No GitHub-specific dependencies in the core checks.

Usage:
    python validate_submission.py <path-to-submission-dir>
    python validate_submission.py --base-ref <sha> --head-ref <sha> \
        --report-md <path> --report-json <path>
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import re
import sys
from pathlib import Path

DIR_NAME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-([a-z0-9][a-z0-9_-]{0,63})$")

REQUIRED_TOP_LEVEL_FILES = (
    "submission.json",
    "results.csv",
    "sub.yaml",
    "provenance.json",
    "README.md",
)

ALLOWED_EXTENSIONS = frozenset({".json", ".csv", ".yaml", ".yml", ".md", ".txt", ".zst"})
ALLOWED_HIDDEN_NAMES = frozenset({".gitkeep"})


@dataclasses.dataclass
class ValidationReport:
    errors: list[str] = dataclasses.field(default_factory=list)
    warnings: list[str] = dataclasses.field(default_factory=list)
    info: dict[str, object] = dataclasses.field(default_factory=dict)

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def has_errors(self) -> bool:
        return bool(self.errors)


def check_directory_naming(
    packet_dir: Path, report: ValidationReport, manifest_id: str | None
) -> None:
    """Rule 2 of spec §4.2: <YYYY-MM-DD>-<slug>/, slug equals manifest id, date ≤ today UTC."""
    name = packet_dir.name
    m = DIR_NAME_RE.match(name)
    if not m:
        report.err(
            f"Directory name '{name}' does not match required pattern "
            f"^\\d{{4}}-\\d{{2}}-\\d{{2}}-[a-z0-9][a-z0-9_-]{{0,63}}$"
        )
        return
    year, month, day, slug = m.group(1), m.group(2), m.group(3), m.group(4)
    try:
        date_val = dt.date(int(year), int(month), int(day))
    except ValueError as e:
        report.err(f"Directory name '{name}' has an invalid date: {e}")
        return
    today = dt.datetime.now(dt.UTC).date()
    if date_val > today:
        report.err(
            f"Directory name '{name}' has a future date ({date_val}); "
            f"must be ≤ today UTC ({today})"
        )
    if manifest_id is not None and slug != manifest_id:
        report.err(
            f"Directory slug '{slug}' does not match submission.id '{manifest_id}' "
            f"in submission.json"
        )


def check_required_files(packet_dir: Path, report: ValidationReport) -> None:
    """Rule 3 of spec §4.2: required top-level files + at least one trial result.json."""
    for name in REQUIRED_TOP_LEVEL_FILES:
        if not (packet_dir / name).is_file():
            report.err(f"Required file missing: {name}")

    trials_dir = packet_dir / "trials"
    if not trials_dir.is_dir():
        report.err("Required directory missing: trials/")
        return
    result_files = list(trials_dir.glob("*/*/result.json"))
    if not result_files:
        report.err("No trial result.json files found under trials/<domain>/<trial_id>/")


def check_no_unexpected_files(packet_dir: Path, report: ValidationReport) -> None:
    """Rule 4 of spec §4.2: reject .zip, .bak, hidden files (except .gitkeep), path traversal."""
    for path in packet_dir.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(packet_dir)
        name = path.name
        if name.startswith(".") and name not in ALLOWED_HIDDEN_NAMES:
            report.err(f"Unexpected hidden file: {rel}")
            continue
        if any(part == ".." for part in rel.parts):
            report.err(f"Path traversal in {rel}")
            continue
        suffixes = "".join(path.suffixes)
        if suffixes.endswith(".bak"):
            report.err(f"Unexpected backup file: {rel}")
            continue
        if path.suffix == ".zip":
            report.err(f"Unexpected zip file: {rel}")
            continue
        if path.suffix and path.suffix not in ALLOWED_EXTENSIONS:
            report.err(f"Unexpected file extension '{path.suffix}': {rel}")


def _load_manifest_id(packet_dir: Path) -> str | None:
    mf = packet_dir / "submission.json"
    if not mf.is_file():
        return None
    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    sub = data.get("submission") or {}
    sid = sub.get("id")
    return sid if isinstance(sid, str) else None


def validate_packet(packet_dir: Path) -> ValidationReport:
    """Top-level entry point — runs all checks against a single packet directory.

    Subsequent tasks extend this with schema, results.csv consistency,
    per-trial integrity, and soft warnings.
    """
    report = ValidationReport()
    if not packet_dir.is_dir():
        report.err(f"Not a directory: {packet_dir}")
        return report

    manifest_id = _load_manifest_id(packet_dir)
    check_directory_naming(packet_dir, report, manifest_id)
    check_required_files(packet_dir, report)
    check_no_unexpected_files(packet_dir, report)
    return report


def _print_report(report: ValidationReport, packet_dir: Path) -> int:
    if report.has_errors():
        print(f"❌ {packet_dir.name}: {len(report.errors)} error(s)", file=sys.stderr)
        for e in report.errors:
            print(f"  - {e}", file=sys.stderr)
    else:
        print(f"✅ {packet_dir.name}: validation passed")
    if report.warnings:
        print(f"⚠️  {len(report.warnings)} warning(s)", file=sys.stderr)
        for w in report.warnings:
            print(f"  - {w}", file=sys.stderr)
    return 1 if report.has_errors() else 0


def _main_single(packet_dir: Path) -> int:
    report = validate_packet(packet_dir)
    return _print_report(report, packet_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a leaderboard submission packet.")
    parser.add_argument(
        "path", nargs="?", type=Path, help="Path to a single submission directory."
    )
    parser.add_argument("--base-ref", help="(CI) PR base SHA — used to compute diff scope.")
    parser.add_argument("--head-ref", help="(CI) PR head SHA — used to compute diff scope.")
    parser.add_argument("--report-md", type=Path, help="(CI) write Markdown report to this path.")
    parser.add_argument(
        "--report-json", type=Path, help="(CI) write structured JSON report to this path."
    )
    args = parser.parse_args(argv)

    if args.path is None:
        parser.error("path is required (CI mode arrives in a later task)")
    return _main_single(args.path)


if __name__ == "__main__":
    sys.exit(main())
