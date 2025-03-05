#!/usr/bin/env python
"""Fix all type annotations to be compatible with Python 3.9 and Typer."""

import re
from pathlib import Path


def fix_file(file_path):
    """Fix type annotations in a single file."""
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Replace str | None with Optional[str]
    content = re.sub(
        r"(\w+)\s*\|\s*None",
        r"Optional[\1]",
        content,
    )

    # Replace other union types with Union[X, Y]
    content = re.sub(
        r"(\w+)\s*\|\s*(\w+)",
        r"Union[\1, \2]",
        content,
    )

    # Ensure Optional and Union are imported from typing
    imports_to_add = []
    if "Optional" in content and "from typing import Optional" not in content and "Optional" not in imports_to_add:
        imports_to_add.append("Optional")
    if "Union" in content and "from typing import Union" not in content and "Union" not in imports_to_add:
        imports_to_add.append("Union")

    if imports_to_add:
        if "from typing import " in content:
            # Add to existing import
            for import_name in imports_to_add:
                if f", {import_name}" not in content and f"import {import_name}" not in content:
                    content = re.sub(
                        r"from typing import ([^;\n]+)",
                        r"from typing import \1, " + import_name,
                        content,
                    )
        else:
            # Add new import statement
            import_line = f"from typing import {', '.join(imports_to_add)}\n"
            content = import_line + content

    # Write changes back to file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Fixed {file_path}")


def main():
    """Find and fix all files with type annotations."""
    # Get the project root directory
    root_dir = Path(__file__).parent.parent
    src_dir = root_dir / "src" / "aws_entity_resolution"

    # Find all Python files in the src directory recursively
    python_files = list(src_dir.glob("**/*.py"))

    # Fix each file
    for file_path in python_files:
        fix_file(file_path)


if __name__ == "__main__":
    main()
