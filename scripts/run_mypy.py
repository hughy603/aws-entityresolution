#!/usr/bin/env python
"""
Helper script to run mypy with optimal settings for aws-entity-resolution.
"""

import os
import sys
import subprocess
from pathlib import Path


def run_mypy():
    """Run mypy type checking with optimal settings."""
    # Get project root directory
    project_root = Path(__file__).parent.parent.absolute()

    # Change to project root
    os.chdir(project_root)

    # Base command with essential flags
    cmd = [
        "mypy",
        "--config-file", "pyproject.toml",  # Use pyproject.toml for config
        "--namespace-packages",             # Handle namespace packages
        "--explicit-package-bases",         # Be explicit about package bases
        "--ignore-missing-imports",         # Ignore missing imports
        "--no-warn-return-any",             # Don't warn about returning Any
        "src",                              # Check only the src directory
    ]

    # Run mypy
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)

    return result.returncode


if __name__ == "__main__":
    sys.exit(run_mypy())
