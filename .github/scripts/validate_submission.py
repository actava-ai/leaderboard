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


# Spec §2.4 size budget
SOFT_LIMITS = {
    "small_json": 100 * 1024,  # submission.json, results.csv, sub.yaml, provenance.json
    "trial_json": 200 * 1024,  # scorecard, reward, result
    "trajectory_zst": 10 * 1024 * 1024,
    "total": 100 * 1024 * 1024,
}
HARD_LIMITS = {
    "small_json": 1 * 1024 * 1024,
    "trial_json": 2 * 1024 * 1024,
    "trajectory_zst": 50 * 1024 * 1024,
    "total": 500 * 1024 * 1024,
}

_TOP_LEVEL_SMALL = ("submission.json", "results.csv", "sub.yaml", "provenance.json")
_TRIAL_FILES_REQUIRED = (
    "result.json",
    "verifier/scorecard.json",
    "verifier/reward.json",
    "agent/trajectory.jsonl.zst",
)


def check_per_trial_integrity(packet_dir: Path, report: ValidationReport) -> None:
    """Rules 8–10: each trial dir has the expected files; trajectory decodes; counts match."""
    import zstandard as zstd

    manifest = _read_manifest(packet_dir)
    per_domain_expected: dict[str, int] = {}
    if manifest is not None:
        per_dom = (manifest.get("results") or {}).get("per_domain") or {}
        for dom, score in per_dom.items():
            n = score.get("n_trials")
            if isinstance(n, int):
                per_domain_expected[dom] = n

    trials_dir = packet_dir / "trials"
    if not trials_dir.is_dir():
        return

    per_domain_actual: dict[str, int] = {}
    for domain_dir in sorted(trials_dir.iterdir()):
        if not domain_dir.is_dir():
            report.err(f"Unexpected non-directory under trials/: {domain_dir.name}")
            continue
        trial_dirs = [p for p in domain_dir.iterdir() if p.is_dir()]
        per_domain_actual[domain_dir.name] = len(trial_dirs)
        for trial_dir in trial_dirs:
            for rel in _TRIAL_FILES_REQUIRED:
                tp = trial_dir / rel
                if not tp.is_file():
                    report.err(f"trial {domain_dir.name}/{trial_dir.name}: missing {rel}")
            actual = {
                str(p.relative_to(trial_dir)) for p in trial_dir.rglob("*") if p.is_file()
            }
            expected = set(_TRIAL_FILES_REQUIRED)
            extras = actual - expected
            for x in sorted(extras):
                report.err(
                    f"trial {domain_dir.name}/{trial_dir.name}: unexpected file {x}"
                )
            traj = trial_dir / "agent" / "trajectory.jsonl.zst"
            if traj.is_file():
                try:
                    decompressor = zstd.ZstdDecompressor()
                    with traj.open("rb") as fh, decompressor.stream_reader(fh) as reader:
                        buf = b""
                        line_count = 0
                        while True:
                            chunk = reader.read(65536)
                            if not chunk:
                                if buf.strip():
                                    json.loads(buf)
                                    line_count += 1
                                break
                            buf += chunk
                            while b"\n" in buf:
                                line, buf = buf.split(b"\n", 1)
                                if line.strip():
                                    json.loads(line)
                                    line_count += 1
                        if line_count < 1:
                            report.err(
                                f"trial {domain_dir.name}/{trial_dir.name}: trajectory is empty"
                            )
                except zstd.ZstdError as e:
                    report.err(
                        f"trial {domain_dir.name}/{trial_dir.name}: "
                        f"trajectory is not valid zstd: {e}"
                    )
                except json.JSONDecodeError as e:
                    report.err(
                        f"trial {domain_dir.name}/{trial_dir.name}: "
                        f"trajectory has malformed JSON line: {e}"
                    )

    for dom, expected_n in per_domain_expected.items():
        actual_n = per_domain_actual.get(dom, 0)
        if actual_n != expected_n:
            report.err(
                f"Trial count mismatch for domain '{dom}': "
                f"found {actual_n}, manifest says n_trials={expected_n}"
            )
    for dom in per_domain_actual:
        if dom not in per_domain_expected:
            report.warn(
                f"Domain '{dom}' has trials on disk but no per_domain entry in manifest"
            )


