"""Type definitions for the AWS Entity Resolution processor."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProcessStatus(str, Enum):
    """Status of a process operation."""

    SUCCESS = "success"
    ERROR = "error"
    RUNNING = "running"
    PENDING = "pending"
    CANCELED = "canceled"


class ProcessResult(BaseModel):
    """Result of a process operation."""

    success: bool = Field(default=True, description="Whether the process was successful")
    job_id: Optional[str] = Field(default=None, description="ID of the processing job")
    status: str = Field(default="COMPLETED", description="Status of the processing job")
    total_records: int = Field(default=0, description="Total number of records processed")
    matched_records: int = Field(default=0, description="Number of records that matched")
    output_path: Optional[str] = Field(default=None, description="Path to the output file")
    error_message: Optional[str] = Field(
        default=None, description="Error message if status is ERROR"
    )
    execution_time: float = Field(default=0.0, description="Execution time in seconds")

    def __str__(self) -> str:
        """Return a string representation of the process result.

        Returns:
            String representation
        """
        if not self.success:
            return f"FAILED: {self.error_message}"
        if self.status == "COMPLETED":
            return (
                f"SUCCESS: Processed {self.total_records} records, matched {self.matched_records}"
            )
        return f"Status: {self.status}, Job ID: {self.job_id}"
