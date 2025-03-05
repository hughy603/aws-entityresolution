#!/usr/bin/env python3
"""Fix imports and function calls in test_processor.py to match the available functions in
processor.py."""

import re
from pathlib import Path


def fix_test_processor() -> None:
    """Fix the imports and function calls in test_processor.py to match the available functions in
    processor.py."""
    test_file = Path("tests/processor/test_processor.py")

    if not test_file.exists():
        print(f"Error: {test_file} does not exist")
        return

    content = test_file.read_text()

    # Replace the import statement
    pattern = r"from aws_entity_resolution\.processor\.processor import \(\n(.*?)\)"
    replacement = """from aws_entity_resolution.processor.processor import (
    ProcessingResult,
    process_data,
    wait_for_matching_job,
)"""

    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    # Add import for S3Service
    if "from aws_entity_resolution.services import S3Service" not in new_content:
        import_pattern = r"from aws_entity_resolution\.config import \(\n(.*?)\)"
        import_replacement = "from aws_entity_resolution.config import (\\1)\n\nfrom aws_entity_resolution.services import EntityResolutionService, S3Service"
        new_content = re.sub(import_pattern, import_replacement, new_content, flags=re.DOTALL)

    # Replace test_find_latest_input_path functions with S3Service.find_latest_path
    # First, update the function names
    new_content = re.sub(
        r"def test_find_latest_input_path_success",
        "def test_s3_service_find_latest_path_success",
        new_content,
    )
    new_content = re.sub(
        r"def test_find_latest_input_path_no_data",
        "def test_s3_service_find_latest_path_no_data",
        new_content,
    )
    new_content = re.sub(
        r"def test_find_latest_input_path_s3_error",
        "def test_s3_service_find_latest_path_s3_error",
        new_content,
    )

    # Then, update the function calls
    new_content = re.sub(
        r"result = find_latest_input_path\(mock_settings\)",
        "s3_service = S3Service(mock_settings)\n        result = s3_service.find_latest_path()",
        new_content,
    )

    new_content = re.sub(
        r"find_latest_input_path\(mock_settings\)",
        "s3_service = S3Service(mock_settings)\n            s3_service.find_latest_path()",
        new_content,
    )

    # Update start_matching_job references to use EntityResolutionService
    new_content = re.sub(
        r"job_id = start_matching_job\(mock_settings, \"(.*?)\"\)",
        """er_service = EntityResolutionService(mock_settings)
        job_id = er_service.start_matching_job("\\1", "output/")""",
        new_content,
    )

    new_content = re.sub(
        r"start_matching_job\(mock_settings, \"(.*?)\"\)",
        """er_service = EntityResolutionService(mock_settings)
            er_service.start_matching_job("\\1", "output/")""",
        new_content,
    )

    # In case another import syntax is used
    if "ProcessingResult" not in new_content:
        new_content = re.sub(
            r"from aws_entity_resolution\.processor\.processor import \(\n(.*?)\)",
            """from aws_entity_resolution.processor.processor import (\\1)

from aws_entity_resolution.services import (
    EntityResolutionService,
    S3Service
)""",
            new_content,
            flags=re.DOTALL,
        )

    test_file.write_text(new_content)
    print(f"Fixed {test_file}")


if __name__ == "__main__":
    fix_test_processor()
