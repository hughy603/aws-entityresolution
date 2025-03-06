"""Type definitions for the AWS Entity Resolution loader."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class LoadStatus(str, Enum):
    """Status of a load operation."""

    SUCCESS = "success"
    ERROR = "error"
    CRITICAL_ERROR = "critical_error"
    SKIPPED = "skipped"
    PARTIAL = "partial"


class LoadResult(BaseModel):
    """Result of a load operation."""

    status: LoadStatus = Field(
        default=LoadStatus.SUCCESS, description="Status of the load operation"
    )
    records_processed: int = Field(default=0, description="Number of records processed")
    records_loaded: int = Field(default=0, description="Number of records loaded")
    records_failed: int = Field(default=0, description="Number of records that failed to load")
    error_message: Optional[str] = Field(
        default=None, description="Error message if status is ERROR"
    )
    details: dict[str, Any] = Field(default_factory=dict, description="Additional details")

    def __str__(self) -> str:
        """Return a string representation of the load result.

        Returns:
            String representation
        """
        if self.status == LoadStatus.ERROR:
            return f"FAILED: {self.error_message}"
        if self.status == LoadStatus.SUCCESS:
            return f"SUCCESS: Loaded {self.records_loaded} records"
        if self.status == LoadStatus.SKIPPED:
            return "SKIPPED: No records to load"
        return f"PARTIAL: Loaded {self.records_loaded} records, {self.records_failed} failed"
