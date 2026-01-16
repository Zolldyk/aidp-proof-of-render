"""
File Storage Manager Service

Manages temporary storage for uploads, renders, and proofs with filesystem operations.
Handles job metadata creation and retrieval.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

logger = logging.getLogger(__name__)


class FileStorageManager:
    """
    Manages file storage operations for upload assets and job metadata.

    Handles:
    - Saving uploaded .gltf files to temporary storage
    - Creating and managing job metadata JSON files
    - Retrieving job metadata
    """

    def __init__(self, base_path: str = "/tmp"):
        """
        Initialize FileStorageManager with base storage path.

        Args:
            base_path: Base directory for all storage operations (default: /tmp)
        """
        self.base_path = Path(base_path)
        self.uploads_path = self.base_path / "uploads"
        self.jobs_path = self.base_path / "jobs"

    async def save_upload(self, job_id: str, file: UploadFile) -> str:
        """
        Save uploaded file to storage with proper permissions.

        Creates directory structure: /tmp/uploads/{job_id}/asset.gltf
        Sets file permissions to 644 (read for all, write for owner)

        Args:
            job_id: Unique job identifier (UUID v4)
            file: FastAPI UploadFile object containing the uploaded asset

        Returns:
            str: Full path to saved file

        Raises:
            OSError: If directory creation or file write fails
        """
        # Create job-specific upload directory
        job_upload_dir = self.uploads_path / job_id
        job_upload_dir.mkdir(parents=True, exist_ok=True)

        # Save file as asset.gltf
        file_path = job_upload_dir / "asset.gltf"

        try:
            # Read file content
            content = await file.read()

            # Write to disk
            with open(file_path, "wb") as f:
                f.write(content)

            # Set file permissions: 644 (rw-r--r--)
            file_path.chmod(0o644)

            logger.info(f"Saved upload for job {job_id} to {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Failed to save upload for job {job_id}: {str(e)}")
            raise OSError(f"Failed to save uploaded file: {str(e)}")

    def create_job_metadata(self, job_id: str, filename: str, file_size: int) -> str:
        """
        Create job metadata JSON file with initial upload information.

        Creates directory structure: /tmp/jobs/{job_id}/metadata.json
        Metadata includes: job_id, upload_timestamp, filename, file_size, status

        Args:
            job_id: Unique job identifier (UUID v4)
            filename: Original uploaded filename
            file_size: File size in bytes

        Returns:
            str: Full path to metadata file

        Raises:
            OSError: If directory creation or file write fails
        """
        # Create job-specific metadata directory
        job_metadata_dir = self.jobs_path / job_id
        job_metadata_dir.mkdir(parents=True, exist_ok=True)

        # Generate metadata
        metadata = {
            "jobId": job_id,
            "status": "uploaded",
            "assetFilename": filename,
            "assetSize": file_size,
            "uploadedAt": datetime.now(timezone.utc).isoformat(),
            "presetName": None,
            "startedAt": None,
            "completedAt": None,
            "aidpJobId": None,
            "renderUrl": None,
            "proofUrl": None,
            "error": None
        }

        # Save metadata as JSON
        metadata_path = job_metadata_dir / "metadata.json"

        try:
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Created job metadata for job {job_id} at {metadata_path}")
            return str(metadata_path)

        except Exception as e:
            logger.error(f"Failed to create metadata for job {job_id}: {str(e)}")
            raise OSError(f"Failed to create job metadata: {str(e)}")

    def get_job_metadata(self, job_id: str) -> Optional[dict]:
        """
        Load and return job metadata if exists.

        Args:
            job_id: Unique job identifier (UUID v4)

        Returns:
            dict: Job metadata if file exists, None otherwise

        Handles JSON parsing errors gracefully by returning None
        """
        metadata_path = self.jobs_path / job_id / "metadata.json"

        if not metadata_path.exists():
            logger.warning(f"Metadata not found for job {job_id}")
            return None

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            logger.info(f"Loaded metadata for job {job_id}")
            return metadata

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse metadata for job {job_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to read metadata for job {job_id}: {str(e)}")
            return None
