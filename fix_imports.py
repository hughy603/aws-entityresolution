#!/usr/bin/env python3
"""Script to fix imports using Ruff.
This script will run Ruff on all Python files in the project to fix import sorting.
"""

import subprocess
import sys
from pathlib import Path


def main() -> int | None:
    """Run Ruff to fix imports in all Python files."""
    # Get the project root directory
    project_root = Path(__file__).parent.absolute()

    print(f"Running Ruff to fix imports in {project_root}")

    # Run Ruff with the --fix option to automatically fix imports
    try:
        result = subprocess.run(
            ["ruff", "check", "--select=I", "--fix", "src", "tests"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print("Ruff encountered issues:")
            print(result.stderr)
            print(result.stdout)
            return 1

        print("Import sorting completed successfully!")
        if result.stdout:
            print(result.stdout)

        return 0

    except Exception as e:
        print(f"Error running Ruff: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
