#!/usr/bin/env python
"""Fix all type annotations to be compatible with Python 3.9 and Typer."""

import os
import re
from pathlib import Path
from typing import List, Set, Tuple


def find_python_files(directory: str = "src") -> List[Path]:
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


def fix_file(file_path: Path) -> Tuple[int, Set[str]]:
    """Fix type annotations in a single file.

    Args:
        file_path: Path to the file to fix.

    Returns:
        A tuple of (number of replacements, set of types that were fixed).
    """
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    original_content = content
    fixed_types = set()

    # Replace str | None with Optional[str]
    pattern1 = r"(\w+(?:\[.+?\])?)\s*\|\s*None"
    matches1 = re.findall(pattern1, content)
    fixed_types.update(matches1)
    content = re.sub(pattern1, r"Optional[\1]", content)

    # Replace Union[Type, None] with Optional[Type]
    pattern2 = r"Union\[([^,]+),\s*None\]"
    matches2 = re.findall(pattern2, content)
    fixed_types.update(matches2)
    content = re.sub(pattern2, r"Optional[\1]", content)

    # Replace other union types with Union[X, Y]
    pattern3 = r"(\w+(?:\[.+?\])?)\s*\|\s*(\w+(?:\[.+?\])?)"
    matches3 = re.findall(pattern3, content)
    for match in matches3:
        if match[1] != "None" and match[0] != "None":  # Skip Optional cases
            fixed_types.add(f"{match[0]}|{match[1]}")
    content = re.sub(pattern3, lambda m: m.group(0) if "None" in m.group(0) else f"Union[{m.group(1)}, {m.group(2)}]", content)

    # Ensure Optional and Union are imported from typing
    imports_to_add = []
    if "Optional" in content and "Optional" not in imports_to_add and "from typing import Optional" not in content and "from typing import" not in content:
        imports_to_add.append("Optional")
    if "Union" in content and "Union" not in imports_to_add and "from typing import Union" not in content and "from typing import" not in content:
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
            # Find the right place to insert the import
            if "import " in content:
                # Find the last import statement
                last_import = 0
                for match in re.finditer(r"^(?:import|from)\s+.+$", content, re.MULTILINE):
                    last_import = max(last_import, match.end())
                if last_import > 0:
                    content = content[:last_import] + "\n" + import_line + content[last_import:]
                else:
                    content = import_line + content
            else:
                content = import_line + content

    # Write changes back to file if any were made
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return len(fixed_types), fixed_types

    return 0, set()


def main():
    """Run the script."""
    python_files = find_python_files()
    total_fixes = 0

    for file_path in python_files:
        fixes, types = fix_file(file_path)
        if fixes > 0:
            total_fixes += fixes
            print(f"Fixed {file_path}")

    # Also check test files
    test_files = find_python_files("tests")
    for file_path in test_files:
        fixes, types = fix_file(file_path)
        if fixes > 0:
            total_fixes += fixes
            print(f"Fixed {file_path}")

    print(f"Total fixes: {total_fixes}")


if __name__ == "__main__":
    main()
