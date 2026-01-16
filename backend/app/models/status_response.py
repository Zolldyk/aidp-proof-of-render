"""Pydantic model for render job status response."""

from typing import Optional

from pydantic import BaseModel, Field


class StatusResponse(BaseModel):
    """
    Response body for GET /api/status/{job_id} endpoint.

    Contains full status information for a render job including
    progress tracking and error details if failed.

    Attributes:
        job_id: Original job ID from upload endpoint
        status: Current job status
        progress_percent: Estimated completion percentage (0-100)
        estimated_time_remaining: Seconds remaining (if known)
        error_message: Error details if status is "failed"
        provider: Render provider type (local or aidp)
        provider_job_id: Provider-specific job ID
    """

    job_id: str = Field(
        ...,
        alias="jobId",
        description="Job ID from upload endpoint",
    )
    status: str = Field(
        ...,
        description="Current job status: queued, processing, rendering_complete, failed",
    )
    progress_percent: int = Field(
        ...,
        alias="progressPercent",
        ge=0,
        le=100,
        description="Estimated completion percentage (0-100)",
    )
    estimated_time_remaining: Optional[int] = Field(
        None,
        alias="estimatedTimeRemaining",
        ge=0,
        description="Estimated seconds remaining until completion",
    )
    error_message: Optional[str] = Field(
        None,
        alias="errorMessage",
        description="Error details if status is 'failed'",
    )
    provider: str = Field(
        ...,
        description="Render provider type: 'local' or 'aidp'",
    )
    provider_job_id: Optional[str] = Field(
        None,
        alias="providerJobId",
        description="Provider-specific job ID",
    )

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [
                {
                    "jobId": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "processing",
                    "progressPercent": 67,
                    "estimatedTimeRemaining": 20,
                    "errorMessage": None,
                    "provider": "aidp",
                    "providerJobId": "aidp_123e4567-e89b-12d3-a456-426614174000",
                }
            ]
        },
    }
