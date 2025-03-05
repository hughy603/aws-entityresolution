#!/usr/bin/env python
"""Run Ruff linting on the codebase."""

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
    """Run Ruff linting and format the codebase."""
    # Ensure we're in the project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    print("🔍 Running Ruff checks...")
    result = run_command(["poetry", "run", "ruff", "check", "."])

    if result.returncode != 0:
        print("❌ Ruff found issues:")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        print("\n🔧 Attempting to auto-fix issues...")
        fix_result = run_command(["poetry", "run", "ruff", "check", "--fix", "."])

        if fix_result.returncode == 0:
            print("✅ Auto-fixes applied successfully!")
        else:
            print("⚠️ Some issues could not be fixed automatically.")
            print("   Review the output above and fix remaining issues manually.")
            return 1
    else:
        print("✅ Ruff checks passed!")

    print("\n🔄 Running Ruff formatter...")
    format_result = run_command(["poetry", "run", "ruff", "format", "."])

    if format_result.returncode == 0:
        print("✅ Formatting completed successfully!")
    else:
        print("❌ Formatting failed:")
        if format_result.stdout:
            print(format_result.stdout)
        if format_result.stderr:
            print(format_result.stderr, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
