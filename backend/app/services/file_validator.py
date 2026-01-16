"""
File Validation Service

Validates file format and structure for uploaded .gltf assets.
"""

import logging

from fastapi import HTTPException, UploadFile
from pygltflib import GLTF2

logger = logging.getLogger(__name__)


def validate_gltf_format(file: UploadFile) -> None:
    """
    Validate file format for .gltf uploads.

    Checks:
    1. File extension must be .gltf
    2. MIME type should be model/gltf+json (accepts application/json or empty as fallback)

    Args:
        file: FastAPI UploadFile object

    Raises:
        HTTPException: 400 if file format is invalid
    """
    # Check file extension
    if not file.filename or not file.filename.lower().endswith('.gltf'):
        logger.warning(f"Invalid file extension: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only .gltf files are supported."
        )

    # Check MIME type (with fallbacks for different clients)
    accepted_mime_types = [
        'model/gltf+json',      # Standard MIME type
        'application/json',     # Fallback for some browsers
        'application/octet-stream',  # Fallback for generic upload
        '',                     # Empty MIME type from some clients
        None                    # No MIME type set
    ]

    if file.content_type not in accepted_mime_types:
        logger.warning(
            f"Invalid MIME type: {file.content_type} for file {file.filename}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid MIME type. Expected model/gltf+json, got {file.content_type}"
        )

    logger.info(f"File format validation passed for {file.filename}")


def validate_gltf_structure(file_path: str) -> None:
    """
    Validate .gltf file structure using pygltflib.

    Verifies file is well-formed and contains valid scene data.
    Requires file to be saved to disk first (pygltflib needs file path).

    Args:
        file_path: Absolute path to saved .gltf file

    Raises:
        HTTPException: 400 if file is corrupted or has invalid structure
    """
    try:
        # Load .gltf file
        gltf = GLTF2.load(file_path)

        # Verify file contains valid scene data
        if not gltf.scenes:
            logger.error(f"GLTF validation failed: No scenes found in {file_path}")
            raise HTTPException(
                status_code=400,
                detail="Invalid .gltf file: No scenes found"
            )

        if not gltf.nodes:
            logger.error(f"GLTF validation failed: No nodes found in {file_path}")
            raise HTTPException(
                status_code=400,
                detail="Invalid .gltf file: No nodes found"
            )

        logger.info(
            f"Valid .gltf structure: {len(gltf.scenes)} scenes, "
            f"{len(gltf.nodes)} nodes"
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"GLTF structure validation failed for {file_path}: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Corrupted .gltf file: {str(e)}"
        )
