"""
Pydantic models for scene preset configurations.

These models define the structure of preset data used for
Blender scene generation and API responses.
"""

from pydantic import BaseModel, Field
from typing import Optional


class Vector3(BaseModel):
    """3D vector with x, y, z coordinates."""

    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    z: float = Field(..., description="Z coordinate")


class LightConfig(BaseModel):
    """Lighting configuration for a single light source."""

    type: str = Field(..., description="Light type: POINT, SUN, SPOT, or AREA")
    position: Optional[Vector3] = Field(
        None, description="Light position (not used for SUN lights)"
    )
    rotation: Optional[Vector3] = Field(
        None, description="Light rotation in degrees (for SUN and SPOT lights)"
    )
    energy: float = Field(..., description="Light energy/intensity")
    color: str = Field(..., description="Light color as hex string (e.g., #ffffff)")
    size: Optional[float] = Field(
        None, description="Light size for SPOT lights (beam width)"
    )


class ScenePreset(BaseModel):
    """
    Complete scene preset configuration.

    Defines camera, lighting, environment, and render settings
    for a specific visual style (e.g., Studio, Sunset, Dramatic).
    """

    name: str = Field(
        ...,
        description="Unique preset identifier (e.g., 'studio', 'sunset', 'dramatic')",
    )
    displayName: str = Field(..., description="Human-readable name for UI display")
    description: str = Field(
        ..., description="Brief explanation of preset visual style"
    )
    thumbnailUrl: Optional[str] = Field(
        None, description="URL to preview thumbnail image"
    )

    cameraPosition: Vector3 = Field(..., description="Camera position in 3D space")
    cameraRotation: Vector3 = Field(
        ..., description="Camera rotation in Euler angles (degrees)"
    )

    backgroundColor: str = Field(
        ..., description="World background color as hex string"
    )

    lights: list[LightConfig] = Field(..., description="Array of light configurations")

    samples: int = Field(
        default=128, description="Cycles render samples (quality vs speed)"
    )
    colorTemperature: Optional[int] = Field(
        None, description="Color temperature in Kelvin for reference"
    )
    estimatedRenderTime: Optional[str] = Field(
        None, description="Human-readable render time estimate"
    )
    recommendedFor: Optional[str] = Field(
        None, description="Suggested use cases for this preset"
    )
    shadowsEnabled: Optional[bool] = Field(
        None, description="Whether shadows are enabled (Cycles default)"
    )


class PresetListResponse(BaseModel):
    """Response model for GET /api/presets endpoint."""

    presets: list[ScenePreset] = Field(
        ..., description="List of available scene presets"
    )
