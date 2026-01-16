"""
Unit tests for preset loader module.

Tests preset loading, validation, and error handling without
requiring Blender or full rendering pipeline.
"""

import pytest
from pathlib import Path

from render_engine.preset_loader import load_preset, list_available_presets


class TestPresetLoading:
    """Test basic preset loading functionality."""

    def test_load_studio_preset(self):
        """Test loading Studio preset returns correct structure."""
        preset = load_preset("studio")

        # Verify basic fields
        assert preset["name"] == "studio"
        assert preset["displayName"] == "Studio"
        assert isinstance(preset["description"], str)
        assert len(preset["description"]) > 0

        # Verify Studio preset has 3 lights (three-point lighting)
        assert "lights" in preset
        assert isinstance(preset["lights"], list)
        assert len(preset["lights"]) == 3

        # Verify all lights have required fields
        for light in preset["lights"]:
            assert "type" in light
            assert "energy" in light
            assert "color" in light

        # Verify camera position exists with x, y, z
        assert "cameraPosition" in preset
        assert "x" in preset["cameraPosition"]
        assert "y" in preset["cameraPosition"]
        assert "z" in preset["cameraPosition"]

        # Verify camera rotation
        assert "cameraRotation" in preset
        assert "x" in preset["cameraRotation"]
        assert "y" in preset["cameraRotation"]
        assert "z" in preset["cameraRotation"]

        # Verify render settings
        assert "samples" in preset
        assert preset["samples"] == 128
        assert "backgroundColor" in preset

    def test_load_sunset_preset(self):
        """Test loading Sunset preset returns correct structure."""
        preset = load_preset("sunset")

        assert preset["name"] == "sunset"
        assert preset["displayName"] == "Sunset"

        # Sunset should have 1 SUN light
        assert len(preset["lights"]) == 1
        assert preset["lights"][0]["type"] == "SUN"

        # Verify warm color temperature
        assert preset["colorTemperature"] == 3500

    def test_load_dramatic_preset(self):
        """Test loading Dramatic preset returns correct structure."""
        preset = load_preset("dramatic")

        assert preset["name"] == "dramatic"
        assert preset["displayName"] == "Dramatic"

        # Dramatic should have 1 SPOT light
        assert len(preset["lights"]) == 1
        assert preset["lights"][0]["type"] == "SPOT"

        # Verify shadows enabled
        assert preset.get("shadowsEnabled") is True

    def test_load_all_presets(self):
        """Test that all presets can be loaded successfully."""
        presets = ["studio", "sunset", "dramatic"]

        for preset_name in presets:
            preset = load_preset(preset_name)

            # Verify basic structure
            assert isinstance(preset, dict)
            assert preset["name"] == preset_name
            assert "displayName" in preset
            assert "description" in preset
            assert "cameraPosition" in preset
            assert "cameraRotation" in preset
            assert "lights" in preset
            assert "backgroundColor" in preset


class TestPresetValidation:
    """Test preset validation and error handling."""

    def test_invalid_preset_raises_error(self):
        """Test that loading invalid preset raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            load_preset("invalid")

        error_message = str(exc_info.value)
        assert "Invalid preset 'invalid'" in error_message
        assert "Available presets:" in error_message

    def test_invalid_preset_error_lists_available_presets(self):
        """Test that error message lists all available presets."""
        with pytest.raises(ValueError) as exc_info:
            load_preset("nonexistent")

        error_message = str(exc_info.value)
        assert "studio" in error_message
        assert "sunset" in error_message
        assert "dramatic" in error_message

    def test_empty_preset_name_raises_error(self):
        """Test that empty preset name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            load_preset("")

        assert "preset_name must be a non-empty string" in str(exc_info.value)

    def test_none_preset_name_raises_error(self):
        """Test that None preset name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            load_preset(None)

        assert "preset_name must be a non-empty string" in str(exc_info.value)


class TestPresetStructure:
    """Test preset structure validation."""

    def test_preset_structure_validation(self):
        """Test that all presets have required fields."""
        required_fields = [
            "name",
            "displayName",
            "description",
            "cameraPosition",
            "cameraRotation",
            "backgroundColor",
            "lights",
            "samples"
        ]

        # Load each preset and validate structure
        for preset_name in ["studio", "sunset", "dramatic"]:
            preset = load_preset(preset_name)

            # Check all required fields exist
            for field in required_fields:
                assert field in preset, f"Preset '{preset_name}' missing required field: {field}"

            # Validate camera position structure
            assert "x" in preset["cameraPosition"]
            assert "y" in preset["cameraPosition"]
            assert "z" in preset["cameraPosition"]

            # Validate camera rotation structure
            assert "x" in preset["cameraRotation"]
            assert "y" in preset["cameraRotation"]
            assert "z" in preset["cameraRotation"]

            # Validate lights is a list with at least one light
            assert isinstance(preset["lights"], list)
            assert len(preset["lights"]) > 0

            # Validate each light has required fields
            for light in preset["lights"]:
                assert "type" in light
                assert "energy" in light
                assert "color" in light

    def test_camera_position_values_are_numeric(self):
        """Test that camera position values are numeric."""
        preset = load_preset("studio")

        assert isinstance(preset["cameraPosition"]["x"], (int, float))
        assert isinstance(preset["cameraPosition"]["y"], (int, float))
        assert isinstance(preset["cameraPosition"]["z"], (int, float))

    def test_light_energy_values_are_numeric(self):
        """Test that light energy values are numeric."""
        preset = load_preset("studio")

        for light in preset["lights"]:
            assert isinstance(light["energy"], (int, float))
            assert light["energy"] > 0

    def test_background_color_is_hex_string(self):
        """Test that background color is a valid hex string."""
        preset = load_preset("studio")

        bg_color = preset["backgroundColor"]
        assert isinstance(bg_color, str)
        assert bg_color.startswith("#")
        assert len(bg_color) == 7  # #RRGGBB format


class TestListPresets:
    """Test list_available_presets function."""

    def test_list_available_presets(self):
        """Test listing all available presets."""
        presets = list_available_presets()

        # Verify it's a list
        assert isinstance(presets, list)

        # Verify expected presets are present
        assert "studio" in presets
        assert "sunset" in presets
        assert "dramatic" in presets

        # Verify count
        assert len(presets) == 3

    def test_list_presets_returns_strings(self):
        """Test that list_available_presets returns list of strings."""
        presets = list_available_presets()

        for preset_name in presets:
            assert isinstance(preset_name, str)
            assert len(preset_name) > 0
