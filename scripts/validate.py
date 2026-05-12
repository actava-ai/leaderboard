#!/usr/bin/env python3
"""Local-runnable shim for the CI validator. Same code path as GitHub Actions.

Usage: python scripts/validate.py <path-to-submission-directory>
"""

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    validator = here.parent / ".github" / "scripts" / "validate_submission.py"
    sys.argv[0] = str(validator)
    runpy.run_path(str(validator), run_name="__main__")
