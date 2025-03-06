#!/usr/bin/env python
"""Helper script to fix Terraform issues."""

import os
import re
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


def fix_step_functions_tf():
    """Fix the step-functions.tf file with proper quoting for $ symbols."""
    print("\n--- Fixing step-functions.tf ---")

    # Path to the terraform file
    tf_file = Path("terraform/modules/step-functions/main.tf")

    if not tf_file.exists():
        print(f"Error: {tf_file} not found")
        return

    with open(tf_file) as f:
        content = f.read()

    # Fix the problematic lines with $ symbols
    # In Terraform, $ needs to be escaped as $$ when used in HCL strings
    # But for Step Functions JSON, we use a single $ and surround with quotes
    fixed_content = re.sub(
        r'(\s*)execution\.(\$)(\s*=\s*)"(\$\$.Execution.Id)"', r'\1"execution.$"\3"\4"', content
    )

    fixed_content = re.sub(r'(\s*)error\.(\$)(\s*=\s*)"(\$.error)"', r'\1"error.$"\3"\4"', content)

    # Check if we made changes
    if fixed_content != content:
        with open(tf_file, "w") as f:
            f.write(fixed_content)
        print(f"Fixed {tf_file} with proper quoting for $ symbols")
    else:
        print(f"No changes needed in {tf_file}")


def fix_terraform_modules():
    """Fix Terraform modules with depends_on issues."""
    print("\n--- Fixing Terraform modules ---")

    # Path to the main.tf file
    tf_file = Path("terraform/modules/entity-resolution-pipeline/main.tf")

    if not tf_file.exists():
        print(f"Error: {tf_file} not found")
        return

    with open(tf_file) as f:
        content = f.read()

    # Remove depends_on from legacy modules
    fixed_content = re.sub(
        r"(\s*)(depends_on\s*=\s*\[.*?\])",
        r"\1# \2  # Commented out due to legacy module compatibility",
        content,
    )

    # Check if we made changes
    if fixed_content != content:
        with open(tf_file, "w") as f:
            f.write(fixed_content)
        print(f"Fixed {tf_file} by commenting out depends_on for legacy modules")
    else:
        print(f"No changes needed in {tf_file}")


def fix_snowflake_provider():
    """Update the Snowflake provider configuration."""
    print("\n--- Fixing Snowflake provider ---")

    # Add provider configuration in modules
    modules = [
        "terraform/modules/schema/snowflake",
    ]

    for module_path in modules:
        provider_file = Path(f"{module_path}/providers.tf")

        if not provider_file.exists():
            # Create providers.tf
            provider_file.parent.mkdir(parents=True, exist_ok=True)

            with open(provider_file, "w") as f:
                f.write(
                    """terraform {
  required_providers {
    snowflake = {
      source  = "Snowflake-Labs/snowflake"
      version = "~> 0.68"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "snowflake" {
  # Snowflake provider configuration is provided through environment variables:
  # SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, SNOWFLAKE_ROLE
}

provider "aws" {
  region = var.aws_region
}
"""
                )
            print(f"Created {provider_file}")
        else:
            print(f"{provider_file} already exists")


def fix_entity_resolution_resources():
    """Fix AWS Entity Resolution resource issues."""
    print("\n--- Fixing Entity Resolution resource issues ---")

    # Create a fix for entity-resolution module
    module_path = "terraform/modules/schema"
    provider_file = Path(f"{module_path}/providers.tf")

    if not provider_file.exists():
        # Create providers.tf
        provider_file.parent.mkdir(parents=True, exist_ok=True)

        with open(provider_file, "w") as f:
            f.write(
                """terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Comment regarding Entity Resolution resources:
# As of this version, AWS Provider may not support aws_entityresolution* resources yet.
# You may need to use a custom provider or AWS CLI/SDK directly.
# This can be addressed by using local-exec provisioners or null resources.
"""
            )
        print(f"Created {provider_file}")
    else:
        print(f"{provider_file} already exists")


def main():
    """Main function."""
    # Set the project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    print("===== Terraform Issue Fixer =====")

    # Fix Terraform step-functions.tf
    fix_step_functions_tf()

    # Fix Terraform modules with depends_on
    fix_terraform_modules()

    # Fix Snowflake provider
    fix_snowflake_provider()

    # Fix Entity Resolution resources
    fix_entity_resolution_resources()

    print("\n===== Terraform Issue Fixer Complete =====")
    print("Run terraform fmt and validate to check if issues have been resolved.")


if __name__ == "__main__":
    main()
