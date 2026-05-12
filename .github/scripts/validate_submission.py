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


def _read_manifest(packet_dir: Path) -> dict | None:
    try:
        return json.loads((packet_dir / "submission.json").read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def check_schema(packet_dir: Path, report: ValidationReport, repo_root: Path) -> None:
    """Rule 5: submission.json validates against benchmarks/<bench>/schema/submission-v<N>.json."""
    import jsonschema

    manifest = _read_manifest(packet_dir)
    if manifest is None:
        report.err("submission.json is missing or malformed JSON")
        return
    schema_field = manifest.get("schema")
    if not isinstance(schema_field, str) or schema_field.count("/") != 2:
        report.err(
            f"submission.json:schema must be '<bench>/submission/v<N>'; got {schema_field!r}"
        )
        return
    bench, kind, vname = schema_field.split("/", 2)
    if kind != "submission":
        report.err(f"Only 'submission' schemas supported at this validator version; got '{kind}'")
        return
    schema_path = repo_root / "benchmarks" / bench / "schema" / f"submission-{vname}.json"
    if not schema_path.is_file():
        report.err(f"Schema file not found for '{schema_field}': expected {schema_path}")
        return
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        report.err(f"Schema file {schema_path} is malformed JSON: {e}")
        return
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(manifest), key=lambda e: list(e.absolute_path))
    for err in errors:
        path = "/".join(str(p) for p in err.absolute_path) or "<root>"
        report.err(f"submission.json schema violation at {path}: {err.message}")


def check_results_csv_consistency(packet_dir: Path, report: ValidationReport) -> None:
    """Rule 6: results.csv rows exactly match the manifest's results.overall / results.per_domain."""
    import csv as _csv

    manifest = _read_manifest(packet_dir)
    if manifest is None:
        return
    csv_path = packet_dir / "results.csv"
    if not csv_path.is_file():
        report.err("results.csv missing")
        return

    sub_id = (manifest.get("submission") or {}).get("id")
    results = manifest.get("results") or {}
    per_domain = results.get("per_domain") or {}
    overall = results.get("overall") or {}

    expected_rows = 1 + len(per_domain)
    with csv_path.open(encoding="utf-8") as fh:
        rows = list(_csv.DictReader(fh))

    if len(rows) != expected_rows:
        report.err(
            f"results.csv has {len(rows)} rows, expected {expected_rows} "
            f"(1 overall + {len(per_domain)} per_domain)"
        )

    seen_domains: set[str] = set()
    for row in rows:
        row_sub_id = row.get("submission_id")
        if row_sub_id != sub_id:
            report.err(
                f"results.csv row submission_id={row_sub_id!r} does not match "
                f"submission.json id={sub_id!r}"
            )
        domain = row.get("domain")
        if domain == "overall":
            _compare_score_row(row, overall, "overall", report)
            seen_domains.add("overall")
        elif domain in per_domain:
            _compare_score_row(row, per_domain[domain], domain, report)
            seen_domains.add(domain)
        else:
            report.err(f"results.csv has unexpected domain row: {domain!r}")

    if "overall" not in seen_domains:
        report.err("results.csv missing the overall row")
    for d in per_domain:
        if d not in seen_domains:
            report.err(f"results.csv missing row for domain '{d}'")


def _compare_score_row(row: dict, score: dict, label: str, report: ValidationReport) -> None:
    for field in ("pass_at_1", "n_trials", "n_tasks"):
        if field not in score:
            continue
        csv_val = row.get(field)
        if csv_val is None:
            report.err(f"results.csv row '{label}' missing field '{field}'")
            continue
        manifest_val = score[field]
        try:
            if isinstance(manifest_val, int):
                csv_typed: float | int = int(csv_val)
            else:
                csv_typed = float(csv_val)
        except ValueError:
            report.err(f"results.csv row '{label}' field '{field}' is not numeric: {csv_val!r}")
            continue
        if isinstance(manifest_val, float):
            if abs(csv_typed - manifest_val) > 1e-9:
                report.err(
                    f"results.csv row '{label}' field '{field}' = {csv_typed} "
                    f"!= manifest {manifest_val}"
                )
        else:
            if csv_typed != manifest_val:
                report.err(
                    f"results.csv row '{label}' field '{field}' = {csv_typed} "
                    f"!= manifest {manifest_val}"
                )


def check_provenance(packet_dir: Path, report: ValidationReport) -> None:
    """Rule 7: provenance.json present with required keys."""
    pf = packet_dir / "provenance.json"
    if not pf.is_file():
        report.err("provenance.json missing")
        return
    try:
        data = json.loads(pf.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        report.err(f"provenance.json malformed: {e}")
        return
    if not isinstance(data, dict):
        report.err("provenance.json must be a JSON object")
        return
    required = ("chi_bench_git_sha", "image_digest", "judge_model", "harness_version")
    for k in required:
        if k not in data:
            report.err(f"provenance.json missing required key: {k}")


def _resolve_repo_root(packet_dir: Path) -> Path:
    """Walk up from packet_dir to find the leaderboard repo root (contains 'benchmarks/')."""
    cur = packet_dir.resolve()
    for parent in (cur, *cur.parents):
        if (parent / "benchmarks").is_dir() and (parent / ".github").is_dir():
            return parent
    return cur.parent.parent.parent.parent


def validate_packet(packet_dir: Path, repo_root: Path | None = None) -> ValidationReport:
    """Top-level entry point — runs all checks against a single packet directory.

    ``repo_root`` is the leaderboard repo root (the one containing
    ``benchmarks/`` and ``.github/``). When omitted, it's resolved by walking
    up from ``packet_dir``; pass it explicitly when the packet lives outside
    the repo tree (e.g. in tests or pre-PR validation of a freshly-prepared
    packet).
    """
    report = ValidationReport()
    if not packet_dir.is_dir():
        report.err(f"Not a directory: {packet_dir}")
        return report

    manifest_id = _load_manifest_id(packet_dir)
    rr = repo_root if repo_root is not None else _resolve_repo_root(packet_dir)

    check_directory_naming(packet_dir, report, manifest_id)
    check_required_files(packet_dir, report)
    check_no_unexpected_files(packet_dir, report)
    check_schema(packet_dir, report, repo_root=rr)
    check_results_csv_consistency(packet_dir, report)
    check_provenance(packet_dir, report)
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
