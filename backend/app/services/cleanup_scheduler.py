"""
Cleanup Scheduler Service

Manages scheduled cleanup of temporary files older than 24 hours.
Uses APScheduler for hourly cleanup job execution.
"""

import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Directories to clean up
CLEANUP_DIRECTORIES = ["/tmp/uploads", "/tmp/outputs", "/tmp/jobs"]

# File TTL in hours (default: 24 hours)
FILE_TTL_HOURS = int(os.getenv("FILE_TTL_HOURS", "24"))

# Cleanup interval in hours (default: 1 hour)
CLEANUP_INTERVAL_HOURS = int(os.getenv("CLEANUP_INTERVAL_HOURS", "1"))


async def cleanup_old_files() -> dict:
    """
    Delete files older than 24 hours from temp directories.

    Scans /tmp/uploads/, /tmp/outputs/, /tmp/jobs/ and removes
    job folders whose modification time exceeds the TTL.

    Returns:
        dict: Summary of cleanup operation with counts
    """
    cutoff = datetime.now() - timedelta(hours=FILE_TTL_HOURS)
    cleanup_summary = {
        "directories_scanned": 0,
        "folders_deleted": 0,
        "errors": 0,
    }

    for directory in CLEANUP_DIRECTORIES:
        dir_path = Path(directory)

        if not dir_path.exists():
            logger.debug(f"Cleanup directory does not exist: {directory}")
            continue

        cleanup_summary["directories_scanned"] += 1

        try:
            for job_folder in dir_path.iterdir():
                if not job_folder.is_dir():
                    continue

                try:
                    # Check folder modification time
                    folder_mtime = datetime.fromtimestamp(job_folder.stat().st_mtime)

                    if folder_mtime < cutoff:
                        shutil.rmtree(job_folder)
                        cleanup_summary["folders_deleted"] += 1
                        logger.info(f"Cleaned up old job folder: {job_folder}")

                except (OSError, PermissionError) as e:
                    cleanup_summary["errors"] += 1
                    logger.error(f"Failed to clean up folder {job_folder}: {e}")

        except (OSError, PermissionError) as e:
            cleanup_summary["errors"] += 1
            logger.error(f"Failed to scan directory {directory}: {e}")

    logger.info(
        f"Cleanup completed: {cleanup_summary['folders_deleted']} folders deleted, "
        f"{cleanup_summary['errors']} errors"
    )

    return cleanup_summary


def start_cleanup_scheduler():
    """
    Start the cleanup scheduler with hourly interval.

    Adds the cleanup job to APScheduler and starts the scheduler.
    Safe to call multiple times - will not add duplicate jobs.
    """
    if scheduler.running:
        logger.debug("Scheduler already running")
        return

    # Add cleanup job if not already added
    job_id = "cleanup_old_files"
    existing_job = scheduler.get_job(job_id)

    if not existing_job:
        scheduler.add_job(
            cleanup_old_files,
            "interval",
            hours=CLEANUP_INTERVAL_HOURS,
            id=job_id,
            name="Cleanup old job files",
            replace_existing=True,
        )
        logger.info(
            f"Scheduled cleanup job: every {CLEANUP_INTERVAL_HOURS} hour(s), "
            f"TTL: {FILE_TTL_HOURS} hours"
        )

    scheduler.start()
    logger.info("Cleanup scheduler started")


def stop_cleanup_scheduler():
    """Stop the cleanup scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Cleanup scheduler stopped")


def get_scheduler_status() -> dict:
    """
    Get current scheduler status for health checks.

    Returns:
        dict: Scheduler status including running state and job info
    """
    job = scheduler.get_job("cleanup_old_files")
    return {
        "running": scheduler.running,
        "job_scheduled": job is not None,
        "next_run": str(job.next_run_time) if job else None,
        "interval_hours": CLEANUP_INTERVAL_HOURS,
        "ttl_hours": FILE_TTL_HOURS,
    }
