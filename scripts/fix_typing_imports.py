#!/usr/bin/env python
"""Fix typing imports across the codebase to comply with Python 3.12 standards."""

import re
from pathlib import Path


def fix_file(file_path):
    """Fix typing imports in a single file."""
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Replace direct shadowing imports with standard typing imports
    content = re.sub(
        r"from typing import (.*?)(dict|list)(.*)",
        lambda m: f"from typing import {m.group(1)}{m.group(3)}",
        content,
        flags=re.MULTILINE,
    )

    # Fix import statement where 'dict' or 'list' appears at the end
    content = re.sub(
        r"from typing import (.*?), (dict|list)$",
        r"from typing import \1",
        content,
        flags=re.MULTILINE,
    )

    # Fix import statement where 'dict' or 'list' is the only import
    content = re.sub(
        r"from typing import (dict|list)$",
        "",
        content,
        flags=re.MULTILINE,
    )

    # Fix any trailing commas in import statements
    content = re.sub(
        r"from typing import (.+),\s*$",
        r"from typing import \1",
        content,
        flags=re.MULTILINE,
    )

    # Replace Dict[...] with dict[...] and List[...] with list[...]
    content = re.sub(r"Dict\[", "dict[", content)
    content = re.sub(r"List\[", "list[", content)

    # Remove empty imports
    content = re.sub(r"from typing import\s*\n", "", content)

    # Remove trailing commas in imports
    content = re.sub(r"from typing import (.*),(\s*\n)", r"from typing import \1\2", content)

    # Write changes back to file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Fixed {file_path}")


def main():
    """Find and fix typing imports in Python files."""
    project_root = Path(__file__).parent.parent
    python_files = list(project_root.glob("src/**/*.py")) + list(project_root.glob("tests/**/*.py"))

    for file_path in python_files:
        fix_file(file_path)

    print(f"Processed {len(python_files)} files")


if __name__ == "__main__":
    main()
