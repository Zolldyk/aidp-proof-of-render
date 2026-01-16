"""Pydantic model for render job submission response."""

from pydantic import BaseModel, Field


class RenderResponse(BaseModel):
    """
    Response body for POST /api/render endpoint.

    Returned after successfully submitting a render job.

    Attributes:
        job_id: Original job ID from request
        status: Current job status (queued on submission)
        message: Human-readable status message
        provider_job_id: Provider-specific job ID for status tracking
        provider: Provider type (local or aidp)
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
    message: str = Field(
        ...,
        description="Human-readable status message",
    )
    provider_job_id: str = Field(
        ...,
        alias="providerJobId",
        description="Provider-specific job ID for status polling",
    )
    provider: str = Field(
        ...,
        description="Render provider type: 'local' or 'aidp'",
    )

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [
                {
                    "jobId": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "queued",
                    "message": "Render job submitted successfully",
                    "providerJobId": "aidp_123e4567-e89b-12d3-a456-426614174000",
                    "provider": "aidp",
                }
            ]
        },
    }
