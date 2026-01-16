"""FastAPI middleware for request/response processing."""

from .error_handler import (
    ErrorHandlerMiddleware,
    RenderError,
    AssetNotFoundError,
    InvalidPresetError,
    JobNotFoundError,
    RenderTimeoutError,
    BlenderCrashError,
    DiskWriteError,
    ProviderUnavailableError,
    format_error_response,
)

__all__ = [
    "ErrorHandlerMiddleware",
    "RenderError",
    "AssetNotFoundError",
    "InvalidPresetError",
    "JobNotFoundError",
    "RenderTimeoutError",
    "BlenderCrashError",
    "DiskWriteError",
    "ProviderUnavailableError",
    "format_error_response",
]
