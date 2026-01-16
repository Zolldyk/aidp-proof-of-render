"""
Background render task for status monitoring and metadata updates.

Polls render provider and updates job metadata.json until completion.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .render_provider import RenderProvider

logger = logging.getLogger(__name__)


def _update_job_metadata(job_id: str, **updates) -> bool:
    """Update job metadata JSON file with given fields."""
    metadata_path = Path(f"/tmp/jobs/{job_id}/metadata.json")
    if not metadata_path.exists():
        logger.warning(f"Metadata file not found: {metadata_path}")
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


def _save_render_output(job_id: str, result_bytes: bytes) -> str | None:
    """
    Save rendered PNG to output directory.

    Args:
        job_id: Job identifier
        result_bytes: PNG image bytes

    Returns:
        str: Path to saved file, or None if failed
    """
    output_dir = Path(f"/tmp/outputs/{job_id}")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "render.png"

    try:
        output_path.write_bytes(result_bytes)
        logger.info(f"Saved render output: {output_path}")
        return str(output_path)
    except OSError as e:
        logger.error(f"Failed to save render output for {job_id}: {e}")
        return None


async def execute_render_job(
    job_id: str,
    provider_job_id: str,
    provider: RenderProvider,
    poll_interval: float = 2.0,
) -> None:
    """
    Background task to monitor render job and update metadata.

    Polls provider every poll_interval seconds until job completes or fails.
    Updates metadata.json with status changes and saves output when complete.

    Args:
        job_id: Original job ID from upload
        provider_job_id: Provider-specific job ID
        provider: RenderProvider instance to poll
        poll_interval: Seconds between status polls (default: 2.0)
    """
    logger.info(
        f"Starting background render monitor: job_id={job_id}, "
        f"provider_job_id={provider_job_id}"
    )

    try:
        while True:
            await asyncio.sleep(poll_interval)

            try:
                status = await provider.get_status(provider_job_id)
            except KeyError:
                logger.error(f"Provider lost job: {provider_job_id}")
                _update_job_metadata(
                    job_id,
                    status="failed",
                    error="Provider lost job during processing",
                    completedAt=datetime.now(timezone.utc).isoformat(),
                )
                break

            # Update metadata with current status
            _update_job_metadata(
                job_id,
                status=status["status"],
                progressPercent=status.get("progress_percent", 0),
                error=status.get("error_message"),
            )

            if status["status"] == "rendering_complete":
                # Get render result and save
                result = await provider.get_result(provider_job_id)
                if result:
                    output_path = _save_render_output(job_id, result)
                    _update_job_metadata(
                        job_id,
                        renderUrl=f"/outputs/{job_id}/render.png",
                        completedAt=datetime.now(timezone.utc).isoformat(),
                    )
                    logger.info(f"Render job complete: {job_id}")
                else:
                    logger.warning(f"No result bytes for completed job: {job_id}")
                break

            elif status["status"] == "failed":
                _update_job_metadata(
                    job_id,
                    error=status.get("error_message", "Render failed"),
                    completedAt=datetime.now(timezone.utc).isoformat(),
                )
                logger.error(
                    f"Render job failed: {job_id} - {status.get('error_message')}"
                )
                break

    except asyncio.CancelledError:
        logger.warning(f"Render monitor cancelled: {job_id}")
        raise

    except Exception as e:
        logger.exception(f"Render monitor error: {job_id}")
        _update_job_metadata(
            job_id,
            status="failed",
            error=str(e),
            completedAt=datetime.now(timezone.utc).isoformat(),
        )