def check_size_limits(packet_dir: Path, report: ValidationReport) -> None:
    """Rule 11: per-file and total size budget."""
    total = 0
    for path in packet_dir.rglob("*"):
        if not path.is_file():
            continue
        size = path.stat().st_size
        total += size
        rel = str(path.relative_to(packet_dir))

        if path.name in _TOP_LEVEL_SMALL and path.parent == packet_dir:
            soft, hard, label = (
                SOFT_LIMITS["small_json"],
                HARD_LIMITS["small_json"],
                "small_json",
            )
        elif rel.startswith("trials/") and path.name in (
            "result.json",
            "scorecard.json",
            "reward.json",
        ):
            soft, hard, label = (
                SOFT_LIMITS["trial_json"],
                HARD_LIMITS["trial_json"],
                "trial_json",
            )
        elif path.name == "trajectory.jsonl.zst":
            soft, hard, label = (
                SOFT_LIMITS["trajectory_zst"],
                HARD_LIMITS["trajectory_zst"],
                "trajectory_zst",
            )
        else:
            continue

        if size > hard:
            report.err(f"{rel} ({size} bytes) exceeds hard limit for {label} ({hard} bytes)")
        elif size > soft:
            report.warn(f"{rel} ({size} bytes) over soft limit for {label} ({soft} bytes)")

    if total > HARD_LIMITS["total"]:
        report.err(
            f"Total packet size {total} bytes exceeds hard limit ({HARD_LIMITS['total']})"
        )
    elif total > SOFT_LIMITS["total"]:
        report.warn(f"Total packet size {total} bytes over soft limit ({SOFT_LIMITS['total']})")


def check_known_dataset_version(
    packet_dir: Path, report: ValidationReport, repo_root: Path
) -> None:
    """Rule 12 (soft): dataset.version is listed in benchmarks/<bench>/schema/known-versions.txt."""
    manifest = _read_manifest(packet_dir)
    if manifest is None:
        return
    ds = manifest.get("dataset") or {}
    bench = ds.get("name")
    version = ds.get("version")
    if not isinstance(bench, str) or not isinstance(version, str):
        return
    kv = repo_root / "benchmarks" / bench / "schema" / "known-versions.txt"
    if not kv.is_file():
        report.warn(
            f"No known-versions.txt for benchmark '{bench}'; cannot verify dataset version"
        )
        return
    known = {line.strip() for line in kv.read_text(encoding="utf-8").splitlines() if line.strip()}
    if version not in known:
        report.warn(
            f"Dataset version '{version}' not listed in {kv.relative_to(repo_root)} "
            f"(known: {sorted(known)}). Reviewer please confirm; the version list "
            f"can be updated in a follow-up PR."
        )


def check_duplicate_submission_id(packet_dir: Path, report: ValidationReport) -> None:
    """Rule 13 (soft): another submission directory has the same submission.id."""
    manifest = _read_manifest(packet_dir)
    if manifest is None:
        return
    sid = (manifest.get("submission") or {}).get("id")
    if not isinstance(sid, str):
        return
    submissions_root = packet_dir.parent
    if not submissions_root.is_dir():
        return
    matches: list[str] = []
    for sibling in submissions_root.iterdir():
        if not sibling.is_dir() or sibling == packet_dir:
            continue
        sibling_mf = _read_manifest(sibling)
        if sibling_mf is None:
            continue
        sibling_id = (sibling_mf.get("submission") or {}).get("id")
        if sibling_id == sid:
            matches.append(sibling.name)
    if matches:
        report.warn(
            f"Possible resubmission of '{sid}' — same submission.id present in: "
            f"{', '.join(matches)}. Reviewer please confirm intent."
        )


def write_markdown_report(report: ValidationReport, packet_dir: Path, out: Path) -> None:
    """Write a sticky-PR-comment-friendly Markdown summary."""
    # In CI mode, packet_dir is the repo root (no useful name); fall back to a label.
    title_suffix = packet_dir.name if packet_dir.name and packet_dir.name != "." else "PR diff"
    lines = [f"## Submission validation — `{title_suffix}`", ""]
    if report.has_errors():
        lines.append(f"❌ **{len(report.errors)} error(s)** — PR cannot merge as-is.\n")
        for e in report.errors:
            lines.append(f"- ❌ {e}")
        lines.append("")
    else:
        lines.append("✅ **All checks passed.**\n")
    if report.warnings:
        lines.append(f"⚠️ **{len(report.warnings)} warning(s)** — reviewer judgment call:\n")
        for w in report.warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json_report(report: ValidationReport, packet_dir: Path, out: Path) -> None:
    """Write a machine-readable JSON report (consumed by the PR-labeller action)."""
    data = {
        "packet": packet_dir.name,
        "status": "invalid"
        if report.has_errors()
        else ("needs-review" if report.warnings else "valid"),
        "errors": report.errors,
        "warnings": report.warnings,
    }
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _git_diff_paths(repo_root: Path, base_ref: str, head_ref: str) -> list[Path]:
    """Return the list of paths added/modified by commits unique to head.

    Uses three-dot syntax (base...head = merge-base..head) so a stale base SHA
    captured at PR-open time doesn't bleed in commits that have since landed on
    the base branch. This matches GitHub's own "Files changed" diff.
    """
    import subprocess

    out = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--name-only", f"{base_ref}...{head_ref}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [Path(line) for line in out.splitlines() if line.strip()]


