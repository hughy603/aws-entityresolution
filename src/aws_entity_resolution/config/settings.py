from typing import Optional

"""Example of secure password handling."""

import os


def get_password() -> Optional[str]:
    """Get password from environment variable securely."""
    return os.environ.get("DB_PASSWORD")
