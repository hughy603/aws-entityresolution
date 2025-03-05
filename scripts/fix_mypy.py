#!/usr/bin/env python
"""Helper script to fix common MyPy issues."""

import os
import subprocess
from pathlib import Path


def run_command(command, capture=True):
    """Run a shell command."""
    print(f"Running: {command}")
    if capture:
        # nosec B602: This is a controlled script used only by developers
        result = subprocess.run(  # nosec
            command, shell=True, check=False, capture_output=True, text=True
        )
        return result
    # nosec B602: This is a controlled script used only by developers
    return subprocess.run(command, shell=True, check=False)  # nosec


def find_duplicate_modules():
    """Find duplicate module names that cause MyPy errors."""
    print("\n--- Finding duplicate module names ---")

    # Look for module names in different directories
    module_paths = {}
    project_root = Path("src")

    for path in project_root.glob("**/*.py"):
        module_name = path.name

        if module_name in module_paths:
            existing_path = module_paths[module_name]
            if path.parent != existing_path.parent:
                print(f"Duplicate module found: {module_name}")
                print(f"  - {existing_path}")
                print(f"  - {path}")

                # Analyze the content to suggest a fix
                suggest_rename(existing_path, path)
        else:
            module_paths[module_name] = path


def suggest_rename(path1, path2):
    """Suggest how to rename a module to avoid duplicates."""
    # Analyze module contents to suggest renaming strategy

    # For CLI modules, suggest changing to reflect their component
    if path1.name == "cli.py" and path2.name == "cli.py":
        comp1 = path1.parent.name

        print("\nSuggestion for duplicate CLI modules:")
        print(f"1. Rename {path1} to {comp1}_cli.py")
        print("   Update imports and entry points accordingly")
        print("2. OR Create an explicit '__init__.py' in each directory")
        print("   This makes the full module path unique:")
        print(f"   - {path1.parent.parent.name}.{path1.parent.name}.cli")
        print(f"   - {path2.parent.parent.name}.{path2.parent.name}.cli")
        print("3. OR Add MyPy configuration to exclude one of the files:")
        print("   Add to pyproject.toml:")
        print("   [[tool.mypy.overrides]]")
        print(
            f'   module = "{path2.relative_to("src").with_suffix("").as_posix().replace("/", ".")}"'
        )
        print("   ignore_errors = true")


def fix_mypy_config():
    """Update MyPy configuration to better handle common issues."""
    print("\n--- Updating MyPy configuration ---")

    # Check if we have explicit_package_bases already configured
    with open("pyproject.toml") as f:
        content = f.read()

    if "explicit_package_bases" not in content:
        print("Adding explicit_package_bases=true to MyPy config...")

        # Find the mypy section and add the config
        with open("pyproject.toml") as f:
            lines = f.readlines()

        new_lines = []
        in_mypy_section = False

        for line in lines:
            new_lines.append(line)
            if "[tool.mypy]" in line:
                in_mypy_section = True
            elif (
                in_mypy_section
                and line.strip()
                and not line.startswith("[")
                and "explicit_package_bases" not in content
            ):
                # We're in the mypy section and this is the first config line
                # Add our new config if not already present
                new_lines.insert(-1, "explicit_package_bases = true\n")
                in_mypy_section = False  # Don't add it again

        # Write the updated content
        with open("pyproject.toml", "w") as f:
            f.writelines(new_lines)

        print("Updated PyProject.toml with explicit_package_bases=true")
    else:
        print("explicit_package_bases already configured in MyPy config")


def create_module_init_files():
    """Create missing __init__.py files in the src directory structure."""
    print("\n--- Creating missing __init__.py files ---")

    # Create __init__.py files where needed
    counts = {"existing": 0, "created": 0}

    for directory in Path("src").glob("**"):
        if directory.is_dir() and not directory.name.startswith("."):
            init_file = directory / "__init__.py"
            if not init_file.exists():
                print(f"Creating {init_file}")
                init_file.touch()
                counts["created"] += 1
            else:
                counts["existing"] += 1

    print(f"Found {counts['existing']} existing __init__.py files")
    print(f"Created {counts['created']} new __init__.py files")


def main():
    """Main function."""
    # Set the project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    print("===== MyPy Issue Fixer =====")

    # Find duplicate modules
    find_duplicate_modules()

    # Update MyPy configuration
    fix_mypy_config()

    # Create missing __init__.py files
    create_module_init_files()

    print("\n===== MyPy Issue Fixer Complete =====")
    print("Run pre-commit again to check if issues have been resolved.")
    print("Remember to manually review and fix the suggested module naming conflicts!")


if __name__ == "__main__":
    main()
