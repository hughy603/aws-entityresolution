#!/usr/bin/env python3
"""Script to fix type annotations in the codebase.

This script converts Python 3.10+ union type annotations (T | None) to the
older Optional[T] syntax for compatibility with libraries like Typer that
don't yet support the newer syntax.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple


def find_python_files(directory: str) -> List[Path]:
    """Find all Python files in the given directory and its subdirectories.

    Args:
        directory: The directory to search in.

    Returns:
        A list of paths to Python files.
    """
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(os.path.join(root, file)))
    return python_files


def fix_union_types(file_path: Path) -> Tuple[int, List[str]]:
    """Fix union type annotations in a file.

    Args:
        file_path: Path to the file to fix.

    Returns:
        A tuple of (number of replacements, list of fixed lines).
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern to match type annotations like "str | None" or "int | None"
    # This regex looks for type annotations followed by | None
    pattern = r"(\w+(?:\[.+?\])?)\s*\|\s*None"

    # Replace with Optional[type]
    fixed_content = re.sub(pattern, r"Optional[\1]", content)

    # Count replacements
    replacements = len(re.findall(pattern, content))

    # Find the lines that were changed
    if replacements > 0:
        original_lines = content.splitlines()
        fixed_lines = fixed_content.splitlines()
        changed_lines = []

        for i, (orig, fixed) in enumerate(zip(original_lines, fixed_lines)):
            if orig != fixed:
                changed_lines.append(f"Line {i+1}: {orig} -> {fixed}")
    else:
        changed_lines = []

    # Write the fixed content back to the file
    if replacements > 0:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(fixed_content)

    return replacements, changed_lines


def ensure_optional_import(file_path: Path) -> bool:
    """Ensure that Optional is imported from typing.

    Args:
        file_path: Path to the file to check.

    Returns:
        True if the import was added, False otherwise.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if Optional is already imported
    if "Optional" in content and "from typing import" in content:
        # Check if Optional is already in the import statement
        import_match = re.search(r"from\s+typing\s+import\s+([^;\n]+)", content)
        if import_match:
            imports = import_match.group(1)
            if "Optional" in imports:
                return False

            # Add Optional to the existing import
            new_imports = imports.strip()
            if new_imports.endswith(","):
                new_imports += " Optional"
            else:
                new_imports += ", Optional"

            new_content = content.replace(imports, new_imports)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True

    # If we get here, we need to add a new import statement
    if "from typing import" in content:
        # Add Optional to an existing typing import
        new_content = re.sub(
            r"from\s+typing\s+import\s+([^;\n]+)",
            r"from typing import \1, Optional",
            content
        )
    else:
        # Add a new typing import at the top of the file
        new_content = "from typing import Optional\n\n" + content

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


def main() -> int:
    """Run the script to fix type annotations.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    # Get the project root directory
    project_root = Path(__file__).parent.parent.absolute()

    # Directories to search
    directories = [
        project_root / "src",
        project_root / "tests",
    ]

    total_files = 0
    total_replacements = 0

    for directory in directories:
        if not directory.exists():
            print(f"Directory not found: {directory}")
            continue

        print(f"Searching for Python files in {directory}...")
        python_files = find_python_files(str(directory))

        for file_path in python_files:
            replacements, changed_lines = fix_union_types(file_path)

            if replacements > 0:
                # Ensure Optional is imported
                added_import = ensure_optional_import(file_path)

                print(f"Fixed {replacements} union type annotations in {file_path}")
                for line in changed_lines:
                    print(f"  {line}")

                if added_import:
                    print(f"  Added 'Optional' import to {file_path}")

                total_files += 1
                total_replacements += replacements

    print(f"\nSummary: Fixed {total_replacements} union type annotations in {total_files} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
