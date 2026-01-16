"""
Integration Tests for Render Endpoints

Tests the complete render flow including job submission, status tracking,
and error handling for POST /api/render and GET /api/status/{job_id}.
"""

import json
import time
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.provider_factory import reset_provider
from app.services.rate_limiter import upload_rate_limiter

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset provider singleton and rate limiter before each test."""
    reset_provider()
    upload_rate_limiter.requests.clear()
    yield
    reset_provider()
    upload_rate_limiter.requests.clear()


@pytest.fixture
def valid_gltf_file():
    """Load valid .gltf test file."""
    test_asset_path = (
        Path(__file__).parent.parent.parent / "render_engine" / "test_assets" / "suzanne.gltf"
    )
    with open(test_asset_path, "rb") as f:
        return f.read()


@pytest.fixture
def uploaded_job(valid_gltf_file):
    """Upload a file and return the job ID."""
    response = client.post(
        "/api/upload",
        files={"file": ("suzanne.gltf", valid_gltf_file, "model/gltf+json")},
    )
    assert response.status_code == 200
    return response.json()["jobId"]


class TestPostRenderEndpoint:
    """Tests for POST /api/render endpoint."""

    def test_submit_render_with_valid_job_and_preset(self, uploaded_job):
        """Test successful render submission with valid job_id and preset."""
        response = client.post(
            "/api/render",
            json={"jobId": uploaded_job, "preset": "studio"},
        )

        assert response.status_code == 200

        data = response.json()
        assert data["jobId"] == uploaded_job
        assert data["status"] == "queued"
        assert data["message"] == "Render job submitted successfully"
        assert "providerJobId" in data
        assert data["provider"] in ["local", "aidp"]

    def test_submit_render_with_all_valid_presets(self, valid_gltf_file):
        """Test render submission works with all valid preset names."""
        valid_presets = ["studio", "sunset", "dramatic"]

        for preset in valid_presets:
            # Upload new file for each preset
            upload_response = client.post(
                "/api/upload",
                files={"file": (f"test_{preset}.gltf", valid_gltf_file, "model/gltf+json")},
            )
            job_id = upload_response.json()["jobId"]

            # Submit render
            response = client.post(
                "/api/render",
                json={"jobId": job_id, "preset": preset},
            )

            assert response.status_code == 200, f"Failed for preset: {preset}"
            assert response.json()["status"] == "queued"

    def test_submit_render_invalid_job_id_returns_404(self):
        """Test render submission fails with 404 for invalid job_id."""
        response = client.post(
            "/api/render",
            json={"jobId": "nonexistent-job-id", "preset": "studio"},
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_submit_render_invalid_preset_returns_400(self, uploaded_job):
        """Test render submission fails with 400 for invalid preset."""
        response = client.post(
            "/api/render",
            json={"jobId": uploaded_job, "preset": "invalid_preset"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "invalid preset" in data["detail"].lower()
        # Should list valid presets
        assert "studio" in data["detail"]

    def test_submit_render_missing_job_id_returns_422(self):
        """Test render submission fails with 422 for missing job_id."""
        response = client.post(
            "/api/render",
            json={"preset": "studio"},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_submit_render_missing_preset_returns_422(self, uploaded_job):
        """Test render submission fails with 422 for missing preset."""
        response = client.post(
            "/api/render",
            json={"jobId": uploaded_job},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_submit_render_updates_metadata(self, uploaded_job):
        """Test render submission updates job metadata.json."""
        response = client.post(
            "/api/render",
            json={"jobId": uploaded_job, "preset": "sunset"},
        )

        assert response.status_code == 200

        # Check metadata was updated
        metadata_path = Path(f"/tmp/jobs/{uploaded_job}/metadata.json")
        assert metadata_path.exists()

        with open(metadata_path) as f:
            metadata = json.load(f)

        # Status may have progressed from "queued" to "processing" or "failed"
        # depending on whether Blender is installed and how fast the background task runs
        assert metadata["status"] in ["queued", "processing", "rendering_complete", "failed"]
        assert metadata["presetName"] == "sunset"
        assert "providerJobId" in metadata
        assert "provider" in metadata


class TestGetStatusEndpoint:
    """Tests for GET /api/status/{job_id} endpoint."""

    def test_get_status_valid_job_returns_200(self, uploaded_job):
        """Test status check returns 200 for valid job."""
        # First submit a render
        client.post(
            "/api/render",
            json={"jobId": uploaded_job, "preset": "studio"},
        )

        # Check status
        response = client.get(f"/api/status/{uploaded_job}")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure (AC 14)
        assert "jobId" in data
        assert "status" in data
        assert "progressPercent" in data
        assert "estimatedTimeRemaining" in data or data["estimatedTimeRemaining"] is None
        assert "errorMessage" in data or data["errorMessage"] is None
        assert "provider" in data

    def test_get_status_invalid_job_returns_404(self):
        """Test status check returns 404 for invalid job_id."""
        response = client.get("/api/status/nonexistent-job-id")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_get_status_before_render_submission(self, uploaded_job):
        """Test status check works for uploaded but not-yet-rendered job."""
        response = client.get(f"/api/status/{uploaded_job}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "uploaded"
        assert data["progressPercent"] == 0

    def test_get_status_all_required_fields_present(self, uploaded_job):
        """Test status response includes all required fields per AC 14."""
        # Submit render first
        client.post(
            "/api/render",
            json={"jobId": uploaded_job, "preset": "studio"},
        )

        response = client.get(f"/api/status/{uploaded_job}")
        assert response.status_code == 200

        data = response.json()

        # Required fields per AC 14
        required_fields = [
            "jobId",
            "status",
            "progressPercent",
            "estimatedTimeRemaining",
            "errorMessage",
            "provider",
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"


class TestRenderWorkflow:
    """Integration tests for the full render workflow."""

    def test_upload_render_status_workflow(self, valid_gltf_file):
        """Test complete workflow: upload → render → status polling."""
        # Step 1: Upload
        upload_response = client.post(
            "/api/upload",
            files={"file": ("workflow_test.gltf", valid_gltf_file, "model/gltf+json")},
        )
        assert upload_response.status_code == 200
        job_id = upload_response.json()["jobId"]

        # Step 2: Submit render
        render_response = client.post(
            "/api/render",
            json={"jobId": job_id, "preset": "studio"},
        )
        assert render_response.status_code == 200
        assert render_response.json()["status"] == "queued"

        # Step 3: Poll status (limited to avoid long test)
        max_polls = 5
        for i in range(max_polls):
            status_response = client.get(f"/api/status/{job_id}")
            assert status_response.status_code == 200

            status = status_response.json()["status"]
            if status in ["rendering_complete", "failed"]:
                break

            time.sleep(0.5)

        # Final status should be one of terminal states or still processing
        final_status = status_response.json()["status"]
        assert final_status in ["queued", "processing", "rendering_complete", "failed"]

    def test_render_with_mock_provider(self, uploaded_job):
        """Test render using MockAIDPProvider (default)."""
        response = client.post(
            "/api/render",
            json={"jobId": uploaded_job, "preset": "dramatic"},
        )

        assert response.status_code == 200
        data = response.json()

        # MockAIDPProvider returns "aidp" as provider name
        assert data["provider"] == "aidp"
        # Job ID should be in aidp_ format
        assert data["providerJobId"].startswith("aidp_")
