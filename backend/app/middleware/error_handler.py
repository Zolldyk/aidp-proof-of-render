"""
Centralized error handling middleware for FastAPI.

Provides consistent error responses and logging for all API routes.
"""

import logging
import traceback
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RenderError(Exception):
    """Base exception for render-related errors."""

    def __init__(self, message: str, status_code: int = 500, details: Any = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class AssetNotFoundError(RenderError):
    """Raised when asset file is not found."""

    def __init__(self, job_id: str):
        super().__init__(
            message=f"Asset file not found for job {job_id}",
            status_code=404,
            details={"job_id": job_id},
        )


class InvalidPresetError(RenderError):
    """Raised when preset name is invalid."""

    def __init__(self, preset: str, valid_presets: list[str]):
        super().__init__(
            message=f"Invalid preset '{preset}'. Valid presets: {', '.join(valid_presets)}",
            status_code=400,
            details={"preset": preset, "valid_presets": valid_presets},
        )


class JobNotFoundError(RenderError):
    """Raised when job ID is not found."""

    def __init__(self, job_id: str):
        super().__init__(
            message=f"Job not found: {job_id}",
            status_code=404,
            details={"job_id": job_id},
        )


class RenderTimeoutError(RenderError):
    """Raised when render exceeds timeout."""

    def __init__(self, job_id: str, timeout_seconds: int):
        super().__init__(
            message=f"Render timeout after {timeout_seconds} seconds",
            status_code=500,
            details={"job_id": job_id, "timeout_seconds": timeout_seconds},
        )


class BlenderCrashError(RenderError):
    """Raised when Blender subprocess crashes."""

    def __init__(self, job_id: str, stderr: str | None = None):
        super().__init__(
            message="Blender render process crashed",
            status_code=500,
            details={"job_id": job_id, "stderr": stderr},
        )


class DiskWriteError(RenderError):
    """Raised when file write operations fail."""

    def __init__(self, path: str, reason: str):
        super().__init__(
            message=f"Failed to write file: {reason}",
            status_code=500,
            details={"path": path, "reason": reason},
        )


class ProviderUnavailableError(RenderError):
    """Raised when render provider is not available."""

    def __init__(self, provider: str):
        super().__init__(
            message=f"Render provider '{provider}' is not available",
            status_code=503,
            details={"provider": provider},
        )


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware that catches unhandled exceptions and returns consistent error responses.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response

        except RenderError as e:
            logger.error(
                f"RenderError: {e.message}",
                extra={"status_code": e.status_code, "details": e.details},
            )
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": e.message,
                    "details": e.details,
                },
            )

        except Exception as e:
            # Log full stack trace for unexpected errors
            logger.exception(f"Unhandled exception: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": str(e) if logger.isEnabledFor(logging.DEBUG) else None,
                },
            )


def format_error_response(
    status_code: int,
    message: str,
    details: Any = None,
) -> dict:
    """
    Format a consistent error response.

    Args:
        status_code: HTTP status code
        message: Human-readable error message
        details: Additional error details (optional)

    Returns:
        dict: Formatted error response
    """
    response = {
        "error": True,
        "status_code": status_code,
        "message": message,
    }
    if details:
        response["details"] = details
    return response
