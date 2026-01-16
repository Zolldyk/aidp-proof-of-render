"""
Scene presets API endpoints.

Provides endpoints for listing and retrieving scene preset configurations.
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Any

from render_engine.preset_loader import load_preset, list_available_presets
from app.models.scene_preset import (
    ScenePreset,
    PresetListResponse,
    Vector3,
    LightConfig,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _convert_preset_to_model(preset_dict: dict[str, Any]) -> ScenePreset:
    """
    Convert preset dictionary from YAML to Pydantic model.

    Args:
        preset_dict: Raw preset data from YAML file

    Returns:
        ScenePreset: Validated Pydantic model
    """
    # Convert camera position
    camera_pos = Vector3(**preset_dict["cameraPosition"])
    camera_rot = Vector3(**preset_dict["cameraRotation"])

    # Convert lights
    lights = []
    for light_data in preset_dict["lights"]:
        light = LightConfig(
            type=light_data["type"],
            position=(
                Vector3(**light_data["position"]) if "position" in light_data else None
            ),
            rotation=(
                Vector3(**light_data["rotation"]) if "rotation" in light_data else None
            ),
            energy=light_data["energy"],
            color=light_data["color"],
            size=light_data.get("size"),
        )
        lights.append(light)

    # Generate thumbnail URL (placeholder for now)
    thumbnail_url = f"/gallery/{preset_dict['name']}-preview.webp"

    # Create ScenePreset model
    return ScenePreset(
        name=preset_dict["name"],
        displayName=preset_dict["displayName"],
        description=preset_dict["description"],
        thumbnailUrl=thumbnail_url,
        cameraPosition=camera_pos,
        cameraRotation=camera_rot,
        backgroundColor=preset_dict["backgroundColor"],
        lights=lights,
        samples=preset_dict.get("samples", 128),
        colorTemperature=preset_dict.get("colorTemperature"),
        estimatedRenderTime=preset_dict.get("estimatedRenderTime"),
        recommendedFor=preset_dict.get("recommendedFor"),
        shadowsEnabled=preset_dict.get("shadowsEnabled"),
    )


@router.get("/presets", response_model=PresetListResponse, tags=["Metadata"])
async def get_presets() -> PresetListResponse:
    """
    Get list of available scene presets.

    Returns all configured scene presets with their camera, lighting,
    and environment settings. Used by frontend to populate preset
    selection UI.

    Returns:
        PresetListResponse: List of available presets

    Raises:
        HTTPException: 500 if preset loading fails
    """
    try:
        # Get list of available preset names
        preset_names = list_available_presets()
        logger.info(f"Loading {len(preset_names)} presets")

        # Load each preset and convert to Pydantic model
        presets = []
        for name in preset_names:
            preset_dict = load_preset(name)
            preset_model = _convert_preset_to_model(preset_dict)
            presets.append(preset_model)

        logger.info(f"Successfully loaded {len(presets)} presets")
        return PresetListResponse(presets=presets)

    except FileNotFoundError as e:
        logger.error(f"Preset file not found: {e}")
        raise HTTPException(
            status_code=500, detail="Preset configuration file not found"
        )

    except ValueError as e:
        logger.error(f"Preset loading error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Invalid preset configuration: {str(e)}"
        )

    except Exception as e:
        logger.error(f"Unexpected error loading presets: {e}")
        raise HTTPException(status_code=500, detail="Failed to load presets")
