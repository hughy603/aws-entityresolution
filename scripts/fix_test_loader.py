#!/usr/bin/env python
"""Fix the test_loader.py file to match the available functions in loader.py."""

import re
from pathlib import Path


def fix_test_loader():
    """Fix the test_loader.py file."""
    file_path = Path("tests/loader/test_loader.py")

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Fix the imports
    content = re.sub(
        (r"from aws_entity_resolution\.loader\.loader import \(\s+LoadingResult,\s+"
         r"create_target_table,\s+.*?,\s+.*?,\s+\)"),
        "from aws_entity_resolution.loader.loader import (\n"
        "    LoadingResult,\n"
        "    create_target_table,\n"
        "    load_matched_records,\n"
        "    load_records,\n"
        ")",
        content,
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Fixed {file_path}")


if __name__ == "__main__":
    fix_test_loader()
