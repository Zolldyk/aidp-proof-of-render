"""
File Size Validation Middleware

Validates uploaded file size without loading entire file into memory.
"""

import logging

from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger(__name__)

# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes


async def validate_file_size(file: UploadFile) -> int:
    """
    Validate uploaded file size without loading entire file into memory.

    Reads file in chunks to check size constraint. Resets file pointer
    to beginning after validation for subsequent processing.

    Args:
        file: FastAPI UploadFile object

    Returns:
        int: Total file size in bytes

    Raises:
        HTTPException: 413 if file exceeds MAX_FILE_SIZE (10MB)
    """
    size = 0
    chunk_size = 1024 * 1024  # 1MB chunks

    # Read file in chunks to calculate total size
    while chunk := await file.read(chunk_size):
        size += len(chunk)
        if size > MAX_FILE_SIZE:
            logger.warning(f"File size exceeded: {size} bytes (max: {MAX_FILE_SIZE})")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds 10MB limit"
            )

    # Reset file pointer to beginning for subsequent reads
    await file.seek(0)

    logger.info(f"File size validation passed: {size} bytes")
    return size
