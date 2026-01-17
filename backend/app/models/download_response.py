"""
Download endpoint response models.

Provides error response schemas for download endpoint error cases.
"""

from typing import Optional

from pydantic import BaseModel, Field


class DownloadErrorResponse(BaseModel):
    """Error response for download endpoint failures."""

    error: str = Field(..., description="Error type identifier")
    jobId: str = Field(..., description="Job ID that was requested")
    status: Optional[str] = Field(None, description="Current job status if available")
    message: str = Field(..., description="Human-readable error message")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "not_found",
                    "jobId": "550e8400-e29b-41d4-a716-446655440000",
                    "status": None,
                    "message": "Job not found",
                },
                {
                    "error": "not_complete",
                    "jobId": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "processing",
                    "message": "Job is still processing. Current status: processing",
                },
                {
                    "error": "failed",
                    "jobId": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "failed",
                    "message": "Render failed: Invalid asset geometry",
                },
            ]
        }
    }
