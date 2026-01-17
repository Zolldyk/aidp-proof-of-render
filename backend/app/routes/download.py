"""
Download endpoint for retrieving rendered files.

Provides GET /api/download/{jobId} for downloading render output or proof files.
"""

import json
import logging
import re
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from app.models import DownloadErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Valid job statuses for download
COMPLETE_STATUSES = {"rendering_complete", "complete"}


def _validate_job_id(job_id: str) -> bool:
    """
    Validate that job_id is a valid UUID format to prevent path traversal.

    Args:
        job_id: The job ID to validate

    Returns:
        bool: True if valid UUID format, False otherwise
    """
    try:
        UUID(job_id, version=4)
        return True
    except (ValueError, AttributeError):
        # Also check for version-agnostic UUID format
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        return bool(uuid_pattern.match(job_id))


def _get_job_metadata(job_id: str) -> dict | None:
    """Load job metadata from filesystem."""
    metadata_path = Path(f"/tmp/jobs/{job_id}/metadata.json")
    if not metadata_path.exists():
        return None
    try:
        with open(metadata_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


@router.get(
    "/download/{jobId}",
    summary="Download Render Output",
    description="""
Download the rendered output or proof file for a completed job.

**Query Parameters:**
- `file`: Type of file to download (default: "render")
  - `render`: Download the rendered PNG image
  - `proof`: Download the cryptographic proof JSON (Epic 2)

**Response:**
- **200**: File download with appropriate Content-Type
- **404**: Job not found, invalid UUID, or job failed
- **409**: Job not complete yet (still processing)

**Security:** Job IDs are validated as UUIDs to prevent path traversal attacks.
""",
    responses={
        200: {"description": "File download successful"},
        404: {
            "description": "Job not found or failed",
            "model": DownloadErrorResponse,
        },
        409: {
            "description": "Job not complete yet",
            "model": DownloadErrorResponse,
        },
    },
)
async def download_job_output(
    jobId: str,
    file: str = Query(
        default="render",
        description="Type of file to download",
        pattern="^(render|proof)$",
    ),
) -> FileResponse:
    """
    Download rendered output or proof file for a completed job.

    Args:
        jobId: Job ID (UUID format) from upload endpoint
        file: Type of file to download ("render" or "proof")

    Returns:
        FileResponse with the requested file

    Raises:
        HTTPException 404: If job not found, invalid UUID, or job failed
        HTTPException 409: If job not complete yet
    """
    logger.info(f"Download request: jobId={jobId}, file={file}")

    # Validate UUID format (security: prevent path traversal)
    if not _validate_job_id(jobId):
        logger.warning(f"Invalid jobId format: {jobId}")
        return JSONResponse(
            status_code=404,
            content=DownloadErrorResponse(
                error="invalid_job_id",
                jobId=jobId,
                status=None,
                message="Invalid job ID format. Must be a valid UUID.",
            ).model_dump(),
        )

    # Load job metadata
    metadata = _get_job_metadata(jobId)
    if metadata is None:
        logger.warning(f"Job not found: {jobId}")
        return JSONResponse(
            status_code=404,
            content=DownloadErrorResponse(
                error="not_found",
                jobId=jobId,
                status=None,
                message=f"Job not found: {jobId}",
            ).model_dump(),
        )

    # Check job status
    status = metadata.get("status", "unknown")

    # Handle failed jobs
    if status == "failed":
        error_message = metadata.get("error", "Unknown error")
        logger.warning(f"Download attempted for failed job: {jobId}")
        return JSONResponse(
            status_code=404,
            content=DownloadErrorResponse(
                error="failed",
                jobId=jobId,
                status=status,
                message=f"Render failed: {error_message}. File not available.",
            ).model_dump(),
        )

    # Check if job is complete
    if status not in COMPLETE_STATUSES:
        logger.info(f"Download attempted for incomplete job: {jobId}, status={status}")
        return JSONResponse(
            status_code=409,
            content=DownloadErrorResponse(
                error="not_complete",
                jobId=jobId,
                status=status,
                message=f"Job is still processing. Current status: {status}",
            ).model_dump(),
        )

    # Determine file path based on requested file type
    if file == "render":
        file_path = Path(f"/tmp/outputs/{jobId}/render.png")
        media_type = "image/png"
        filename = f"{jobId}_render.png"
    else:  # proof
        file_path = Path(f"/tmp/outputs/{jobId}/proof.json")
        media_type = "application/json"
        filename = f"{jobId}_proof.json"

    # Check file exists
    if not file_path.exists():
        logger.error(f"Output file not found: {file_path}")
        return JSONResponse(
            status_code=404,
            content=DownloadErrorResponse(
                error="file_not_found",
                jobId=jobId,
                status=status,
                message=f"Output file not found. The {file} file may not have been generated.",
            ).model_dump(),
        )

    logger.info(f"Serving download: {file_path}")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
