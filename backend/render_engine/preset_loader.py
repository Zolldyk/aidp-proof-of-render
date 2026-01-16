"""
Preset loader for scene rendering configurations.

This module loads scene presets from presets.yaml and provides
functions to retrieve and validate preset configurations.
"""

import yaml
from pathlib import Path
from typing import Any


def list_available_presets() -> list[str]:
    """
    Returns list of available preset names.

    Returns:
        List of preset names (e.g., ["studio", "sunset", "dramatic"])
    """
    preset_file = Path(__file__).parent / "presets.yaml"

    if not preset_file.exists():
        raise FileNotFoundError(
            f"presets.yaml not found. Ensure file exists at {preset_file}"
        )

    try:
        with open(preset_file) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML format in presets.yaml: {e}")

    if not data or "presets" not in data:
        raise ValueError("presets.yaml must contain a 'presets' key")

    return [preset["name"] for preset in data["presets"]]


def load_preset(preset_name: str) -> dict[str, Any]:
    """
    Load a preset configuration by name.

    Args:
        preset_name: Name of the preset to load (e.g., "studio", "sunset", "dramatic")

    Returns:
        Dictionary containing preset configuration with camera, lighting, and render settings

    Raises:
        ValueError: If preset_name is invalid or not found
        FileNotFoundError: If presets.yaml doesn't exist
    """
    # Input validation
    if not preset_name or not isinstance(preset_name, str):
        raise ValueError("preset_name must be a non-empty string")

    preset_file = Path(__file__).parent / "presets.yaml"

    if not preset_file.exists():
        raise FileNotFoundError(
            f"presets.yaml not found. Ensure file exists at {preset_file}"
        )

    # Load and parse YAML
    try:
        with open(preset_file) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML format in presets.yaml: {e}")

    if not data or "presets" not in data:
        raise ValueError("presets.yaml must contain a 'presets' key")

    # Search for preset by name
    for preset in data["presets"]:
        if preset.get("name") == preset_name:
            return preset

    # Preset not found - raise error with available options
    available = list_available_presets()
    raise ValueError(
        f"Invalid preset '{preset_name}'. " f"Available presets: {', '.join(available)}"
    )
