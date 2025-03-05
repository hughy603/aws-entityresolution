#!/usr/bin/env python
"""Run pre-commit checks on staged files."""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command, capture=True):
    """Run a shell command and return the result."""
    print(f"Running: {' '.join(command)}")
    if capture:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result
    return subprocess.run(command, check=False)


def main():
    """Run pre-commit checks on staged files."""
    # Ensure we're in the project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    print("🔍 Running pre-commit checks on staged files...")
    result = run_command(["pre-commit", "run"])

    if result.returncode != 0:
        print("❌ Pre-commit checks failed:")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        print("\n💡 Tips for fixing common pre-commit issues:")
        print("  - Run 'scripts/lint.py' to auto-fix Ruff linting issues")
        print("  - For mypy errors, add appropriate type annotations")
        print("  - For terraform errors, run 'terraform fmt'")
        print("  - For failing tests, check 'pytest' output")
        return 1
    print("✅ All pre-commit checks passed!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
