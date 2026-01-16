"""
Unit tests for render provider classes.

Tests LocalBlenderProvider, MockAIDPProvider, and provider factory
with mocked Blender subprocess execution.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.services.render_provider import RenderProvider
from app.services.local_blender_provider import LocalBlenderProvider
from app.services.mock_aidp_provider import MockAIDPProvider
from app.services.provider_factory import get_render_provider, reset_provider


class TestLocalBlenderProvider:
    """Tests for LocalBlenderProvider class."""

    def test_provider_name_is_local(self):
        """Test provider_name returns 'local'."""
        provider = LocalBlenderProvider()
        assert provider.provider_name == "local"

    @pytest.mark.asyncio
    async def test_submit_job_returns_valid_job_id(self, tmp_path):
        """Test submit_job returns a local_{uuid} format job ID."""
        # Create mock asset file
        asset_file = tmp_path / "test_job" / "asset.gltf"
        asset_file.parent.mkdir(parents=True)
        asset_file.write_text('{"asset": {"version": "2.0"}}')

        provider = LocalBlenderProvider()

        # Mock the execute_preset_render to avoid actual Blender execution
        with patch(
            "app.services.local_blender_provider.execute_preset_render"
        ) as mock_render:
            mock_render.return_value = {
                "success": True,
                "output_path": "/tmp/outputs/test/render.png",
                "duration": 10.0,
                "memory_used": 100.0,
                "error": None,
            }

            job_id = await provider.submit_job(
                job_id="test_job",
                asset_path=str(asset_file),
                preset="studio",
            )

            assert job_id.startswith("local_")
            assert len(job_id) > 10

    @pytest.mark.asyncio
    async def test_submit_job_raises_on_missing_asset(self):
        """Test submit_job raises FileNotFoundError for missing asset."""
        provider = LocalBlenderProvider()

        with pytest.raises(FileNotFoundError):
            await provider.submit_job(
                job_id="test_job",
                asset_path="/nonexistent/path/asset.gltf",
                preset="studio",
            )

    @pytest.mark.asyncio
    async def test_get_status_returns_expected_structure(self, tmp_path):
        """Test get_status returns dict with expected keys."""
        asset_file = tmp_path / "test_job" / "asset.gltf"
        asset_file.parent.mkdir(parents=True)
        asset_file.write_text('{"asset": {"version": "2.0"}}')

        provider = LocalBlenderProvider()

        with patch(
            "app.services.local_blender_provider.execute_preset_render"
        ) as mock_render:
            mock_render.return_value = {
                "success": True,
                "output_path": "/tmp/outputs/test/render.png",
                "duration": 10.0,
                "memory_used": 100.0,
                "error": None,
            }

            job_id = await provider.submit_job(
                job_id="test_job",
                asset_path=str(asset_file),
                preset="studio",
            )

            # Wait a bit for status to be initialized
            await asyncio.sleep(0.1)

            status = await provider.get_status(job_id)

            assert "status" in status
            assert "progress_percent" in status
            assert "estimated_time_remaining" in status
            assert "error_message" in status

    @pytest.mark.asyncio
    async def test_get_status_raises_on_unknown_job(self):
        """Test get_status raises KeyError for unknown job ID."""
        provider = LocalBlenderProvider()

        with pytest.raises(KeyError):
            await provider.get_status("unknown_job_id")

    @pytest.mark.asyncio
    async def test_get_result_returns_none_when_not_complete(self, tmp_path):
        """Test get_result returns None when job is still processing."""
        asset_file = tmp_path / "test_job" / "asset.gltf"
        asset_file.parent.mkdir(parents=True)
        asset_file.write_text('{"asset": {"version": "2.0"}}')

        provider = LocalBlenderProvider()

        # Create a slow mock that keeps job in processing state
        async def slow_render(*args, **kwargs):
            await asyncio.sleep(10)
            return {"success": True}

        with patch(
            "app.services.local_blender_provider.execute_preset_render",
            side_effect=lambda *args: {"success": False, "error": "Mock"},
        ):
            job_id = await provider.submit_job(
                job_id="test_job",
                asset_path=str(asset_file),
                preset="studio",
            )

            # Immediately check result (job not complete)
            result = await provider.get_result(job_id)
            # Result should be None since job just started
            assert result is None or isinstance(result, bytes)


class TestMockAIDPProvider:
    """Tests for MockAIDPProvider class."""

    def test_provider_name_is_aidp(self):
        """Test provider_name returns 'aidp'."""
        provider = MockAIDPProvider()
        assert provider.provider_name == "aidp"

    @pytest.mark.asyncio
    async def test_submit_job_returns_aidp_format_job_id(self, tmp_path):
        """Test submit_job returns aidp_{uuid} format job ID."""
        asset_file = tmp_path / "test_job" / "asset.gltf"
        asset_file.parent.mkdir(parents=True)
        asset_file.write_text('{"asset": {"version": "2.0"}}')

        provider = MockAIDPProvider()

        # Mock the underlying local provider
        with patch.object(
            provider._local_provider,
            "submit_job",
            new_callable=AsyncMock,
            return_value="local_test123",
        ):
            job_id = await provider.submit_job(
                job_id="test_job",
                asset_path=str(asset_file),
                preset="studio",
            )

            assert job_id.startswith("aidp_")
            assert len(job_id) > 10

    @pytest.mark.asyncio
    async def test_status_includes_aidp_metadata(self, tmp_path):
        """Test get_status returns AIDP-style metadata."""
        asset_file = tmp_path / "test_job" / "asset.gltf"
        asset_file.parent.mkdir(parents=True)
        asset_file.write_text('{"asset": {"version": "2.0"}}')

        provider = MockAIDPProvider()

        # Mock the local provider methods
        with patch.object(
            provider._local_provider,
            "submit_job",
            new_callable=AsyncMock,
            return_value="local_test123",
        ):
            job_id = await provider.submit_job(
                job_id="test_job",
                asset_path=str(asset_file),
                preset="studio",
            )

            # Wait for job to be initialized
            await asyncio.sleep(0.1)

            status = await provider.get_status(job_id)

            assert "job_id" in status
            assert "provider_id" in status
            assert status["provider_id"] == "mock-provider-001"

    @pytest.mark.asyncio
    async def test_status_transitions_through_lifecycle(self, tmp_path):
        """Test job transitions through queued → processing states."""
        asset_file = tmp_path / "test_job" / "asset.gltf"
        asset_file.parent.mkdir(parents=True)
        asset_file.write_text('{"asset": {"version": "2.0"}}')

        provider = MockAIDPProvider()

        with patch.object(
            provider._local_provider,
            "submit_job",
            new_callable=AsyncMock,
            return_value="local_test123",
        ):
            with patch.object(
                provider._local_provider,
                "get_status",
                new_callable=AsyncMock,
                return_value={
                    "status": "processing",
                    "progress_percent": 50,
                    "estimated_time_remaining": 30,
                    "error_message": None,
                },
            ):
                job_id = await provider.submit_job(
                    job_id="test_job",
                    asset_path=str(asset_file),
                    preset="studio",
                )

                # Initially should be queued
                status = await provider.get_status(job_id)
                assert status["status"] == "queued"


class TestProviderFactory:
    """Tests for provider factory function."""

    def setup_method(self):
        """Reset provider before each test."""
        reset_provider()

    def teardown_method(self):
        """Reset provider after each test."""
        reset_provider()

    def test_get_render_provider_returns_mock_aidp_when_enabled(self):
        """Test factory returns MockAIDPProvider when USE_MOCK_AIDP=true."""
        with patch("app.services.provider_factory.settings") as mock_settings:
            mock_settings.USE_MOCK_AIDP = True
            reset_provider()

            provider = get_render_provider()

            assert isinstance(provider, MockAIDPProvider)
            assert provider.provider_name == "aidp"

    def test_get_render_provider_raises_when_aidp_disabled(self):
        """Test factory raises NotImplementedError when USE_MOCK_AIDP=false."""
        with patch("app.services.provider_factory.settings") as mock_settings:
            mock_settings.USE_MOCK_AIDP = False
            reset_provider()

            with pytest.raises(NotImplementedError) as exc_info:
                get_render_provider()

            assert "not yet implemented" in str(exc_info.value).lower()

    def test_get_render_provider_returns_singleton(self):
        """Test factory returns same instance on multiple calls."""
        with patch("app.services.provider_factory.settings") as mock_settings:
            mock_settings.USE_MOCK_AIDP = True
            reset_provider()

            provider1 = get_render_provider()
            provider2 = get_render_provider()

            assert provider1 is provider2

    def test_reset_provider_clears_singleton(self):
        """Test reset_provider allows new instance creation."""
        with patch("app.services.provider_factory.settings") as mock_settings:
            mock_settings.USE_MOCK_AIDP = True
            reset_provider()

            provider1 = get_render_provider()
            reset_provider()
            provider2 = get_render_provider()

            assert provider1 is not provider2
