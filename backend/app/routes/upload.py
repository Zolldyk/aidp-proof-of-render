"""
Upload API Route

Handles file upload endpoint for .gltf assets.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.middleware.file_size_validator import validate_file_size
from app.models.upload_response import UploadResponse
from app.services.file_storage import FileStorageManager
from app.services.file_validator import validate_gltf_format, validate_gltf_structure
from app.services.rate_limiter import check_upload_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize file storage manager
storage = FileStorageManager()


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload 3D Asset",
    description="""
Upload a .gltf 3D asset for rendering.

**Workflow:** Upload asset → Submit render → Poll status → Download result

**Constraints:**
- **Max File Size:** 10MB
- **Rate Limit:** 10 uploads per hour per IP
- **Supported Format:** .gltf (JSON format only, not GLB binary)

**Response:** Returns a unique `jobId` to use with `/api/render` endpoint.
""",
    responses={
        200: {
            "description": "Upload successful",
            "content": {
                "application/json": {
                    "example": {
                        "jobId": "550e8400-e29b-41d4-a716-446655440000",
                        "message": "Upload successful",
                        "assetFilename": "model.gltf",
                        "assetSize": 15234,
                        "nextStep": "/api/render",
                    }
                }
            },
        },
        400: {"description": "Invalid file format or empty file"},
        413: {"description": "File too large (max 10MB)"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Server error"},
    },
)
async def upload_asset(
    file: UploadFile = File(...),
    file_size: int = Depends(validate_file_size),
    rate_limit: None = Depends(check_upload_rate_limit),
) -> UploadResponse:
    """
    Upload and validate .gltf asset file.

    Args:
        file: Uploaded .gltf file (multipart/form-data)

    Returns:
        UploadResponse: Contains job ID and next steps

    Raises:
        HTTPException: For validation errors, file size limits, or storage failures
    """
    # Check if file is provided
    if not file:
        raise HTTPException(
            status_code=400,
            detail="No file provided. Please upload a .gltf file."
        )

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    logger.info(f"Upload started for job {job_id}, filename: {file.filename}")

    # Validate file format (extension and MIME type)
    validate_gltf_format(file)

    # Check for empty file (file_size validated by dependency)
    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file uploaded. Please provide a valid .gltf file."
        )

    try:
        # Save uploaded file
        file_path = await storage.save_upload(job_id, file)

        # Validate .gltf structure (requires saved file)
        validate_gltf_structure(file_path)

        # Create job metadata
        storage.create_job_metadata(job_id, file.filename, file_size)

        logger.info(f"Upload successful for job {job_id}")

        # Return success response
        return UploadResponse(
            jobId=job_id,
            message="Upload successful",
            assetFilename=file.filename,
            assetSize=file_size,
            nextStep="/api/render"
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except OSError as e:
        logger.error(f"Filesystem error for job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to save uploaded file. Please try again."
        )
    except Exception as e:
        logger.error(f"Unexpected error for job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again."
        )
