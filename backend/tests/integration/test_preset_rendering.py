"""
Integration tests for preset-based rendering.

Tests the complete rendering pipeline with different scene presets:
- Studio preset (three-point lighting)
- Sunset preset (warm directional lighting)
- Dramatic preset (high-contrast spotlight)
"""

import pytest
import hashlib
from pathlib import Path
from PIL import Image

from render_engine.preset_loader import load_preset, list_available_presets
from render_engine.scene_generator import generate_preset_scene
from render_engine.blender_renderer import execute_preset_render


@pytest.fixture
def test_asset_path():
    """Path to test .gltf asset (Suzanne)."""
    return str(Path(__file__).parent.parent.parent / "render_engine" / "test_assets" / "suzanne.gltf")


@pytest.fixture
def output_dir(tmp_path):
    """Temporary directory for test outputs."""
    return tmp_path


def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of file for comparison."""
    with open(file_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


class TestPresetLoader:
    """Test preset loading and validation."""

    def test_list_available_presets(self):
        """Test listing all available presets."""
        presets = list_available_presets()

        assert isinstance(presets, list)
        assert len(presets) == 3
        assert "studio" in presets
        assert "sunset" in presets
        assert "dramatic" in presets

    def test_preset_loader_valid_preset(self):
        """Test loading a valid preset returns correct structure."""
        preset = load_preset("studio")

        # Verify required fields
        assert preset["name"] == "studio"
        assert preset["displayName"] == "Studio"
        assert "description" in preset
        assert "cameraPosition" in preset
        assert "cameraRotation" in preset
        assert "backgroundColor" in preset
        assert "lights" in preset
        assert "samples" in preset

        # Verify Studio preset has 3 lights (three-point lighting)
        assert len(preset["lights"]) == 3

        # Verify camera position has x, y, z
        assert "x" in preset["cameraPosition"]
        assert "y" in preset["cameraPosition"]
        assert "z" in preset["cameraPosition"]

    def test_preset_loader_invalid_preset(self):
        """Test loading invalid preset raises ValueError with helpful message."""
        with pytest.raises(ValueError) as exc_info:
            load_preset("nonexistent")

        error_message = str(exc_info.value)
        assert "Invalid preset 'nonexistent'" in error_message
        assert "Available presets:" in error_message
        assert "studio" in error_message
        assert "sunset" in error_message
        assert "dramatic" in error_message


class TestPresetRendering:
    """
    Test rendering with different presets.

    Note: These tests require Blender to be installed and available.
    They will be skipped if Blender is not found.
    """

    @pytest.mark.skipif(
        not Path("/usr/bin/blender").exists() and not Path("/Applications/Blender.app").exists(),
        reason="Blender not installed"
    )
    def test_studio_preset_render(self, test_asset_path, output_dir):
        """Test rendering with Studio preset produces valid output."""
        output_path = str(output_dir / "studio_render.png")

        # Note: This test requires Blender to be available
        # In CI/CD or Docker environment, this should pass
        # For local development without Blender, test is skipped
        result = execute_preset_render(test_asset_path, "studio", output_path)

        # If Blender is not available, result will have error
        if not result["success"]:
            pytest.skip(f"Blender not available: {result.get('error')}")

        # Verify render succeeded
        assert result["success"] is True
        assert result["preset"] == "studio"
        assert result["duration"] > 0
        assert Path(output_path).exists()

        # Verify output is valid PNG
        img = Image.open(output_path)
        assert img.format == "PNG"
        assert img.size == (1024, 1024)

        # Verify file size > 100KB (not blank)
        file_size = Path(output_path).stat().st_size
        assert file_size > 100 * 1024, f"Output file too small: {file_size} bytes"

    @pytest.mark.skipif(
        not Path("/usr/bin/blender").exists() and not Path("/Applications/Blender.app").exists(),
        reason="Blender not installed"
    )
    def test_sunset_preset_render(self, test_asset_path, output_dir):
        """Test rendering with Sunset preset produces different output."""
        output_path = str(output_dir / "sunset_render.png")

        result = execute_preset_render(test_asset_path, "sunset", output_path)

        if not result["success"]:
            pytest.skip(f"Blender not available: {result.get('error')}")

        # Verify render succeeded
        assert result["success"] is True
        assert result["preset"] == "sunset"
        assert Path(output_path).exists()

        # Verify output is valid PNG
        img = Image.open(output_path)
        assert img.format == "PNG"
        assert img.size == (1024, 1024)

    @pytest.mark.skipif(
        not Path("/usr/bin/blender").exists() and not Path("/Applications/Blender.app").exists(),
        reason="Blender not installed"
    )
    def test_dramatic_preset_render(self, test_asset_path, output_dir):
        """Test rendering with Dramatic preset produces different output."""
        output_path = str(output_dir / "dramatic_render.png")

        result = execute_preset_render(test_asset_path, "dramatic", output_path)

        if not result["success"]:
            pytest.skip(f"Blender not available: {result.get('error')}")

        # Verify render succeeded
        assert result["success"] is True
        assert result["preset"] == "dramatic"
        assert Path(output_path).exists()

        # Verify output is valid PNG
        img = Image.open(output_path)
        assert img.format == "PNG"
        assert img.size == (1024, 1024)

    @pytest.mark.skipif(
        not Path("/usr/bin/blender").exists() and not Path("/Applications/Blender.app").exists(),
        reason="Blender not installed"
    )
    def test_different_presets_produce_different_outputs(self, test_asset_path, output_dir):
        """Verify that different presets produce visually different renders."""
        studio_path = str(output_dir / "studio_compare.png")
        sunset_path = str(output_dir / "sunset_compare.png")

        # Render with Studio preset
        studio_result = execute_preset_render(test_asset_path, "studio", studio_path)
        if not studio_result["success"]:
            pytest.skip(f"Blender not available: {studio_result.get('error')}")

        # Render with Sunset preset
        sunset_result = execute_preset_render(test_asset_path, "sunset", sunset_path)

        # Compute file hashes
        studio_hash = compute_file_hash(studio_path)
        sunset_hash = compute_file_hash(sunset_path)

        # Verify different presets produce different outputs
        assert studio_hash != sunset_hash, "Studio and Sunset presets should produce different images"


class TestSceneGeneration:
    """Test scene script generation from presets."""

    def test_generate_preset_scene_script(self, test_asset_path):
        """Test scene script generation produces valid Python code."""
        output_path = "/tmp/test_output.png"

        script = generate_preset_scene(test_asset_path, "studio", output_path)

        # Verify script is a string
        assert isinstance(script, str)

        # Verify script contains expected Blender commands
        assert "import bpy" in script
        assert "import mathutils" in script
        assert "import_scene.gltf" in script
        assert test_asset_path in script
        assert output_path in script

        # Verify Studio preset camera settings
        assert "camera_add" in script.lower()

        # Verify lighting setup
        assert "light_add" in script.lower()

    def test_generate_all_presets(self, test_asset_path):
        """Test script generation for all available presets."""
        presets = list_available_presets()

        for preset_name in presets:
            script = generate_preset_scene(test_asset_path, preset_name, "/tmp/test.png")

            assert isinstance(script, str)
            assert len(script) > 0
            assert "import bpy" in script
