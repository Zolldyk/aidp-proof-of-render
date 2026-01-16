"""
Render endpoints for job submission and status tracking.

Provides POST /api/render for submitting render jobs and
GET /api/status/{job_id} for checking job status.
"""

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models import RenderRequest, RenderResponse, StatusResponse
from app.services import get_render_provider
from app.services.render_task import execute_render_job
from render_engine.preset_loader import list_available_presets

logger = logging.getLogger(__name__)

router = APIRouter()

# Valid presets (loaded dynamically but cached for validation)
VALID_PRESETS: list[str] = []


def _get_valid_presets() -> list[str]:
    """Get list of valid preset names, caching result."""
    global VALID_PRESETS
    if not VALID_PRESETS:
        try:
            VALID_PRESETS = list_available_presets()
        except Exception:
            VALID_PRESETS = ["studio", "sunset", "dramatic"]
    return VALID_PRESETS


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


def _update_job_metadata(job_id: str, **updates) -> bool:
    """Update job metadata with given fields."""
    metadata_path = Path(f"/tmp/jobs/{job_id}/metadata.json")
    if not metadata_path.exists():
        return False
    try:
        with open(metadata_path) as f:
            metadata = json.load(f)
        metadata.update(updates)
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        return True
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to update metadata for {job_id}: {e}")
        return False


@router.post(
    "/render",
    response_model=RenderResponse,
    summary="Submit Render Job",
    description="""
Submit a render job for a previously uploaded .gltf asset.

The job will be processed using the configured render provider:
- **MockAIDPProvider** (default): Local Blender rendering with simulated AIDP lifecycle
- **AIDPProvider** (future): Real AIDP GPU network integration

Job status transitions: `queued` → `processing` → `rendering_complete` | `failed`

Use GET /api/status/{job_id} to poll for completion.
""",
    responses={
        200: {"description": "Render job submitted successfully"},
        400: {"description": "Invalid preset name"},
        404: {"description": "Job ID not found"},
        500: {"description": "Internal server error"},
    },
)
async def submit_render(
    request: RenderRequest,
    background_tasks: BackgroundTasks,
) -> RenderResponse:
    """
    Submit a render job for processing.

    Args:
        request: RenderRequest with job_id and preset
        background_tasks: FastAPI BackgroundTasks for scheduling status monitor

    Returns:
        RenderResponse with job status and provider details

    Raises:
        HTTPException 400: If preset is invalid
        HTTPException 404: If job_id not found
        HTTPException 500: On internal errors
    """
    job_id = request.job_id
    preset = request.preset

    logger.info(f"Render submission received: job_id={job_id}, preset={preset}")

    # Validate job exists
    metadata = _get_job_metadata(job_id)
    if metadata is None:
        logger.warning(f"Job not found: {job_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}. Upload asset first via POST /api/upload",
        )

    # Validate preset
    valid_presets = _get_valid_presets()
    if preset not in valid_presets:
        logger.warning(f"Invalid preset: {preset}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid preset '{preset}'. Valid presets: {', '.join(valid_presets)}",
        )

    # Verify asset file exists
    asset_path = Path(f"/tmp/uploads/{job_id}/asset.gltf")
    if not asset_path.exists():
        logger.error(f"Asset file missing for job {job_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Asset file not found for job {job_id}. Re-upload required.",
        )

    try:
        # Get render provider
        provider = get_render_provider()

        # Submit job to provider
        provider_job_id = await provider.submit_job(
            job_id=job_id,
            asset_path=str(asset_path),
            preset=preset,
        )

        # Update metadata with render job info
        _update_job_metadata(
            job_id,
            status="queued",
            presetName=preset,
            providerJobId=provider_job_id,
            provider=provider.provider_name,
        )

        logger.info(
            f"Render job submitted: job_id={job_id}, "
            f"provider_job_id={provider_job_id}, provider={provider.provider_name}"
        )

        # Schedule background task to monitor render progress and update metadata
        background_tasks.add_task(
            execute_render_job,
            job_id=job_id,
            provider_job_id=provider_job_id,
            provider=provider,
        )

        return RenderResponse(
            job_id=job_id,
            status="queued",
            message="Render job submitted successfully",
            provider_job_id=provider_job_id,
            provider=provider.provider_name,
        )

    except FileNotFoundError as e:
        logger.error(f"Asset not found during submit: {e}")
        raise HTTPException(status_code=404, detail=str(e))

    except ValueError as e:
        logger.error(f"Invalid preset during submit: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except NotImplementedError as e:
        logger.error(f"Provider not implemented: {e}")
        raise HTTPException(
            status_code=500,
            detail="Render provider not available. Check USE_MOCK_AIDP configuration.",
        )

    except Exception as e:
        logger.exception(f"Render submission failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit render job: {str(e)}",
        )


@router.get(
    "/status/{job_id}",
    response_model=StatusResponse,
    summary="Get Job Status",
    description="""
Get the current status of a render job.

Returns progress information, estimated completion time, and error details if failed.

Status values:
- **queued**: Job waiting to be processed
- **processing**: Render in progress
- **rendering_complete**: Render finished successfully
- **failed**: Render failed (check errorMessage)
""",
    responses={
        200: {"description": "Job status retrieved successfully"},
        404: {"description": "Job not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_job_status(job_id: str) -> StatusResponse:
    """
    Get current status of a render job.

    Args:
        job_id: Job ID from upload endpoint

    Returns:
        StatusResponse with current status and progress

    Raises:
        HTTPException 404: If job_id not found
        HTTPException 500: On internal errors
    """
    logger.info(f"Status request: job_id={job_id}")

    # Load job metadata
    metadata = _get_job_metadata(job_id)
    if metadata is None:
        logger.warning(f"Job not found: {job_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}",
        )

    # Get provider job ID from metadata
    provider_job_id = metadata.get("providerJobId")
    provider_name = metadata.get("provider", "local")

    # If no provider job ID, job hasn't been submitted for rendering yet
    if not provider_job_id:
        return StatusResponse(
            job_id=job_id,
            status=metadata.get("status", "uploaded"),
            progress_percent=0,
            estimated_time_remaining=None,
            error_message=metadata.get("error"),
            provider=provider_name,
            provider_job_id=None,
        )

    try:
        # Get live status from provider
        provider = get_render_provider()
        provider_status = await provider.get_status(provider_job_id)

        # Update metadata with latest status
        _update_job_metadata(
            job_id,
            status=provider_status["status"],
            error=provider_status.get("error_message"),
        )

        return StatusResponse(
            job_id=job_id,
            status=provider_status["status"],
            progress_percent=provider_status.get("progress_percent", 0),
            estimated_time_remaining=provider_status.get("estimated_time_remaining"),
            error_message=provider_status.get("error_message"),
            provider=provider_name,
            provider_job_id=provider_job_id,
        )

    except KeyError:
        # Provider doesn't have this job - return metadata status
        logger.warning(f"Provider job not found: {provider_job_id}")
        return StatusResponse(
            job_id=job_id,
            status=metadata.get("status", "unknown"),
            progress_percent=0,
            estimated_time_remaining=None,
            error_message="Provider job not found",
            provider=provider_name,
            provider_job_id=provider_job_id,
        )

    except NotImplementedError as e:
        logger.error(f"Provider not implemented: {e}")
        raise HTTPException(
            status_code=500,
            detail="Render provider not available. Check configuration.",
        )

    except Exception as e:
        logger.exception(f"Status check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job status: {str(e)}",
        )
