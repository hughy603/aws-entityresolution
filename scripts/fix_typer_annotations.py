#!/usr/bin/env python3
"""
Fix Typer annotations in CLI files to use Optional instead of Union[Type, None].

This script updates type annotations in CLI files to use Optional[Type] instead of Type | None
or Union[Type, None] to ensure compatibility with Typer.
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Set, Tuple

# Directories to search for CLI files
CLI_DIRS = [
    "src/aws_entity_resolution/cli.py",
    "src/aws_entity_resolution/extractor/cli.py",
    "src/aws_entity_resolution/loader/cli.py",
    "src/aws_entity_resolution/processor/cli.py",
]

# Regex patterns for finding type annotations
UNION_PATTERN = r"(\w+(?:\[.+?\])?)\s*\|\s*None"
TYPING_UNION_PATTERN = r"Union\[([^,]+),\s*None\]"
COMPLEX_UNION_PATTERN = r"(\w+(?:\[.+?\])?)\s*\|\s*(\w+(?:\[.+?\])?)"


def find_cli_files() -> List[Path]:
    """Find all CLI files in the project."""
    files = []
    for cli_path in CLI_DIRS:
        path = Path(cli_path)
        if path.exists():
            files.append(path)
    return files


def fix_annotations_in_file(file_path: Path) -> Tuple[int, Set[str]]:
    """Fix type annotations in a file.

    Args:
        file_path: Path to the file to fix.

    Returns:
        Tuple of (number of fixes, set of fixed types)
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find all instances of Type | None
    union_matches = re.findall(UNION_PATTERN, content)

    # Find all instances of Union[Type, None]
    typing_union_matches = re.findall(TYPING_UNION_PATTERN, content)

    # Find all instances of complex unions (Type1 | Type2)
    complex_union_matches = []
    for match in re.findall(COMPLEX_UNION_PATTERN, content):
        if match[1] != "None" and match[0] != "None":  # Skip Optional cases
            complex_union_matches.append(match)

    # Combine all types that need to be fixed
    all_types = set(union_matches + typing_union_matches)
    complex_types = set(f"{m[0]}|{m[1]}" for m in complex_union_matches)

    # Replace Type | None with Optional[Type]
    modified_content = re.sub(UNION_PATTERN, r"Optional[\1]", content)

    # Replace Union[Type, None] with Optional[Type]
    modified_content = re.sub(TYPING_UNION_PATTERN, r"Optional[\1]", modified_content)

    # Replace Type1 | Type2 with Union[Type1, Type2]
    modified_content = re.sub(
        COMPLEX_UNION_PATTERN,
        lambda m: m.group(0) if "None" in m.group(0) else f"Union[{m.group(1)}, {m.group(2)}]",
        modified_content
    )

    # Check if we need to add Optional import
    imports_to_add = []
    if all_types and "Optional" not in content:
        imports_to_add.append("Optional")

    # Check if we need to add Union import
    if complex_types and "Union" not in content:
        imports_to_add.append("Union")

    # Add imports if needed
    if imports_to_add:
        # Add Optional/Union to existing typing import
        if "from typing import " in modified_content:
            for import_name in imports_to_add:
                if f", {import_name}" not in modified_content and f"import {import_name}" not in modified_content:
                    modified_content = re.sub(
                        r"from typing import ([^;\n]+)",
                        r"from typing import \1, " + import_name,
                        modified_content
                    )
        else:
            # Add new import at the top after other imports
            import_pos = 0
            for match in re.finditer(r"^import .+$|^from .+ import .+$", modified_content, re.MULTILINE):
                import_pos = max(import_pos, match.end())

            if import_pos > 0:
                modified_content = (
                    modified_content[:import_pos] +
                    f"\nfrom typing import {', '.join(imports_to_add)}" +
                    modified_content[import_pos:]
                )
            else:
                modified_content = f"from typing import {', '.join(imports_to_add)}\n" + modified_content

    # Write changes back to file if any were made
    if content != modified_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(modified_content)
        return len(all_types) + len(complex_types), all_types.union(complex_types)

    return 0, set()


def main():
    """Run the script."""
    print("Checking CLI files for type annotation issues...")
    cli_files = find_cli_files()

    if not cli_files:
        print("No CLI files found.")
        return

    print(f"Found {len(cli_files)} CLI files.")
    total_fixes = 0
    fixed_files = 0

    for file_path in cli_files:
        fixes, types = fix_annotations_in_file(file_path)
        if fixes > 0:
            total_fixes += fixes
            fixed_files += 1
            print(f"Fixed {fixes} type annotations in {file_path}")

    if total_fixes > 0:
        print(f"Fixed {total_fixes} type annotations in {fixed_files} files.")
    else:
        print("No type annotation issues found.")


if __name__ == "__main__":
    main()
