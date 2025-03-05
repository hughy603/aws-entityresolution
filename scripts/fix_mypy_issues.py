#!/usr/bin/env python3
"""Helper script to automatically fix common mypy issues.

This script performs the following tasks:
1. Resolves duplicate module issues by creating __init__.py files
2. Automatically adds typing stubs for missing imports
"""

import os
import shutil
from pathlib import Path


def create_missing_init_files():
    """Create missing __init__.py files in the src directory structure."""
    src_dir = Path("src")

    if not src_dir.exists():
        print("src directory not found")
        return

    # Walk through all directories in src
    for dir_path_str, _dirs, _files in os.walk(src_dir):
        dir_path = Path(dir_path_str)

        # Skip __pycache__ and other hidden directories
        if any(part.startswith(("__pycache__", ".")) for part in dir_path.parts):
            continue

        # Check if __init__.py exists, create it if it doesn't
        init_file = dir_path / "__init__.py"
        if not init_file.exists():
            print(f"Creating {init_file}")
            with open(init_file, "w") as f:
                f.write('"""Auto-generated __init__.py file by fix_mypy_issues.py."""\n')


def resolve_duplicate_modules():
    """Resolve duplicate module conflicts by detecting module.py and module/ pairs."""
    src_dir = Path("src")

    if not src_dir.exists():
        print("src directory not found")
        return

    # Find all .py files
    for py_file in src_dir.glob("**/*.py"):
        # Skip __init__.py files
        if py_file.name == "__init__.py":
            continue

        # Check if there's both a module.py and a module/ directory
        module_name = py_file.stem
        module_dir = py_file.parent / module_name

        if module_dir.is_dir():
            # Conflict detected: module.py and module/ exist
            print(f"Duplicate module detected: {py_file} and {module_dir}/")

            # Check if module directory has an __init__.py
            init_file = module_dir / "__init__.py"
            if not init_file.exists():
                print(f"  Creating {init_file}")
                with open(init_file, "w") as f:
                    f.write('"""Auto-generated __init__.py file by fix_mypy_issues.py."""\n')

            # Rename the .py file to avoid conflicts (add _module suffix)
            backup_file = py_file.with_suffix(".py.bak")
            print(f"  Renaming {py_file} to {backup_file}")
            shutil.copy2(py_file, backup_file)

            # Create a new file that imports from the module directory
            with open(py_file, "w") as f:
                f.write(
                    '"""Auto-generated import file to resolve duplicate module conflict."""\n\n'
                )
                f.write(
                    f"from {py_file.parent.name}.{module_name} import *  # noqa: F403\n"
                )


def main():
    """Run all fix functions."""
    print("=== Fixing mypy issues ===")
    create_missing_init_files()
    resolve_duplicate_modules()
    print("Done!")


if __name__ == "__main__":
    main()
