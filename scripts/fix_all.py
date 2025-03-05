#!/usr/bin/env python3
"""Run all fix scripts to resolve common issues before committing.

This script orchestrates running all the fix scripts in the correct order to
prepare your code for committing. It's designed to fix most non-critical issues
automatically so they don't slow down your development process.
"""

import os
import subprocess
import time
from pathlib import Path


def run_command(cmd, description=None):
    """Run a command and print its output."""
    if description:
        print(f"\n{'=' * 5} {description} {'=' * 5}")

    print(f"Running: {cmd}")
    start_time = time.time()

    result = subprocess.run(cmd, shell=True, check=False, capture_output=True, text=True)

    duration = time.time() - start_time
    print(f"Command completed in {duration:.2f} seconds with status: {result.returncode}")

    if result.stdout:
        print("\nOutput:")
        print(result.stdout)

    if result.returncode != 0 and result.stderr:
        print("\nErrors:")
        print(result.stderr)

    return result


def run_fix_scripts():
    """Run all fix scripts in the correct order."""
    scripts_dir = Path(__file__).parent

    # First fix mypy issues (like duplicate modules)
    run_command(
        f"python {scripts_dir}/fix_mypy_issues.py",
        "Fixing mypy issues"
    )

    # Then fix Ruff linting issues
    run_command(
        f"python {scripts_dir}/fix_ruff.py",
        "Fixing Ruff linting issues"
    )


def run_ruff_optimized():
    """Run Ruff with optimized settings for quick fixes."""
    run_command(
        "ruff check --fix --unsafe-fixes --extend-select=E,F,B,I,W,C90 .",
        "Running essential Ruff linting"
    )


def run_essential_checks():
    """Run just the essential pre-commit hooks."""
    run_command(
        "pre-commit run trailing-whitespace --all-files && "
        "pre-commit run end-of-file-fixer --all-files && "
        "pre-commit run check-yaml --all-files && "
        "pre-commit run check-added-large-files --all-files && "
        "pre-commit run check-json --all-files && "
        "pre-commit run check-merge-conflict --all-files && "
        "pre-commit run debug-statements --all-files",
        "Running essential pre-commit hooks"
    )


def main():
    """Run all fix scripts and essential checks."""
    print("\n🔧 Starting automatic code fixes 🔧\n")

    # Set working directory to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Run the fix scripts
    run_fix_scripts()

    # Run optimized ruff
    run_ruff_optimized()

    # Run essential pre-commit hooks
    run_essential_checks()

    print("\n✅ All fixes completed. Most non-critical issues should be resolved.")
    print("💡 To run full pre-commit checks (slower): pre-commit run --all-files")
    print("💡 To run only on changed files: pre-commit run")


if __name__ == "__main__":
    main()
