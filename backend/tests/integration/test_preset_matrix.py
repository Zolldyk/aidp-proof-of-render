"""
Multi-Asset Multi-Preset Test Matrix

Tests all 15 combinations of 5 test assets with 3 presets.
Marked as slow tests due to extended execution time.
"""

import shutil
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.provider_factory import reset_provider
from app.services.rate_limiter import upload_rate_limiter

client = TestClient(app)

TEST_ASSETS_DIR = Path(__file__).parent.parent.parent.parent / "test-assets"

TEST_ASSETS = ["cube.gltf", "sphere.gltf", "suzanne.gltf", "cylinder.gltf", "torus.gltf"]
PRESETS = ["studio", "sunset", "dramatic"]


@pytest.fixture(autouse=True)
def reset_state():
    """Reset provider singleton and rate limiter before each test."""
    reset_provider()
    upload_rate_limiter.requests.clear()
    yield
    reset_provider()
    upload_rate_limiter.requests.clear()


@pytest.fixture
def cleanup_outputs():
    """Clean up test outputs after each test."""
    yield
    # Cleanup is handled by the hourly cron job in production


def load_test_asset(asset_name: str) -> bytes:
    """Load a test asset file."""
    asset_path = TEST_ASSETS_DIR / asset_name
    if not asset_path.exists():
        pytest.skip(f"Test asset not found: {asset_path}")
    with open(asset_path, "rb") as f:
        return f.read()


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.parametrize("asset", TEST_ASSETS)
@pytest.mark.parametrize("preset", PRESETS)
def test_render_asset_with_preset(asset: str, preset: str):
    """
    Test render pipeline with asset and preset combination.

    AC: 7 - All five test assets successfully render with all three presets
    (15 total combinations).
    """
    # Load asset
    asset_data = load_test_asset(asset)

    # Upload
    upload_response = client.post(
        "/api/upload",
        files={"file": (asset, asset_data, "model/gltf+json")},
    )
    assert upload_response.status_code == 200, f"Upload failed for {asset}"
    job_id = upload_response.json()["jobId"]

    # Submit render
    render_response = client.post(
        "/api/render",
        json={"jobId": job_id, "preset": preset},
    )
    assert render_response.status_code == 200, f"Render submit failed for {asset}/{preset}"

    # Poll until complete (max 90 seconds per render)
    max_wait = 90
    final_status = None

    for _ in range(max_wait):
        status_response = client.get(f"/api/status/{job_id}")
        assert status_response.status_code == 200

        status_data = status_response.json()
        final_status = status_data["status"]

        if final_status in ["rendering_complete", "complete"]:
            break
        elif final_status == "failed":
            pytest.fail(
                f"Render failed for {asset}/{preset}: {status_data.get('errorMessage')}"
            )

        time.sleep(1)

    assert final_status in ["rendering_complete", "complete"], (
        f"Render did not complete for {asset}/{preset}. Final status: {final_status}"
    )

    # Verify output exists and is valid
    output_path = Path(f"/tmp/outputs/{job_id}/render.png")
    assert output_path.exists(), f"Output not found for {asset}/{preset}"

    # Verify PNG is valid
    with Image.open(output_path) as img:
        assert img.format == "PNG", f"Invalid format for {asset}/{preset}"
        assert img.size == (1024, 1024), f"Wrong dimensions for {asset}/{preset}: {img.size}"

    # Verify file size (should be substantial for real render)
    file_size = output_path.stat().st_size
    assert file_size > 50 * 1024, f"File too small for {asset}/{preset}: {file_size} bytes"


@pytest.mark.slow
@pytest.mark.integration
class TestPresetMatrixSummary:
    """Summary tests for the preset matrix."""

    def test_all_assets_exist(self):
        """Verify all required test assets exist."""
        for asset in TEST_ASSETS:
            asset_path = TEST_ASSETS_DIR / asset
            assert asset_path.exists(), f"Missing test asset: {asset}"

            # Also check for companion .bin file
            bin_path = asset_path.with_suffix(".bin")
            assert bin_path.exists(), f"Missing binary file: {bin_path.name}"

    def test_asset_sizes_under_1mb(self):
        """Verify all test assets are under 1MB as specified."""
        max_size = 1 * 1024 * 1024  # 1MB

        for asset in TEST_ASSETS:
            gltf_path = TEST_ASSETS_DIR / asset
            bin_path = gltf_path.with_suffix(".bin")

            total_size = gltf_path.stat().st_size + bin_path.stat().st_size
            assert total_size < max_size, (
                f"Asset {asset} is {total_size} bytes, exceeds 1MB limit"
            )
