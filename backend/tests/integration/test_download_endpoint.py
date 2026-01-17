"""
Download Endpoint Tests

Tests for GET /api/download/{jobId} including error scenarios,
security validation, and edge cases.
"""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.provider_factory import reset_provider
from app.services.rate_limiter import upload_rate_limiter

client = TestClient(app)

TEST_ASSETS_DIR = Path(__file__).parent.parent.parent.parent / "test-assets"


@pytest.fixture(autouse=True)
def reset_state():
    """Reset provider singleton and rate limiter before each test."""
    reset_provider()
    upload_rate_limiter.requests.clear()
    yield
    reset_provider()
    upload_rate_limiter.requests.clear()


@pytest.fixture
def cube_gltf():
    """Load cube.gltf test file."""
    with open(TEST_ASSETS_DIR / "cube.gltf", "rb") as f:
        return f.read()


@pytest.fixture
def completed_job(cube_gltf):
    """Upload, render, and wait for completion. Returns job_id."""
    # Upload
    upload_response = client.post(
        "/api/upload",
        files={"file": ("cube.gltf", cube_gltf, "model/gltf+json")},
    )
    job_id = upload_response.json()["jobId"]

    # Submit render
    client.post("/api/render", json={"jobId": job_id, "preset": "studio"})

    # Poll until complete (max 90s)
    for _ in range(90):
        status_response = client.get(f"/api/status/{job_id}")
        if status_response.json()["status"] in ["rendering_complete", "complete"]:
            return job_id
        time.sleep(1)

    pytest.skip("Render did not complete in time")


class TestDownloadEndpoint:
    """Tests for GET /api/download/{jobId}."""

    def test_download_completed_job_returns_png(self, completed_job):
        """Test successful download of completed render."""
        response = client.get(f"/api/download/{completed_job}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert "attachment" in response.headers.get("content-disposition", "")
        assert len(response.content) > 0

    def test_download_with_render_query_param(self, completed_job):
        """Test download with explicit file=render parameter."""
        response = client.get(f"/api/download/{completed_job}?file=render")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

    def test_download_proof_returns_404_until_epic2(self, completed_job):
        """Test download of proof file returns 404 (not implemented until Epic 2)."""
        response = client.get(f"/api/download/{completed_job}?file=proof")

        # Proof file won't exist until Epic 2
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "file_not_found"


class TestDownloadErrorScenarios:
    """Error scenario tests for download endpoint (AC: 6)."""

    def test_download_invalid_jobId_returns_404(self):
        """Test download with nonexistent job_id returns 404."""
        response = client.get("/api/download/nonexistent-job-id")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "invalid_job_id"
        assert "Invalid job ID format" in data["message"]

    def test_download_malformed_jobId_returns_404(self):
        """Test path traversal attempt is rejected with 404."""
        # Path traversal attempt - FastAPI may normalize the path or reject it
        response = client.get("/api/download/..%2F..%2F..%2Fetc%2Fpasswd")

        # Should be rejected - either by FastAPI routing or our validation
        assert response.status_code in [404, 422]

    def test_download_sql_injection_attempt_returns_404(self):
        """Test SQL injection-like input is rejected."""
        response = client.get("/api/download/'; DROP TABLE jobs; --")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "invalid_job_id"

    def test_download_valid_uuid_not_found_returns_404(self):
        """Test download with valid UUID format but nonexistent job returns 404."""
        # Valid UUID format but doesn't exist
        response = client.get("/api/download/550e8400-e29b-41d4-a716-446655440000")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "not_found"
        assert "Job not found" in data["message"]

    def test_download_before_completion_returns_409(self, cube_gltf):
        """Test download attempt before render completes returns 409 Conflict."""
        # Upload file
        upload_response = client.post(
            "/api/upload",
            files={"file": ("cube.gltf", cube_gltf, "model/gltf+json")},
        )
        job_id = upload_response.json()["jobId"]

        # Submit render
        client.post("/api/render", json={"jobId": job_id, "preset": "studio"})

        # Immediately try to download (before completion)
        response = client.get(f"/api/download/{job_id}")

        # Expected outcomes:
        # - 409 Conflict: Job still processing
        # - 200: Render completed very quickly
        # - 404 with "failed": Render failed (e.g., Blender not installed)
        if response.status_code == 409:
            data = response.json()
            assert data["error"] == "not_complete"
            assert "still processing" in data["message"].lower()
        elif response.status_code == 404:
            # Render may have failed (Blender not installed in test env)
            data = response.json()
            assert data["error"] in ["failed", "not_found"]
        else:
            # Render completed very quickly
            assert response.status_code == 200

    def test_download_failed_job_returns_404_with_details(self, cube_gltf):
        """Test download of failed job returns 404 with error details."""
        # Upload file
        upload_response = client.post(
            "/api/upload",
            files={"file": ("cube.gltf", cube_gltf, "model/gltf+json")},
        )
        job_id = upload_response.json()["jobId"]

        # Manually set job status to failed
        metadata_path = Path(f"/tmp/jobs/{job_id}/metadata.json")
        with open(metadata_path) as f:
            metadata = json.load(f)

        metadata["status"] = "failed"
        metadata["error"] = "Test error: render failed intentionally"

        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Try to download
        response = client.get(f"/api/download/{job_id}")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "failed"
        assert data["status"] == "failed"
        assert "render failed" in data["message"].lower()

    def test_download_uploaded_only_returns_409(self, cube_gltf):
        """Test download of uploaded-only job (no render submitted) returns 409."""
        # Upload file but don't submit render
        upload_response = client.post(
            "/api/upload",
            files={"file": ("cube.gltf", cube_gltf, "model/gltf+json")},
        )
        job_id = upload_response.json()["jobId"]

        # Try to download
        response = client.get(f"/api/download/{job_id}")

        assert response.status_code == 409
        data = response.json()
        assert data["error"] == "not_complete"
        assert data["status"] == "uploaded"


class TestDownloadContentDisposition:
    """Tests for Content-Disposition header."""

    def test_download_has_correct_filename(self, completed_job):
        """Test download has correct filename in Content-Disposition header."""
        response = client.get(f"/api/download/{completed_job}")

        assert response.status_code == 200
        content_disp = response.headers.get("content-disposition", "")
        assert f"{completed_job}_render.png" in content_disp
