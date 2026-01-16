"""
Unit Tests for FileStorageManager

Tests file storage operations in isolation.
"""

import json
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.services.file_storage import FileStorageManager


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage directory for testing."""
    return FileStorageManager(base_path=str(tmp_path))


@pytest.fixture
def mock_upload_file():
    """Create mock UploadFile for testing."""
    content = b"fake gltf content"
    file_obj = BytesIO(content)
    return UploadFile(filename="test.gltf", file=file_obj)


@pytest.mark.asyncio
async def test_save_upload_creates_directory_and_file(temp_storage, mock_upload_file):
    """Test that save_upload creates directory and saves file correctly."""
    job_id = "test-job-123"

    # Save upload
    file_path = await temp_storage.save_upload(job_id, mock_upload_file)

    # Verify path is correct
    expected_path = Path(temp_storage.uploads_path) / job_id / "asset.gltf"
    assert file_path == str(expected_path)

    # Verify directory was created
    assert expected_path.parent.exists()
    assert expected_path.parent.is_dir()

    # Verify file was created
    assert expected_path.exists()
    assert expected_path.is_file()

    # Verify file content
    with open(expected_path, "rb") as f:
        content = f.read()
    assert content == b"fake gltf content"

    # Verify file permissions (644 = rw-r--r--)
    # Note: Permission checking may vary by OS
    assert expected_path.stat().st_mode & 0o777 == 0o644


def test_create_job_metadata_generates_correct_structure(temp_storage):
    """Test that create_job_metadata generates correct JSON structure."""
    job_id = "test-job-456"
    filename = "dragon.gltf"
    file_size = 2457600

    # Create metadata
    metadata_path = temp_storage.create_job_metadata(job_id, filename, file_size)

    # Verify path is correct
    expected_path = Path(temp_storage.jobs_path) / job_id / "metadata.json"
    assert metadata_path == str(expected_path)

    # Verify file was created
    assert expected_path.exists()
    assert expected_path.is_file()

    # Load and verify metadata structure
    with open(expected_path, "r") as f:
        metadata = json.load(f)

    # Verify all required fields
    assert metadata["jobId"] == job_id
    assert metadata["status"] == "uploaded"
    assert metadata["assetFilename"] == filename
    assert metadata["assetSize"] == file_size
    assert "uploadedAt" in metadata
    assert metadata["presetName"] is None
    assert metadata["startedAt"] is None
    assert metadata["completedAt"] is None
    assert metadata["aidpJobId"] is None
    assert metadata["renderUrl"] is None
    assert metadata["proofUrl"] is None
    assert metadata["error"] is None

    # Verify uploadedAt is valid ISO 8601 timestamp
    upload_timestamp = metadata["uploadedAt"]
    # Should be parseable as datetime
    parsed_time = datetime.fromisoformat(upload_timestamp)
    assert isinstance(parsed_time, datetime)


def test_get_job_metadata_returns_none_for_missing_job(temp_storage):
    """Test that get_job_metadata returns None for non-existent job."""
    job_id = "non-existent-job"

    # Try to get metadata for non-existent job
    metadata = temp_storage.get_job_metadata(job_id)

    # Should return None
    assert metadata is None


def test_get_job_metadata_loads_existing_metadata(temp_storage):
    """Test that get_job_metadata correctly loads existing metadata."""
    job_id = "test-job-789"

    # Create metadata manually
    metadata_dir = Path(temp_storage.jobs_path) / job_id
    metadata_dir.mkdir(parents=True, exist_ok=True)

    test_metadata = {
        "jobId": job_id,
        "status": "uploaded",
        "assetFilename": "test.gltf",
        "assetSize": 1024,
        "uploadedAt": "2026-01-04T10:30:00Z"
    }

    metadata_path = metadata_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(test_metadata, f)

    # Load metadata
    loaded_metadata = temp_storage.get_job_metadata(job_id)

    # Verify metadata was loaded correctly
    assert loaded_metadata is not None
    assert loaded_metadata["jobId"] == job_id
    assert loaded_metadata["status"] == "uploaded"
    assert loaded_metadata["assetFilename"] == "test.gltf"
    assert loaded_metadata["assetSize"] == 1024
    assert loaded_metadata["uploadedAt"] == "2026-01-04T10:30:00Z"
