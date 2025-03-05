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
UNION_PATTERN = r"(\w+)\s*\|\s*None"
TYPING_UNION_PATTERN = r"Union\[([^,]+),\s*None\]"


def find_cli_files() -> List[Path]:
    """Find all CLI files in the project."""
    files = []
    for cli_path in CLI_DIRS:
        path = Path(cli_path)
        if path.exists():
            files.append(path)
    return files


def fix_annotations_in_file(file_path: Path) -> Tuple[int, Set[str]]:
    """Fix type annotations in a file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find all instances of Type | None
    union_matches = re.findall(UNION_PATTERN, content)

    # Find all instances of Union[Type, None]
    typing_union_matches = re.findall(TYPING_UNION_PATTERN, content)

    # Combine all types that need to be fixed
    all_types = set(union_matches + typing_union_matches)

    # Replace Type | None with Optional[Type]
    modified_content = re.sub(UNION_PATTERN, r"Optional[\1]", content)

    # Replace Union[Type, None] with Optional[Type]
    modified_content = re.sub(TYPING_UNION_PATTERN, r"Optional[\1]", modified_content)

    # Check if we need to add Optional import
    if all_types and "Optional" not in content:
        # Add Optional to existing typing import
        if "from typing import " in modified_content:
            modified_content = re.sub(
                r"from typing import (.+)",
                r"from typing import \1, Optional",
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
                    "\nfrom typing import Optional" +
                    modified_content[import_pos:]
                )
            else:
                modified_content = "from typing import Optional\n" + modified_content

    # Write changes back to file if any were made
    if content != modified_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(modified_content)
        return len(all_types), all_types

    return 0, set()


def main():
    """Run the script to fix all CLI files."""
    cli_files = find_cli_files()
    total_fixes = 0
    all_fixed_types = set()

    print(f"Checking {len(cli_files)} CLI files for type annotation issues...")

    for file_path in cli_files:
        fixes, fixed_types = fix_annotations_in_file(file_path)
        if fixes > 0:
            print(f"Fixed {fixes} type annotations in {file_path}")
            all_fixed_types.update(fixed_types)
        total_fixes += fixes

    if total_fixes > 0:
        print(f"\nTotal fixes: {total_fixes}")
        print(f"Fixed types: {', '.join(sorted(all_fixed_types))}")
    else:
        print("No type annotation issues found.")


if __name__ == "__main__":
    main()
