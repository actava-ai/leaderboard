#!/usr/bin/env python3
"""Local-runnable shim for the CI validator. Same code path as GitHub Actions.

Usage: python scripts/validate.py <path-to-submission-directory>

Defaults --repo-root to this leaderboard repo so the validator can resolve
benchmark schemas even when the packet lives outside the repo (e.g. a freshly
prepared /tmp/.../packet/ directory).
"""

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    leaderboard_root = here.parent
    validator = leaderboard_root / ".github" / "scripts" / "validate_submission.py"
    # Inject --repo-root if the user didn't specify it explicitly.
    if "--repo-root" not in sys.argv:
        sys.argv.extend(["--repo-root", str(leaderboard_root)])
    sys.argv[0] = str(validator)
    runpy.run_path(str(validator), run_name="__main__")