def validate_pr_diff(repo_root: Path, base_ref: str, head_ref: str) -> ValidationReport:
    """CI entry point: enforce diff scope (rule 1) and validate any touched packets."""
    report = ValidationReport()
    paths = _git_diff_paths(repo_root, base_ref, head_ref)
    if not paths:
        report.warn("PR has no file changes")
        return report

    submission_dirs: set[Path] = set()
    non_submission_paths: list[Path] = []
    for p in paths:
        parts = p.parts
        if len(parts) >= 4 and parts[0] == "benchmarks" and parts[2] == "submissions":
            submission_dirs.add(repo_root / parts[0] / parts[1] / parts[2] / parts[3])
        else:
            non_submission_paths.append(p)

    if non_submission_paths:
        listed = "\n".join(f"  - {p}" for p in non_submission_paths[:20])
        report.err(
            "PR touches files outside benchmarks/*/submissions/*/ — submissions and "
            "meta-changes must land in separate PRs (or a maintainer applies the 'meta:' "
            "label to bypass this check):\n" + listed
        )

    if len(submission_dirs) > 1:
        listed = ", ".join(sorted(d.name for d in submission_dirs))
        report.err(
            f"PR touches multiple submission directories ({listed}); expected exactly one"
        )

    for d in sorted(submission_dirs):
        if not d.is_dir():
            report.err(f"Submission directory missing on head ref: {d.name}")
            continue
        sub_report = validate_packet(d, repo_root=repo_root)
        for e in sub_report.errors:
            report.err(f"[{d.name}] {e}")
        for w in sub_report.warnings:
            report.warn(f"[{d.name}] {w}")
    return report


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
    check_per_trial_integrity(packet_dir, report)
    check_size_limits(packet_dir, report)
    check_known_dataset_version(packet_dir, report, repo_root=rr)
    check_duplicate_submission_id(packet_dir, report)
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
    parser.add_argument("--base-ref", help="(CI) PR base SHA — required with --head-ref.")
    parser.add_argument("--head-ref", help="(CI) PR head SHA — required with --base-ref.")
    parser.add_argument(
        "--repo-root", type=Path, default=Path("."), help="(CI) repo root; default cwd."
    )
    parser.add_argument("--report-md", type=Path, help="Write Markdown report to this path.")
    parser.add_argument(
        "--report-json", type=Path, help="Write structured JSON report to this path."
    )
    args = parser.parse_args(argv)

    if args.base_ref and args.head_ref:
        report = validate_pr_diff(args.repo_root, args.base_ref, args.head_ref)
        label = "PR diff"
        report_dir = args.repo_root
    elif args.path:
        # Pass repo_root only if explicitly set (not the cwd default), so
        # _resolve_repo_root can still walk up for in-repo packets.
        repo_root_arg = args.repo_root if args.repo_root != Path(".") else None
        report = validate_packet(args.path, repo_root=repo_root_arg)
        label = args.path.name
        report_dir = args.path
    else:
        parser.error("provide either a path or --base-ref/--head-ref")
        return 2

    if args.report_md:
        write_markdown_report(report, report_dir, args.report_md)
    if args.report_json:
        write_json_report(report, report_dir, args.report_json)

    print(
        f"{'❌' if report.has_errors() else '✅'} {label}: "
        f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)",
        file=sys.stderr,
    )
    for e in report.errors:
        print(f"  ❌ {e}", file=sys.stderr)
    for w in report.warnings:
        print(f"  ⚠️ {w}", file=sys.stderr)
    return 1 if report.has_errors() else 0


if __name__ == "__main__":
    sys.exit(main())
