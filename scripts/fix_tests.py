#!/usr/bin/env python
"""Helper script to set up environment variables for tests."""

import os
import subprocess
from pathlib import Path


def run_command(command, capture=True):
    """Run a shell command."""
    print(f"Running: {command}")
    if capture:
        # nosec B602: This is a controlled script used only by developers
        result = subprocess.run(  # nosec
            command, shell=True, check=False, capture_output=True, text=True
        )
        return result
    # nosec B602: This is a controlled script used only by developers
    return subprocess.run(command, shell=True, check=False)  # nosec


def create_env_file():
    """Create a .env file with test environment variables."""
    print("\n--- Creating .env file for tests ---")

    env_file = Path(".env.test")

    if env_file.exists():
        print(f"{env_file} already exists")
        return

    env_vars = {
        "AWS_REGION": "us-west-2",
        "AWS_ACCESS_KEY_ID": "test-key",
        "AWS_SECRET_ACCESS_KEY": "test-secret",
        "SNOWFLAKE_ACCOUNT": "test-account",
        "SNOWFLAKE_USERNAME": "test-user",
        "SNOWFLAKE_PASSWORD": "test-password",
        "SNOWFLAKE_WAREHOUSE": "test-warehouse",
        "SNOWFLAKE_SOURCE_DATABASE": "test-source-db",
        "SNOWFLAKE_SOURCE_SCHEMA": "test-source-schema",
        "SNOWFLAKE_TARGET_DATABASE": "test-target-db",
        "SNOWFLAKE_TARGET_SCHEMA": "test-target-schema",
        "S3_BUCKET_NAME": "test-bucket",
        "S3_PREFIX": "test-prefix/",
        "ER_WORKFLOW_NAME": "test-workflow",
        "ER_SCHEMA_NAME": "test-schema",
        "ER_ENTITY_ATTRIBUTES": "id,name,email",
        "SOURCE_TABLE": "test_source",
        "TARGET_TABLE": "test_target",
    }

    with open(env_file, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    print(f"Created {env_file} with test variables")


def update_pytest_ini():
    """Update pytest.ini to load environment variables from .env.test."""
    print("\n--- Updating pytest.ini ---")

    pytest_ini = Path("pytest.ini")

    if not pytest_ini.exists():
        print("Creating new pytest.ini file")
        with open(pytest_ini, "w") as f:
            f.write("[pytest]\n")
            f.write("testpaths = tests\n")
            f.write("env_files = .env.test\n")
    else:
        print("Updating existing pytest.ini file")
        with open(pytest_ini) as f:
            content = f.read()

        if "env_files" not in content:
            with open(pytest_ini, "a") as f:
                f.write("\nenv_files = .env.test\n")

        print("Updated pytest.ini with env_files setting")


def update_conftest():
    """Update conftest.py to load environment variables from .env.test."""
    print("\n--- Updating conftest.py ---")

    conftest = Path("tests/conftest.py")

    if not conftest.exists():
        print("Error: conftest.py not found")
        return

    with open(conftest) as f:
        content = f.read()

    # Check if python-dotenv is already being used
    if "dotenv" not in content:
        print("Adding dotenv loading to conftest.py")

        # Read current content
        with open(conftest) as f:
            lines = f.readlines()

        # Find import section
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.startswith(("import ", "from ")):
                insert_pos = i + 1

        # Add dotenv import
        lines.insert(insert_pos, "from dotenv import load_dotenv\n")

        # Find pytest_configure or add it
        has_configure = False
        for i, line in enumerate(lines):
            if "def pytest_configure" in line:
                has_configure = True
                configure_pos = i + 1
                # Check if there's already a load_dotenv call
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith("def "):
                    if "load_dotenv" in lines[j]:
                        has_configure = False  # Already has dotenv loading
                        break
                    j += 1
                break

        if has_configure:
            # Add load_dotenv to existing configure
            lines.insert(configure_pos, "    load_dotenv('.env.test')\n")
        else:
            # Add new configure function
            lines.append("\n\ndef pytest_configure():\n")
            lines.append('    """Load environment variables before tests."""\n')
            lines.append("    load_dotenv('.env.test')\n")

        # Write updated content
        with open(conftest, "w") as f:
            f.writelines(lines)

        print("Updated conftest.py to load .env.test")
    else:
        print("conftest.py already appears to load dotenv")


def update_requirements():
    """Ensure pytest-env is in dev dependencies."""
    print("\n--- Checking dependencies ---")

    # Check if pytest-env is in pyproject.toml
    with open("pyproject.toml") as f:
        content = f.read()

    if "pytest-env" not in content:
        print("Adding pytest-env to dev dependencies")
        run_command("poetry add --group dev pytest-env", capture=False)
    else:
        print("pytest-env is already in dependencies")


def main():
    """Main function."""
    # Set the project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    print("===== Test Environment Setup =====")

    # Create .env file with test variables
    create_env_file()

    # Update pytest configuration
    update_pytest_ini()

    # Update conftest.py
    update_conftest()

    # Update dependencies
    update_requirements()

    print("\n===== Test Environment Setup Complete =====")
    print("Run 'pytest' to check if tests are now passing.")


if __name__ == "__main__":
    main()
