"""Pydantic model for render job submission request."""

from pydantic import BaseModel, Field


class RenderRequest(BaseModel):
    """
    Request body for POST /api/render endpoint.

    Attributes:
        job_id: Job ID returned from upload endpoint (UUID v4)
        preset: Scene preset name for rendering configuration
    """

    job_id: str = Field(
        ...,
        alias="jobId",
        description="Job ID from upload endpoint (UUID v4 format)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    preset: str = Field(
        ...,
        description="Preset name: studio, sunset, or dramatic",
        examples=["studio"],
    )

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [{"jobId": "550e8400-e29b-41d4-a716-446655440000", "preset": "studio"}]
        },
    }
