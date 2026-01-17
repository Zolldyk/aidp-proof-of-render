"""
Full Pipeline Integration Tests

Tests the complete render pipeline from upload to download,
verifying output file exists and is valid.
"""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.provider_factory import reset_provider
from app.services.rate_limiter import upload_rate_limiter

client = TestClient(app)

# Test assets directory
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


@pytest.mark.integration
class TestFullRenderPipeline:
    """Tests for complete render pipeline: upload → render → poll → download."""

    def test_full_render_pipeline(self, cube_gltf):
        """
        Test complete pipeline: upload → render → poll → download → verify.

        AC: 2, 3, 4 - Integration test with local Blender, verifies output.
        """
        # Step 1: Upload test asset
        upload_response = client.post(
            "/api/upload",
            files={"file": ("cube.gltf", cube_gltf, "model/gltf+json")},
        )
        assert upload_response.status_code == 200
        job_id = upload_response.json()["jobId"]

        # Step 2: Submit render job with studio preset
        render_response = client.post(
            "/api/render",
            json={"jobId": job_id, "preset": "studio"},
        )
        assert render_response.status_code == 200
        assert render_response.json()["status"] == "queued"

        # Step 3: Poll until complete (max 90 seconds)
        max_wait_time = 90
        poll_interval = 2
        start_time = time.time()
        final_status = None

        while time.time() - start_time < max_wait_time:
            status_response = client.get(f"/api/status/{job_id}")
            assert status_response.status_code == 200

            status_data = status_response.json()
            final_status = status_data["status"]

            if final_status in ["rendering_complete", "complete"]:
                break
            elif final_status == "failed":
                pytest.fail(f"Render failed: {status_data.get('errorMessage', 'Unknown error')}")

            time.sleep(poll_interval)

        assert final_status in ["rendering_complete", "complete"], (
            f"Render did not complete within {max_wait_time}s. Final status: {final_status}"
        )

        # Step 4: Download rendered PNG
        download_response = client.get(f"/api/download/{job_id}")
        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "image/png"

        # Step 5: Verify output file exists
        output_path = Path(f"/tmp/outputs/{job_id}/render.png")
        assert output_path.exists(), "Output file should exist"

        # Step 6: Verify PNG format and dimensions
        with Image.open(output_path) as img:
            assert img.format == "PNG", "Output should be PNG format"
            assert img.size == (1024, 1024), f"Expected 1024x1024, got {img.size}"

        # Step 7: Verify file size >100KB (not blank/corrupted)
        file_size = output_path.stat().st_size
        assert file_size > 100 * 1024, f"File size {file_size} bytes is too small (expected >100KB)"

    def test_pipeline_with_sunset_preset(self, cube_gltf):
        """Test pipeline with sunset preset."""
        # Upload
        upload_response = client.post(
            "/api/upload",
            files={"file": ("cube.gltf", cube_gltf, "model/gltf+json")},
        )
        job_id = upload_response.json()["jobId"]

        # Render with sunset preset
        render_response = client.post(
            "/api/render",
            json={"jobId": job_id, "preset": "sunset"},
        )
        assert render_response.status_code == 200

        # Poll until complete
        for _ in range(45):
            status_response = client.get(f"/api/status/{job_id}")
            if status_response.json()["status"] in ["rendering_complete", "complete"]:
                break
            time.sleep(2)

        # Download
        download_response = client.get(f"/api/download/{job_id}")
        assert download_response.status_code == 200

    def test_pipeline_with_dramatic_preset(self, cube_gltf):
        """Test pipeline with dramatic preset."""
        # Upload
        upload_response = client.post(
            "/api/upload",
            files={"file": ("cube.gltf", cube_gltf, "model/gltf+json")},
        )
        job_id = upload_response.json()["jobId"]

        # Render with dramatic preset
        render_response = client.post(
            "/api/render",
            json={"jobId": job_id, "preset": "dramatic"},
        )
        assert render_response.status_code == 200

        # Poll until complete
        for _ in range(45):
            status_response = client.get(f"/api/status/{job_id}")
            if status_response.json()["status"] in ["rendering_complete", "complete"]:
                break
            time.sleep(2)

        # Download
        download_response = client.get(f"/api/download/{job_id}")
        assert download_response.status_code == 200
