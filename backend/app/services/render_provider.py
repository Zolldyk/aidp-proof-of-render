"""
RenderProvider abstraction layer for render backends.

Defines the interface for render providers (local Blender, AIDP, etc.)
allowing the API to swap between providers via configuration.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional


class RenderProvider(ABC):
    """
    Abstract base class for render providers.

    Defines the interface that all render backends must implement,
    enabling provider swapping via environment configuration.

    Implementations:
    - LocalBlenderProvider: Direct Blender subprocess execution
    - MockAIDPProvider: Simulates AIDP lifecycle with local rendering
    - AIDPProvider: Real AIDP GPU network integration (future)
    """

    @abstractmethod
    async def submit_job(self, job_id: str, asset_path: str, preset: str) -> str:
        """
        Submit a render job to the provider.

        Args:
            job_id: Unique job identifier from upload endpoint
            asset_path: Full path to the .gltf asset file
            preset: Preset name for scene configuration (studio, sunset, dramatic)

        Returns:
            str: Provider-specific job ID for status tracking
                 Format varies by provider:
                 - LocalBlenderProvider: "local_{uuid}"
                 - MockAIDPProvider: "aidp_{uuid}"

        Raises:
            FileNotFoundError: If asset_path doesn't exist
            ValueError: If preset is invalid
        """
        pass

    @abstractmethod
    async def get_status(self, provider_job_id: str) -> Dict:
        """
        Get current status of a render job.

        Args:
            provider_job_id: Provider-specific job ID from submit_job()

        Returns:
            dict: Status information containing:
                - status (str): One of "queued", "processing",
                                "rendering_complete", "failed"
                - progress_percent (int): 0-100 completion estimate
                - estimated_time_remaining (int | None): Seconds remaining
                - error_message (str | None): Error details if failed
                - started_at (str | None): ISO timestamp when processing began
                - completed_at (str | None): ISO timestamp when finished

        Raises:
            KeyError: If provider_job_id not found
        """
        pass

    @abstractmethod
    async def get_result(self, provider_job_id: str) -> Optional[bytes]:
        """
        Get rendered image bytes if job is complete.

        Args:
            provider_job_id: Provider-specific job ID from submit_job()

        Returns:
            bytes: PNG image data if render is complete
            None: If job is still processing or failed

        Raises:
            KeyError: If provider_job_id not found
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Return provider identifier for API responses.

        Returns:
            str: Provider name - "local" or "aidp"
        """
        pass
