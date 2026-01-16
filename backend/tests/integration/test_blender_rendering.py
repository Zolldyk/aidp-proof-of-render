"""
Integration tests for Blender headless rendering.

Tests the complete render pipeline including:
- Blender binary availability
- Scene script generation
- Headless render execution
- Output validation
- Error handling
- Performance metrics
"""

import subprocess
import time
from pathlib import Path

import pytest

from render_engine import blender_renderer, scene_generator


class TestBlenderBinaryAvailability:
    """Test Blender installation and binary access"""

    def test_blender_binary_availability(self):
        """Verify Blender binary is installed and accessible"""
        result = blender_renderer._validate_blender_binary()
        assert result is True, "Blender binary should be accessible"


class TestHeadlessRenderExecution:
    """Test complete render pipeline execution"""

    def test_headless_render_execution(self, tmp_path):
        """Execute full render pipeline and verify output"""
        # Generate output path in temp directory
        output_path = tmp_path / "test_output.png"

        # Generate test scene script
        script = scene_generator.generate_test_scene(str(output_path))
        assert script is not None
        assert "bpy.ops.render.render" in script
        assert str(output_path) in script

        # Execute render
        result = blender_renderer.execute_render(script, str(output_path))

        # Verify result structure
        assert "success" in result
        assert "output_path" in result
        assert "duration" in result
        assert "memory_used" in result
        assert "error" in result

        # Verify render succeeded
        assert result["success"] is True, f"Render should succeed, but got error: {result.get('error')}"

        # Verify output file exists
        assert output_path.exists(), "Output PNG file should exist"

        # Verify render duration
        assert result["duration"] > 0, "Render duration should be greater than 0"
        assert result["duration"] < 300, f"Render should complete within timeout ({result['duration']}s)"

        # Verify memory usage
        assert result["memory_used"] >= 0, "Memory usage should be non-negative"

        # Verify error is None on success
        assert result["error"] is None, "Error should be None when render succeeds"

    def test_render_performance_baseline(self, tmp_path):
        """Measure and log baseline render performance"""
        output_path = tmp_path / "baseline_render.png"
        script = scene_generator.generate_test_scene(str(output_path))

        # Execute render and measure
        start = time.time()
        result = blender_renderer.execute_render(script, str(output_path))
        total_duration = time.time() - start

        # Log performance metrics
        print(f"\n=== Blender Render Baseline Performance ===")
        print(f"Render Duration: {result['duration']:.2f} seconds")
        print(f"Total Duration: {total_duration:.2f} seconds")
        print(f"Memory Used: {result['memory_used']:.2f} MB")
        print(f"Resolution: 1024x1024")
        print(f"Samples: 128")
        print(f"==========================================")

        assert result["success"] is True
        assert result["memory_used"] < 2000, "Memory usage should be under 2GB Railway limit"


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_error_handling_invalid_script(self, tmp_path):
        """Verify error handling for invalid Blender script"""
        output_path = tmp_path / "error_test.png"

        # Create invalid Blender script with syntax error
        invalid_script = """
import bpy

# This will cause a syntax error
this is not valid python code!!!

bpy.ops.render.render(write_still=True)
"""

        # Execute render with invalid script
        result = blender_renderer.execute_render(invalid_script, str(output_path))

        # Verify render failed
        assert result["success"] is False, "Render should fail with invalid script"
        assert result["error"] is not None, "Error message should be present"
        assert len(result["error"]) > 0, "Error message should not be empty"

    def test_error_handling_missing_output_path(self, tmp_path):
        """Verify error handling when output path is invalid"""
        # Use a path in a non-existent directory
        invalid_output = "/nonexistent/directory/output.png"

        script = scene_generator.generate_test_scene(invalid_output)
        result = blender_renderer.execute_render(script, invalid_output)

        # Should fail due to invalid output path
        assert result["success"] is False
        assert result["error"] is not None

    def test_render_timeout(self, tmp_path):
        """Verify timeout handling for long-running renders"""
        output_path = tmp_path / "timeout_test.png"

        # Create a script with an infinite loop to trigger timeout
        timeout_script = """
import bpy
import time

# This will cause a timeout
while True:
    time.sleep(1)
"""

        # Temporarily modify timeout for this test (original is 300s)
        from app.config import settings
        original_timeout = settings.RENDER_TIMEOUT
        settings.RENDER_TIMEOUT = 5  # 5 second timeout for test

        try:
            result = blender_renderer.execute_render(timeout_script, str(output_path))

            # Verify timeout error
            assert result["success"] is False, "Render should fail on timeout"
            assert result["error"] is not None
            assert "timeout" in result["error"].lower() or "Timeout" in result["error"]

        finally:
            # Restore original timeout
            settings.RENDER_TIMEOUT = original_timeout


class TestOutputVerification:
    """Test output file validation"""

    def test_output_dimensions_validation(self, tmp_path):
        """Verify output file has correct dimensions"""
        output_path = tmp_path / "dimension_test.png"
        script = scene_generator.generate_test_scene(str(output_path))

        result = blender_renderer.execute_render(script, str(output_path))

        assert result["success"] is True

        # Verify using PIL
        from PIL import Image
        img = Image.open(output_path)
        assert img.size == (1024, 1024), f"Expected 1024x1024, got {img.size}"
        assert img.format == 'PNG', f"Expected PNG format, got {img.format}"

    def test_output_not_blank(self, tmp_path):
        """Verify rendered output is not a blank image"""
        output_path = tmp_path / "content_test.png"
        script = scene_generator.generate_test_scene(str(output_path))

        result = blender_renderer.execute_render(script, str(output_path))
        assert result["success"] is True

        # Check pixel variance
        from PIL import Image
        img = Image.open(output_path)
        extrema = img.convert('L').getextrema()  # Convert to grayscale first

        # Should have some variance (not all black or all white)
        assert extrema[0] != extrema[1] or extrema != (0, 0), "Image should not be blank"
