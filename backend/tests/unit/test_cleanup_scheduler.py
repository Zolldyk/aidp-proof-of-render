"""
Unit Tests for Cleanup Scheduler Service

Tests the cleanup logic for removing old job files.
"""

import os
import shutil
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.cleanup_scheduler import (
    CLEANUP_DIRECTORIES,
    cleanup_old_files,
    get_scheduler_status,
    start_cleanup_scheduler,
    stop_cleanup_scheduler,
)


@pytest.fixture
def temp_cleanup_dirs():
    """Create temporary directories for testing cleanup."""
    temp_base = tempfile.mkdtemp()

    # Create temp directories matching production structure
    uploads_dir = Path(temp_base) / "uploads"
    outputs_dir = Path(temp_base) / "outputs"
    jobs_dir = Path(temp_base) / "jobs"

    uploads_dir.mkdir()
    outputs_dir.mkdir()
    jobs_dir.mkdir()

    yield {
        "base": temp_base,
        "uploads": uploads_dir,
        "outputs": outputs_dir,
        "jobs": jobs_dir,
    }

    # Cleanup
    shutil.rmtree(temp_base, ignore_errors=True)


class TestCleanupOldFiles:
    """Tests for cleanup_old_files function."""

    @pytest.mark.asyncio
    async def test_cleanup_removes_old_folders(self, temp_cleanup_dirs):
        """Test that folders older than TTL are removed."""
        # Create an "old" job folder
        old_job_dir = temp_cleanup_dirs["uploads"] / "old-job-id"
        old_job_dir.mkdir()
        (old_job_dir / "asset.gltf").write_text("{}")

        # Set modification time to 25 hours ago
        old_time = time.time() - (25 * 3600)
        os.utime(old_job_dir, (old_time, old_time))

        # Create a "new" job folder
        new_job_dir = temp_cleanup_dirs["uploads"] / "new-job-id"
        new_job_dir.mkdir()
        (new_job_dir / "asset.gltf").write_text("{}")

        # Patch the cleanup directories
        with patch(
            "app.services.cleanup_scheduler.CLEANUP_DIRECTORIES",
            [str(temp_cleanup_dirs["uploads"])],
        ):
            result = await cleanup_old_files()

        # Old folder should be deleted
        assert not old_job_dir.exists(), "Old folder should be deleted"
        # New folder should remain
        assert new_job_dir.exists(), "New folder should remain"
        # Check summary
        assert result["folders_deleted"] == 1

    @pytest.mark.asyncio
    async def test_cleanup_handles_nonexistent_directories(self):
        """Test cleanup handles missing directories gracefully."""
        with patch(
            "app.services.cleanup_scheduler.CLEANUP_DIRECTORIES",
            ["/nonexistent/path/uploads"],
        ):
            result = await cleanup_old_files()

        assert result["errors"] == 0
        assert result["folders_deleted"] == 0

    @pytest.mark.asyncio
    async def test_cleanup_skips_files_not_directories(self, temp_cleanup_dirs):
        """Test cleanup only processes directories, not files."""
        # Create a file directly in the uploads dir (should be skipped)
        stray_file = temp_cleanup_dirs["uploads"] / "stray_file.txt"
        stray_file.write_text("test")

        # Set old modification time
        old_time = time.time() - (25 * 3600)
        os.utime(stray_file, (old_time, old_time))

        with patch(
            "app.services.cleanup_scheduler.CLEANUP_DIRECTORIES",
            [str(temp_cleanup_dirs["uploads"])],
        ):
            result = await cleanup_old_files()

        # File should still exist (we only delete directories)
        assert stray_file.exists()
        assert result["folders_deleted"] == 0

    @pytest.mark.asyncio
    async def test_cleanup_respects_ttl_setting(self, temp_cleanup_dirs):
        """Test cleanup uses FILE_TTL_HOURS setting."""
        # Create a folder that's 12 hours old
        job_dir = temp_cleanup_dirs["uploads"] / "twelve-hour-job"
        job_dir.mkdir()

        twelve_hours_ago = time.time() - (12 * 3600)
        os.utime(job_dir, (twelve_hours_ago, twelve_hours_ago))

        # With default 24 hour TTL, this should NOT be deleted
        with patch(
            "app.services.cleanup_scheduler.CLEANUP_DIRECTORIES",
            [str(temp_cleanup_dirs["uploads"])],
        ):
            result = await cleanup_old_files()

        assert job_dir.exists(), "12-hour-old folder should not be deleted with 24h TTL"
        assert result["folders_deleted"] == 0


class TestSchedulerLifecycle:
    """Tests for scheduler start/stop functions."""

    def test_get_scheduler_status_before_start(self):
        """Test scheduler status before starting."""
        stop_cleanup_scheduler()  # Ensure stopped
        status = get_scheduler_status()

        assert status["running"] is False

    @pytest.mark.asyncio
    async def test_start_scheduler(self):
        """Test starting the scheduler."""
        # Start
        start_cleanup_scheduler()
        status = get_scheduler_status()

        assert status["running"] is True
        assert status["job_scheduled"] is True
        assert status["next_run"] is not None

    @pytest.mark.skip(reason="Scheduler stop requires same event loop - tested in integration")
    @pytest.mark.asyncio
    async def test_stop_scheduler(self):
        """Test stopping the scheduler."""
        # Note: This test is skipped because stopping the scheduler requires
        # the same event loop it was started on. The scheduler lifecycle is
        # tested through FastAPI integration tests instead.
        pass

    @pytest.mark.asyncio
    async def test_start_scheduler_idempotent(self):
        """Test that starting scheduler multiple times is safe."""
        # Start twice - should not raise
        start_cleanup_scheduler()
        start_cleanup_scheduler()

        status = get_scheduler_status()
        assert status["running"] is True


class TestCleanupIntegration:
    """Integration tests for cleanup with real temp directories."""

    @pytest.mark.asyncio
    async def test_cleanup_all_directories(self, temp_cleanup_dirs):
        """Test cleanup scans all three directories."""
        # Create old folders in each directory
        for dir_name in ["uploads", "outputs", "jobs"]:
            old_job = temp_cleanup_dirs[dir_name] / f"old-{dir_name}-job"
            old_job.mkdir()

            old_time = time.time() - (25 * 3600)
            os.utime(old_job, (old_time, old_time))

        with patch(
            "app.services.cleanup_scheduler.CLEANUP_DIRECTORIES",
            [
                str(temp_cleanup_dirs["uploads"]),
                str(temp_cleanup_dirs["outputs"]),
                str(temp_cleanup_dirs["jobs"]),
            ],
        ):
            result = await cleanup_old_files()

        assert result["directories_scanned"] == 3
        assert result["folders_deleted"] == 3
