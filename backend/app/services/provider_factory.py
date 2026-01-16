"""
Provider factory for render backend selection.

Returns appropriate RenderProvider based on USE_MOCK_AIDP configuration.
"""

import logging

from app.config import settings
from .mock_aidp_provider import MockAIDPProvider
from .render_provider import RenderProvider

logger = logging.getLogger(__name__)

# Singleton provider instance
_provider_instance: RenderProvider | None = None


def get_render_provider() -> RenderProvider:
    """
    Get the configured render provider instance.

    Uses singleton pattern to maintain job state across requests.

    Returns:
        RenderProvider: MockAIDPProvider if USE_MOCK_AIDP=true,
                        raises NotImplementedError for real AIDP (future Story 1.6.1)

    Raises:
        NotImplementedError: If USE_MOCK_AIDP=false (real AIDP not yet implemented)
    """
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    if settings.USE_MOCK_AIDP:
        logger.info(
            "Initializing MockAIDPProvider (USE_MOCK_AIDP=true) - "
            "local Blender rendering with simulated AIDP lifecycle"
        )
        _provider_instance = MockAIDPProvider()
    else:
        # Future: Story 1.6.1 will implement real AIDP provider
        # from .aidp_provider import AIDPProvider
        # _provider_instance = AIDPProvider()
        raise NotImplementedError(
            "Real AIDP provider not yet implemented. "
            "Set USE_MOCK_AIDP=true or see Story 1.6.1 for AIDP integration."
        )

    return _provider_instance


def reset_provider() -> None:
    """
    Reset the provider singleton (for testing purposes).

    Clears the cached provider instance, allowing a fresh
    provider to be created on next get_render_provider() call.
    """
    global _provider_instance
    _provider_instance = None
    logger.info("Provider singleton reset")
