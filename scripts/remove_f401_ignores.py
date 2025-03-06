#!/usr/bin/env python3
"""Remove F401 (unused import) ignores from Ruff configuration.

This script modifies the .ruff.toml file to remove F401 ignores from files
where we want to enforce unused import removal.
"""

import re
import sys
from pathlib import Path


def remove_f401_ignores():
    """Remove F401 ignores from the Ruff configuration."""
    ruff_config_path = Path(".ruff.toml")

    if not ruff_config_path.exists():
        print("Error: .ruff.toml file not found")
        sys.exit(1)

    # Read the current configuration
    with open(ruff_config_path, "r") as f:
        content = f.read()

    # Files to keep F401 ignores for (typically __init__.py files)
    keep_f401_for = [
        r'"[*][*]/__init__\.py"',
        r'"src/aws_entity_resolution/config/__init__\.py"',
        r'"src/\*/\*/__init__\.py"',
        r'"tests/__init__\.py"',
    ]

    # Create a regex pattern to match these files
    keep_pattern = "|".join(keep_f401_for)

    # Find all per-file ignore sections
    per_file_sections = re.findall(r'("[^"]+"\s*=\s*\[\s*(?:[^\]]+)\])', content)

    # Process each section
    for section in per_file_sections:
        # Skip sections for files where we want to keep F401 ignores
        if re.search(keep_pattern, section):
            continue

        # Remove F401 from the ignore list
        modified_section = re.sub(r'"F401",?\s*#\s*Allow unused imports', "", section)

        # Replace the section in the content
        content = content.replace(section, modified_section)

    # Write the modified configuration back
    with open(ruff_config_path, "w") as f:
        f.write(content)

    print("Successfully removed F401 ignores from Ruff configuration")


if __name__ == "__main__":
    remove_f401_ignores()
