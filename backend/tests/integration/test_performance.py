"""
Performance Benchmark Tests

Measures end-to-end render time and verifies it meets <90 second requirement.
"""

import logging
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.provider_factory import reset_provider
from app.services.rate_limiter import upload_rate_limiter

client = TestClient(app)
logger = logging.getLogger(__name__)

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


@pytest.mark.slow
@pytest.mark.integration
class TestRenderPerformance:
    """Performance benchmark tests for render pipeline."""

    def test_render_performance_under_90_seconds(self, cube_gltf):
        """
        Test that render completes within 90 seconds.

        AC: 5 - Performance test measures end-to-end time from /api/render call
        to "rendering_complete" status - must be <90 seconds for local rendering.
        """
        # Upload test asset
        upload_response = client.post(
            "/api/upload",
            files={"file": ("cube.gltf", cube_gltf, "model/gltf+json")},
        )
        assert upload_response.status_code == 200
        job_id = upload_response.json()["jobId"]

        # Start timing from render submission
        start_time = time.time()

        # Submit render job
        render_response = client.post(
            "/api/render",
            json={"jobId": job_id, "preset": "studio"},
        )
        assert render_response.status_code == 200

        # Poll until complete
        max_wait = 90
        poll_interval = 1
        final_status = None

        while time.time() - start_time < max_wait:
            status_response = client.get(f"/api/status/{job_id}")
            assert status_response.status_code == 200

            status_data = status_response.json()
            final_status = status_data["status"]

            if final_status in ["rendering_complete", "complete"]:
                break
            elif final_status == "failed":
                pytest.fail(f"Render failed: {status_data.get('errorMessage')}")

            time.sleep(poll_interval)

        total_time = time.time() - start_time

        # Log actual render time for baseline metrics
        logger.info(f"Render completed in {total_time:.2f} seconds")

        # Assert performance requirement
        assert total_time < 90, f"Render took {total_time:.2f}s, exceeds 90s limit"
        assert final_status in ["rendering_complete", "complete"], (
            f"Render did not complete. Final status: {final_status}"
        )

    def test_render_time_breakdown(self, cube_gltf):
        """Measure individual phase timings for performance analysis."""
        timings = {}

        # Phase 1: Upload
        t0 = time.time()
        upload_response = client.post(
            "/api/upload",
            files={"file": ("cube.gltf", cube_gltf, "model/gltf+json")},
        )
        timings["upload"] = time.time() - t0
        job_id = upload_response.json()["jobId"]

        # Phase 2: Render submission
        t0 = time.time()
        render_response = client.post(
            "/api/render",
            json={"jobId": job_id, "preset": "studio"},
        )
        timings["submit"] = time.time() - t0

        # Phase 3: Render execution (polling)
        t0 = time.time()
        for _ in range(90):
            status_response = client.get(f"/api/status/{job_id}")
            if status_response.json()["status"] in ["rendering_complete", "complete"]:
                break
            time.sleep(1)
        timings["render"] = time.time() - t0

        # Phase 4: Download
        t0 = time.time()
        download_response = client.get(f"/api/download/{job_id}")
        timings["download"] = time.time() - t0

        # Log timing breakdown
        logger.info(f"Performance breakdown: {timings}")
        logger.info(f"Total time: {sum(timings.values()):.2f}s")

        # Individual phase assertions
        assert timings["upload"] < 5, "Upload should complete in <5s"
        assert timings["submit"] < 2, "Render submission should complete in <2s"
        assert timings["download"] < 2, "Download should complete in <2s"
