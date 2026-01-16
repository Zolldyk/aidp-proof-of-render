"""
Integration Tests for Upload Endpoint

Tests the complete upload flow including validation, storage, and error handling.
"""

import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.rate_limiter import upload_rate_limiter

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter before each test."""
    upload_rate_limiter.requests.clear()
    yield
    upload_rate_limiter.requests.clear()


@pytest.fixture
def valid_gltf_file():
    """Load valid .gltf test file."""
    test_asset_path = Path(__file__).parent.parent.parent / "render_engine" / "test_assets" / "suzanne.gltf"
    with open(test_asset_path, "rb") as f:
        return f.read()


def test_successful_upload(valid_gltf_file):
    """Test successful upload with valid .gltf file."""
    # Upload file
    response = client.post(
        "/api/upload",
        files={"file": ("suzanne.gltf", valid_gltf_file, "model/gltf+json")}
    )

    # Assert response status
    assert response.status_code == 200

    # Parse response
    data = response.json()

    # Assert response structure
    assert "jobId" in data
    assert "message" in data
    assert "assetFilename" in data
    assert "assetSize" in data
    assert "nextStep" in data

    # Assert response values
    assert data["message"] == "Upload successful"
    assert data["assetFilename"] == "suzanne.gltf"
    assert data["assetSize"] > 0
    assert data["nextStep"] == "/api/render"

    # Verify job ID is valid UUID
    job_id = data["jobId"]
    assert len(job_id) == 36  # UUID v4 format

    # Verify file exists at expected location
    upload_path = Path("/tmp/uploads") / job_id / "asset.gltf"
    assert upload_path.exists()
    assert upload_path.stat().st_size > 0

    # Verify metadata exists
    metadata_path = Path("/tmp/jobs") / job_id / "metadata.json"
    assert metadata_path.exists()

    # Verify metadata structure
    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    assert metadata["jobId"] == job_id
    assert metadata["status"] == "uploaded"
    assert metadata["assetFilename"] == "suzanne.gltf"
    assert metadata["assetSize"] > 0
    assert "uploadedAt" in metadata
    assert metadata["presetName"] is None
    assert metadata["startedAt"] is None
    assert metadata["completedAt"] is None


def test_file_size_limit_exceeded():
    """Test upload fails when file exceeds 10MB limit."""
    # Create 11MB file
    large_file = io.BytesIO(b"0" * (11 * 1024 * 1024))

    # Upload oversized file
    response = client.post(
        "/api/upload",
        files={"file": ("large.gltf", large_file, "model/gltf+json")}
    )

    # Assert 413 error
    assert response.status_code == 413

    # Assert error message
    data = response.json()
    assert "detail" in data
    assert "File size exceeds 10MB limit" in data["detail"]


def test_invalid_file_format():
    """Test upload fails with invalid file format."""
    # Create .obj file (unsupported format)
    obj_content = b"# Blender OBJ File\nv 0 0 0\n"

    # Upload .obj file
    response = client.post(
        "/api/upload",
        files={"file": ("model.obj", obj_content, "text/plain")}
    )

    # Assert 400 error
    assert response.status_code == 400

    # Assert error message
    data = response.json()
    assert "detail" in data
    assert "Invalid file format" in data["detail"]


def test_corrupted_gltf_file():
    """Test upload fails with corrupted .gltf file."""
    # Create invalid JSON with .gltf extension
    corrupted_content = b"not valid json{]"

    # Upload corrupted file
    response = client.post(
        "/api/upload",
        files={"file": ("corrupted.gltf", corrupted_content, "model/gltf+json")}
    )

    # Assert 400 error
    assert response.status_code == 400

    # Assert error message
    data = response.json()
    assert "detail" in data
    assert "Corrupted .gltf file" in data["detail"]


def test_missing_file():
    """Test upload fails when no file is provided."""
    # Send POST request without file field
    response = client.post("/api/upload")

    # Assert 422 error (FastAPI validation error for missing field)
    assert response.status_code == 422

    # Assert error details
    data = response.json()
    assert "detail" in data


def test_empty_file():
    """Test upload fails with 0-byte file."""
    # Create empty file
    empty_file = io.BytesIO(b"")

    # Upload empty file
    response = client.post(
        "/api/upload",
        files={"file": ("empty.gltf", empty_file, "model/gltf+json")}
    )

    # Assert 400 error
    assert response.status_code == 400

    # Assert error message
    data = response.json()
    assert "detail" in data
    assert "Empty file" in data["detail"]


def test_rate_limiting(valid_gltf_file):
    """Test rate limiting blocks 11th upload."""
    # Upload 10 files (should all succeed)
    for i in range(10):
        response = client.post(
            "/api/upload",
            files={"file": (f"suzanne_{i}.gltf", valid_gltf_file, "model/gltf+json")}
        )
        assert response.status_code == 200, f"Request {i + 1} failed"

    # 11th upload should fail with 429 error
    response = client.post(
        "/api/upload",
        files={"file": ("suzanne_11.gltf", valid_gltf_file, "model/gltf+json")}
    )

    # Assert 429 error
    assert response.status_code == 429

    # Assert error message
    data = response.json()
    assert "detail" in data
    assert "Rate limit exceeded" in data["detail"]
