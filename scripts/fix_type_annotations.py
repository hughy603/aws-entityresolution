#!/usr/bin/env python3
"""
Fix type annotations in CLI files to use Optional[type] instead of type | None.

This script finds and replaces Python 3.10+ Union type syntax with the older
typing.Optional syntax that is compatible with Typer/Click.
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple, Set

# Files to process
CLI_FILES = [
    "src/aws_entity_resolution/extractor/cli.py",
    "src/aws_entity_resolution/processor/cli.py",
    "src/aws_entity_resolution/loader/cli.py",
    "src/aws_entity_resolution/cli.py",
]

# Regex pattern to find type | None annotations - handles any type, not just str
UNION_PATTERN = re.compile(r'([a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)?)\s*\|\s*None')

def ensure_optional_import(content: str) -> Tuple[str, bool]:
    """
    Ensure that Optional is imported from typing.

    Returns:
        Tuple of (modified_content, was_optional_already_imported)
    """
    # Check if Optional is already imported
    optional_imported = False

    # Check for 'from typing import Optional' or 'from typing import ..., Optional, ...'
    if re.search(r'from\s+typing\s+import\s+([^,]*,\s*)*Optional(\s*,|$)', content):
        optional_imported = True

    # Check for 'import typing' and add Optional if needed
    if not optional_imported:
        # If there's already a typing import block, add Optional to it
        typing_import_match = re.search(r'from\s+typing\s+import\s+(.*?)$', content, re.MULTILINE)
        if typing_import_match:
            imports = typing_import_match.group(1)
            if 'Optional' not in imports:
                if imports.strip().endswith(','):
                    new_imports = f"{imports} Optional,"
                else:
                    new_imports = f"{imports}, Optional"
                content = content.replace(typing_import_match.group(0), f"from typing import {new_imports}")
        else:
            # Add a new import line after other imports
            import_section_end = 0
            for match in re.finditer(r'^import\s+.*?$|^from\s+.*?\s+import\s+.*?$', content, re.MULTILINE):
                if match.end() > import_section_end:
                    import_section_end = match.end()

            if import_section_end > 0:
                content = (
                    content[:import_section_end] +
                    "\nfrom typing import Optional" +
                    content[import_section_end:]
                )
            else:
                # No imports found, add at the top after docstring
                docstring_end = content.find('"""', content.find('"""') + 3) + 3 if '"""' in content else 0
                content = (
                    content[:docstring_end] +
                    "\n\nfrom typing import Optional" +
                    content[docstring_end:]
                )

    return content, optional_imported

def fix_file(file_path: str) -> None:
    """Fix type annotations in a file."""
    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {file_path}")
        return

    print(f"Processing {file_path}...")

    # Read file content
    content = path.read_text()

    # Ensure Optional is imported
    content, was_optional_imported = ensure_optional_import(content)

    # Find and replace all instances of type | None with Optional[type]
    modified_content = UNION_PATTERN.sub(r'Optional[\1]', content)

    # If no changes were made and Optional wasn't already imported, remove the import we added
    if modified_content == content and not was_optional_imported:
        modified_content = re.sub(r'\nfrom typing import Optional\n', '\n', modified_content)

    # Write back to file if changes were made
    if modified_content != content:
        path.write_text(modified_content)
        print(f"  Fixed type annotations in {file_path}")
    else:
        print(f"  No changes needed in {file_path}")

def main() -> None:
    """Main function to process all CLI files."""
    for file_path in CLI_FILES:
        fix_file(file_path)

    print("\nDone! Type annotations have been fixed.")

if __name__ == "__main__":
    main()
