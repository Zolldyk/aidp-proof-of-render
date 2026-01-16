"""
Upload Response Pydantic Model

Defines the response structure for successful file uploads.
"""

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """
    Response model for successful file upload.

    Returned by POST /api/upload endpoint after successful upload and validation.
    """

    jobId: str = Field(
        ...,
        description="UUID v4 job identifier for tracking upload through render pipeline"
    )
    message: str = Field(
        ...,
        description="Success message confirming upload completion"
    )
    assetFilename: str = Field(
        ...,
        description="Original uploaded filename (e.g., 'dragon.gltf')"
    )
    assetSize: int = Field(
        ...,
        description="File size in bytes"
    )
    nextStep: str = Field(
        ...,
        description="Next API endpoint to call (e.g., '/api/render')"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "jobId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "message": "Upload successful",
                "assetFilename": "dragon.gltf",
                "assetSize": 2457600,
                "nextStep": "/api/render"
            }
        }
    }
