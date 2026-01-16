"""
MockAIDPProvider - Simulates AIDP GPU network with local rendering.

Wraps LocalBlenderProvider to simulate AIDP job lifecycle
for development and testing without actual AIDP credentials.
"""

import asyncio
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from .local_blender_provider import LocalBlenderProvider
from .render_provider import RenderProvider

logger = logging.getLogger(__name__)


class MockAIDPProvider(RenderProvider):
    """
    Mock AIDP provider that simulates AIDP lifecycle with local rendering.

    Wraps LocalBlenderProvider and adds:
    - AIDP-style job IDs (aidp_{uuid})
    - Realistic queue delay (2-5 seconds)
    - Mock AIDP metadata in status responses
    - [MOCK-AIDP] prefixed logging for debugging
    """

    def __init__(self):
        """Initialize MockAIDPProvider with LocalBlenderProvider backend."""
        self._local_provider = LocalBlenderProvider()
        self._jobs: Dict[str, Dict] = {}
        logger.info("[MOCK-AIDP] MockAIDPProvider initialized (simulating AIDP API)")

    @property
    def provider_name(self) -> str:
        """Return provider identifier for API responses."""
        return "aidp"

    async def submit_job(self, job_id: str, asset_path: str, preset: str) -> str:
        """
        Submit a render job with simulated AIDP queuing.

        Adds a random 2-5 second queue delay before actual render
        to simulate AIDP job scheduling behavior.

        Args:
            job_id: Unique job identifier from upload endpoint
            asset_path: Full path to the .gltf asset file
            preset: Preset name (studio, sunset, dramatic)

        Returns:
            str: Provider job ID in AIDP format "aidp_{uuid}"

        Raises:
            FileNotFoundError: If asset_path doesn't exist
            ValueError: If preset is invalid
        """
        # Generate AIDP-style job ID
        aidp_job_id = f"aidp_{uuid.uuid4()}"

        # Initialize job tracking with AIDP metadata
        queue_delay = random.uniform(2.0, 5.0)
        self._jobs[aidp_job_id] = {
            "job_id": job_id,
            "asset_path": asset_path,
            "preset": preset,
            "status": "queued",
            "progress_percent": 0,
            "estimated_time_remaining": None,
            "error_message": None,
            "started_at": None,
            "completed_at": None,
            "queued_at": datetime.now(timezone.utc).isoformat(),
            "queue_delay": queue_delay,
            "provider_id": "mock-provider-001",
            "local_provider_job_id": None,
        }

        logger.info(
            f"[MOCK-AIDP] Job submitted: {aidp_job_id} for job_id={job_id}, "
            f"preset={preset}, queue_delay={queue_delay:.1f}s"
        )

        # Start simulated AIDP lifecycle
        asyncio.create_task(self._simulate_aidp_lifecycle(aidp_job_id))

        return aidp_job_id

    async def _simulate_aidp_lifecycle(self, aidp_job_id: str) -> None:
        """
        Simulate AIDP job lifecycle with queue delay.

        Lifecycle: queued (2-5s) → processing → rendering_complete | failed
        """
        job = self._jobs.get(aidp_job_id)
        if not job:
            logger.error(f"[MOCK-AIDP] Job not found: {aidp_job_id}")
            return

        try:
            # Simulate queue delay
            logger.info(
                f"[MOCK-AIDP] Job queued: {aidp_job_id}, "
                f"waiting {job['queue_delay']:.1f}s"
            )
            await asyncio.sleep(job["queue_delay"])

            # Transition to processing and submit to local provider
            job["status"] = "processing"
            job["started_at"] = datetime.now(timezone.utc).isoformat()

            logger.info(f"[MOCK-AIDP] Job processing: {aidp_job_id}")

            # Submit to local Blender provider
            local_job_id = await self._local_provider.submit_job(
                job["job_id"], job["asset_path"], job["preset"]
            )
            job["local_provider_job_id"] = local_job_id

            # Poll local provider until complete
            while True:
                await asyncio.sleep(1.0)

                try:
                    local_status = await self._local_provider.get_status(local_job_id)
                except KeyError:
                    job["status"] = "failed"
                    job["error_message"] = "Local provider lost job"
                    job["completed_at"] = datetime.now(timezone.utc).isoformat()
                    break

                # Update progress from local provider
                job["progress_percent"] = local_status["progress_percent"]
                job["estimated_time_remaining"] = local_status[
                    "estimated_time_remaining"
                ]

                if local_status["status"] == "rendering_complete":
                    job["status"] = "rendering_complete"
                    job["progress_percent"] = 100
                    job["estimated_time_remaining"] = 0
                    job["completed_at"] = datetime.now(timezone.utc).isoformat()
                    logger.info(
                        f"[MOCK-AIDP] Job complete: {aidp_job_id}"
                    )
                    break

                elif local_status["status"] == "failed":
                    job["status"] = "failed"
                    job["error_message"] = local_status.get(
                        "error_message", "Render failed"
                    )
                    job["completed_at"] = datetime.now(timezone.utc).isoformat()
                    logger.error(
                        f"[MOCK-AIDP] Job failed: {aidp_job_id} - "
                        f"{job['error_message']}"
                    )
                    break

        except Exception as e:
            job["status"] = "failed"
            job["error_message"] = str(e)
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
            logger.exception(f"[MOCK-AIDP] Job exception: {aidp_job_id}")

    async def get_status(self, provider_job_id: str) -> Dict:
        """
        Get current status with AIDP-style metadata.

        Args:
            provider_job_id: AIDP job ID from submit_job()

        Returns:
            dict: Status with AIDP metadata including provider_id,
                  started_at, estimated_completion

        Raises:
            KeyError: If provider_job_id not found
        """
        if provider_job_id not in self._jobs:
            raise KeyError(f"Job not found: {provider_job_id}")

        job = self._jobs[provider_job_id]

        # Calculate estimated completion time
        estimated_completion = None
        if job["status"] == "processing" and job["started_at"]:
            started = datetime.fromisoformat(job["started_at"])
            remaining = job.get("estimated_time_remaining") or 60
            estimated_completion = (
                started.replace(tzinfo=timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            )
            if remaining > 0:
                from datetime import timedelta

                est_complete = datetime.now(timezone.utc) + timedelta(seconds=remaining)
                estimated_completion = est_complete.isoformat().replace("+00:00", "Z")

        return {
            "job_id": provider_job_id,
            "status": job["status"],
            "progress_percent": job["progress_percent"],
            "estimated_time_remaining": job["estimated_time_remaining"],
            "error_message": job["error_message"],
            "started_at": job["started_at"],
            "completed_at": job["completed_at"],
            "provider_id": job["provider_id"],
            "estimated_completion": estimated_completion,
        }

    async def get_result(self, provider_job_id: str) -> Optional[bytes]:
        """
        Get rendered image bytes via local provider.

        Args:
            provider_job_id: AIDP job ID from submit_job()

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

        local_job_id = job.get("local_provider_job_id")
        if not local_job_id:
            logger.error(f"[MOCK-AIDP] No local job ID for: {provider_job_id}")
            return None

        return await self._local_provider.get_result(local_job_id)
