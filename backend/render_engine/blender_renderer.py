"""
Blender headless rendering orchestration module.

Handles Blender subprocess execution, monitoring, and validation.
"""

import logging
import subprocess
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

import psutil
from PIL import Image

from app.config import settings
from .scene_generator import generate_preset_scene

# Configure logging
logger = logging.getLogger(__name__)


def _validate_blender_binary() -> bool:
    """
    Check if Blender binary is available and executable.

    Returns:
        bool: True if Blender is accessible, False otherwise
    """
    try:
        result = subprocess.run(
            [settings.BLENDER_BINARY, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        logger.info(f"Blender binary validated: {result.stdout.strip().split()[0:2]}")
        return True
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as e:
        logger.error(f"Blender binary validation failed: {e}")
        return False


def _verify_output(output_path: str) -> bool:
    """
    Verify rendered output file is valid PNG with correct dimensions.

    Args:
        output_path: Path to output PNG file

    Returns:
        bool: True if output is valid, False otherwise

    Raises:
        Exception: If verification fails with details
    """
    output_file = Path(output_path)

    # Check file exists
    if not output_file.exists():
        logger.error(f"Output file does not exist: {output_path}")
        raise Exception("Output file not found")

    # Check file size > 0
    if output_file.stat().st_size == 0:
        logger.error(f"Output file is empty: {output_path}")
        raise Exception("Output file is empty")

    try:
        # Validate PNG structure with Pillow
        img = Image.open(output_path)

        # Verify dimensions (1024x1024)
        if img.size != (1024, 1024):
            logger.error(
                f"Output dimensions incorrect: {img.size}, expected (1024, 1024)"
            )
            raise Exception(f"Invalid dimensions: {img.size}")

        # Verify format is PNG
        if img.format != "PNG":
            logger.error(f"Output format incorrect: {img.format}, expected PNG")
            raise Exception(f"Invalid format: {img.format}")

        # Ensure image is not blank (check pixel variance)
        extrema = img.getextrema()
        if extrema == (0, 0) or extrema == (255, 255):
            logger.warning("Output image may be blank (no pixel variance)")

        logger.info(f"Output verified: 1024x1024 PNG at {output_path}")
        return True

    except Exception as e:
        logger.error(f"Output verification failed: {e}")
        raise


def _monitor_render_process(process: subprocess.Popen) -> None:
    """
    Track render process execution (placeholder for future enhancements).

    Args:
        process: Subprocess handle for Blender render
    """
    # Future: Could poll Blender progress if API available
    pass


def execute_render(scene_script: str, output_path: str) -> Dict[str, Any]:
    """
    Execute Blender headless render with given scene script.

    Args:
        scene_script: Complete Blender Python script content
        output_path: Path where rendered PNG should be saved

    Returns:
        dict: Render result with keys:
            - success (bool): Whether render completed successfully
            - output_path (str): Path to output file
            - duration (float): Render time in seconds
            - memory_used (float): Memory increase in MB
            - error (str | None): Error message if failed
    """
    # Validate output directory exists
    output_dir = Path(output_path).parent
    if not output_dir.exists():
        error_msg = f"Output directory does not exist: {output_dir}"
        logger.error(error_msg)
        return {
            "success": False,
            "output_path": output_path,
            "duration": 0,
            "memory_used": 0,
            "error": error_msg,
        }

    # Track memory before render
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024  # MB

    # Create temporary script file
    script_path = Path("/tmp") / f"render_script_{uuid.uuid4()}.py"

    try:
        # Write scene script to temporary file
        script_path.write_text(scene_script)
        logger.info(f"Created temporary render script: {script_path}")

        # Construct Blender command
        command = [
            settings.BLENDER_BINARY,
            "--background",
            "--python",
            str(script_path),
            "--",
            "--output",
            output_path,
        ]

        # Record start time
        start_time = time.time()

        # Execute Blender subprocess
        logger.info(f"Starting Blender render: {output_path}")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=settings.RENDER_TIMEOUT,
            check=True,
        )

        # Calculate render duration
        end_time = time.time()
        duration = end_time - start_time

        # Track memory after render
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_used = mem_after - mem_before

        logger.info(f"Render completed in {duration:.2f} seconds")
        logger.info(f"Render memory usage: {mem_used:.2f} MB")

        # Log warning if memory usage high
        if mem_used > 1800:
            logger.warning(
                f"High memory usage detected: {mem_used:.2f} MB (approaching 2GB limit)"
            )

        # Verify output
        try:
            _verify_output(output_path)
        except Exception as e:
            return {
                "success": False,
                "output_path": output_path,
                "duration": duration,
                "memory_used": mem_used,
                "error": f"Output verification failed: {str(e)}",
            }

        return {
            "success": True,
            "output_path": output_path,
            "duration": duration,
            "memory_used": mem_used,
            "error": None,
        }

    except subprocess.TimeoutExpired:
        error_msg = f"Render timeout after {settings.RENDER_TIMEOUT} seconds"
        logger.error(error_msg)
        mem_after = process.memory_info().rss / 1024 / 1024
        return {
            "success": False,
            "output_path": output_path,
            "duration": settings.RENDER_TIMEOUT,
            "memory_used": mem_after - mem_before,
            "error": error_msg,
        }

    except subprocess.CalledProcessError as e:
        error_msg = f"Blender process failed: {e.stderr}"
        logger.error(error_msg)

        # Parse Blender stderr for common errors
        stderr_lower = e.stderr.lower() if e.stderr else ""
        if "no module named 'bpy'" in stderr_lower:
            error_msg = "Blender installation incomplete (bpy module not found)"
        elif "cuda error" in stderr_lower:
            error_msg = "GPU compute unavailable (CUDA error) - falling back to CPU"
        elif "out of memory" in stderr_lower:
            error_msg = "Insufficient RAM for render"

        mem_after = process.memory_info().rss / 1024 / 1024
        return {
            "success": False,
            "output_path": output_path,
            "duration": 0,
            "memory_used": mem_after - mem_before,
            "error": error_msg,
        }

    except FileNotFoundError:
        error_msg = f"Blender binary not found at {settings.BLENDER_BINARY}"
        logger.error(error_msg)
        return {
            "success": False,
            "output_path": output_path,
            "duration": 0,
            "memory_used": 0,
            "error": error_msg,
        }

    except OSError as e:
        error_msg = f"System error during render: {str(e)}"
        logger.error(error_msg)
        mem_after = process.memory_info().rss / 1024 / 1024
        return {
            "success": False,
            "output_path": output_path,
            "duration": 0,
            "memory_used": mem_after - mem_before,
            "error": error_msg,
        }

    finally:
        # Always cleanup temporary script file
        if script_path.exists():
            script_path.unlink(missing_ok=True)
            logger.debug(f"Cleaned up temporary script: {script_path}")


def execute_preset_render(
    asset_path: str, preset_name: str, output_path: str
) -> Dict[str, Any]:
    """
    Execute Blender headless render using a named scene preset.

    This function generates a Blender scene script from a preset configuration
    and executes the render. Presets define camera position, lighting setup,
    background color, and render settings.

    Args:
        asset_path: Path to .gltf asset file to import and render
        preset_name: Name of preset to use (e.g., "studio", "sunset", "dramatic")
        output_path: Path where rendered PNG should be saved

    Returns:
        dict: Render result with keys:
            - success (bool): Whether render completed successfully
            - output_path (str): Path to output file
            - duration (float): Render time in seconds
            - memory_used (float): Memory increase in MB
            - error (str | None): Error message if failed
            - preset (str): Name of preset used

    Raises:
        ValueError: If preset_name is invalid
        FileNotFoundError: If asset_path or preset file not found
    """
    logger.info(f"Rendering with preset: {preset_name}")

    # Validate asset path exists
    if not Path(asset_path).exists():
        error_msg = f"Asset file not found: {asset_path}"
        logger.error(error_msg)
        return {
            "success": False,
            "output_path": output_path,
            "duration": 0,
            "memory_used": 0,
            "error": error_msg,
            "preset": preset_name,
        }

    try:
        # Generate scene script from preset
        script = generate_preset_scene(asset_path, preset_name, output_path)
        logger.debug(f"Generated scene script from preset: {preset_name}")

        # Execute render using existing execute_render function
        result = execute_render(script, output_path)

        # Add preset information to result
        result["preset"] = preset_name

        if result["success"]:
            logger.info(
                f"Preset render completed: {preset_name} in {result['duration']:.2f}s"
            )
        else:
            logger.error(f"Preset render failed: {preset_name} - {result.get('error')}")

        return result

    except ValueError as e:
        # Preset loading error (invalid preset name)
        error_msg = str(e)
        logger.error(f"Preset loading failed: {error_msg}")
        return {
            "success": False,
            "output_path": output_path,
            "duration": 0,
            "memory_used": 0,
            "error": error_msg,
            "preset": preset_name,
        }

    except FileNotFoundError as e:
        # Template or preset file not found
        error_msg = f"Template/preset file error: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "output_path": output_path,
            "duration": 0,
            "memory_used": 0,
            "error": error_msg,
            "preset": preset_name,
        }

    except Exception as e:
        # Unexpected error during scene generation
        error_msg = f"Scene generation error: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "output_path": output_path,
            "duration": 0,
            "memory_used": 0,
            "error": error_msg,
            "preset": preset_name,
        }
