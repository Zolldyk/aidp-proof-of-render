"""
LocalBlenderProvider - Direct Blender subprocess execution.

Implements RenderProvider interface using local Blender installation
for rendering via subprocess execution.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from app.config import settings
from render_engine.blender_renderer import execute_preset_render
from .render_provider import RenderProvider

logger = logging.getLogger(__name__)


class LocalBlenderProvider(RenderProvider):
    """
    Render provider using local Blender subprocess execution.

    Manages render jobs by executing Blender in headless mode,
    tracking job state in memory, and returning results.
    """

    def __init__(self):
        """Initialize LocalBlenderProvider with empty job tracking."""
        self._jobs: Dict[str, Dict] = {}
        self._output_base = Path("/tmp/outputs")
        logger.info("[LOCAL] LocalBlenderProvider initialized")

    @property
    def provider_name(self) -> str:
        """Return provider identifier."""
        return "local"

    async def submit_job(self, job_id: str, asset_path: str, preset: str) -> str:
        """
        Submit a render job for local Blender execution.

        Args:
            job_id: Unique job identifier from upload endpoint
            asset_path: Full path to the .gltf asset file
            preset: Preset name (studio, sunset, dramatic)

        Returns:
            str: Provider job ID in format "local_{uuid}"

        Raises:
            FileNotFoundError: If asset_path doesn't exist
            ValueError: If preset is invalid
        """
        # Validate asset exists
        if not Path(asset_path).exists():
            raise FileNotFoundError(f"Asset file not found: {asset_path}")

        # Generate provider job ID
        provider_job_id = f"local_{uuid.uuid4()}"

        # Prepare output path
        output_dir = self._output_base / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / "render.png")

        # Initialize job tracking
        self._jobs[provider_job_id] = {
            "job_id": job_id,
            "asset_path": asset_path,
            "preset": preset,
            "output_path": output_path,
            "status": "queued",
            "progress_percent": 0,
            "estimated_time_remaining": None,
            "error_message": None,
            "started_at": None,
            "completed_at": None,
            "queued_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            f"[LOCAL] Job submitted: {provider_job_id} for job_id={job_id}, "
            f"preset={preset}"
        )

        # Start render in background task
        asyncio.create_task(self._execute_render(provider_job_id))

        return provider_job_id

    async def _execute_render(self, provider_job_id: str) -> None:
        """
        Execute Blender render in background.

        Updates job status through the render lifecycle:
        queued → processing → rendering_complete | failed
        """
        job = self._jobs.get(provider_job_id)
        if not job:
            logger.error(f"[LOCAL] Job not found for execution: {provider_job_id}")
            return

        try:
            # Transition to processing
            job["status"] = "processing"
            job["started_at"] = datetime.now(timezone.utc).isoformat()
            job["progress_percent"] = 10
            job["estimated_time_remaining"] = settings.RENDER_TIMEOUT

            logger.info(f"[LOCAL] Starting render: {provider_job_id}")

            # Execute render in thread pool to avoid blocking
            start_time = time.time()
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                execute_preset_render,
                job["asset_path"],
                job["preset"],
                job["output_path"],
            )

            elapsed = time.time() - start_time

            if result["success"]:
                job["status"] = "rendering_complete"
                job["progress_percent"] = 100
                job["estimated_time_remaining"] = 0
                job["completed_at"] = datetime.now(timezone.utc).isoformat()
                logger.info(
                    f"[LOCAL] Render complete: {provider_job_id} "
                    f"in {elapsed:.2f}s"
                )
            else:
                job["status"] = "failed"
                job["error_message"] = result.get("error", "Unknown render error")
                job["completed_at"] = datetime.now(timezone.utc).isoformat()
                logger.error(
                    f"[LOCAL] Render failed: {provider_job_id} - "
                    f"{job['error_message']}"
                )

        except Exception as e:
            job["status"] = "failed"
            job["error_message"] = str(e)
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
            logger.exception(f"[LOCAL] Render exception: {provider_job_id}")

    async def get_status(self, provider_job_id: str) -> Dict:
        """
        Get current status of a render job.

        Args:
            provider_job_id: Provider job ID from submit_job()

        Returns:
            dict: Status information with progress details

        Raises:
            KeyError: If provider_job_id not found
        """
        if provider_job_id not in self._jobs:
            raise KeyError(f"Job not found: {provider_job_id}")

        job = self._jobs[provider_job_id]

        # Estimate progress based on elapsed time if processing
        if job["status"] == "processing" and job["started_at"]:
            started = datetime.fromisoformat(job["started_at"])
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            expected_duration = 60.0  # Assume ~60s for typical render

            progress = min(95, int((elapsed / expected_duration) * 100))
            remaining = max(0, int(expected_duration - elapsed))

            job["progress_percent"] = progress
            job["estimated_time_remaining"] = remaining

        return {
            "status": job["status"],
            "progress_percent": job["progress_percent"],
            "estimated_time_remaining": job["estimated_time_remaining"],
            "error_message": job["error_message"],
            "started_at": job["started_at"],
            "completed_at": job["completed_at"],
        }

    async def get_result(self, provider_job_id: str) -> Optional[bytes]:
        """
        Get rendered image bytes if job is complete.

        Args:
            provider_job_id: Provider job ID from submit_job()

        Returns:
            bytes: PNG image data if complete, None otherwise

        Raises:
            KeyError: If provider_job_id not found
        """
        if provider_job_id not in self._jobs:
            raise KeyError(f"Job not found: {provider_job_id}")

        job = self._jobs[provider_job_id]

        if job["status"] != "rendering_complete":
            return None

        output_path = Path(job["output_path"])
        if not output_path.exists():
            logger.error(f"[LOCAL] Output file missing: {output_path}")
            return None

        return output_path.read_bytes()
