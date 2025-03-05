#!/usr/bin/env python3
"""Fix style issues in the codebase."""

import subprocess
import sys
from pathlib import Path
import os


def run_command(command):
    """Run a command and return True if it succeeds."""
    try:
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    """Fix style issues in the codebase."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent.absolute()

    # Change to the project root directory
    os.chdir(project_root)

    # First run black to format code
    success = run_command(["poetry", "run", "black", "."])

    # Then run ruff to fix imports and other issues
    success = run_command(["poetry", "run", "ruff", "check", "--select=I", "--fix", "."]) and success

    # Return 0 if all commands succeeded, 1 otherwise
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
