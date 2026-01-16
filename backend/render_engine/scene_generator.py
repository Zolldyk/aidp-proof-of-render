"""
Blender scene script generation module.

Generates Blender Python scripts for various scene configurations.
"""

import logging
from pathlib import Path
from typing import Any
from jinja2 import Environment, FileSystemLoader
from .preset_loader import load_preset

logger = logging.getLogger(__name__)


def generate_test_scene(output_path: str) -> str:
    """
    Generate Blender Python script for basic test scene.

    Creates a scene with:
    - Default cube at origin
    - Camera at (7, -7, 5) looking at origin
    - Area light at (5, 5, 5)
    - Cycles render engine with GPU compute
    - 1024x1024 resolution, 128 samples, PNG output

    Args:
        output_path: Path where rendered PNG should be saved

    Returns:
        str: Complete Blender Python script content
    """
    script = f"""import bpy
import mathutils

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Create cube at origin
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
cube = bpy.context.object
cube.name = 'TestCube'

# Create camera at (7, -7, 5) looking at origin
bpy.ops.object.camera_add(location=(7, -7, 5))
camera = bpy.context.object
camera.name = 'TestCamera'

# Point camera at origin using track_to constraint method
# Calculate rotation angles to look at origin
direction = mathutils.Vector((0, 0, 0)) - mathutils.Vector((7, -7, 5))
rot_quat = direction.to_track_quat('-Z', 'Y')
camera.rotation_euler = rot_quat.to_euler()

# Set active camera
bpy.context.scene.camera = camera

# Create area light at (5, 5, 5)
bpy.ops.object.light_add(type='AREA', location=(5, 5, 5))
light_obj = bpy.context.object
light_obj.name = 'TestLight'
light_data = light_obj.data
light_data.energy = 1000

# Configure render settings
scene = bpy.context.scene

# Set render engine to Cycles
scene.render.engine = 'CYCLES'

# Enable GPU compute (will fallback to CPU if unavailable)
scene.cycles.device = 'GPU'

# Set resolution
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100

# Set samples
scene.cycles.samples = 128

# Set output format
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.color_depth = '8'

# Set output path
scene.render.filepath = '{output_path}'

# Execute render
print("Starting Blender render...")
bpy.ops.render.render(write_still=True)
print(f"Render complete: {{scene.render.filepath}}")
"""

    logger.debug(f"Generated test scene script for output: {output_path}")
    return script


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """
    Convert hex color string to RGB tuple (0.0-1.0 range).

    Args:
        hex_color: Hex color string (e.g., "#ff7e3e" or "ff7e3e")

    Returns:
        Tuple of (r, g, b) floats in range 0.0-1.0
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b)


def _rgb_to_rgba(rgb: tuple[float, float, float]) -> tuple[float, float, float, float]:
    """
    Convert RGB tuple to RGBA tuple by adding alpha channel.

    Args:
        rgb: RGB tuple (r, g, b) with values 0.0-1.0

    Returns:
        RGBA tuple (r, g, b, a) with alpha=1.0
    """
    return (rgb[0], rgb[1], rgb[2], 1.0)


def generate_preset_scene(asset_path: str, preset_name: str, output_path: str) -> str:
    """
    Generate Blender Python script for preset-based scene rendering.

    Uses Jinja2 template to generate a Blender script that applies
    camera, lighting, and environment settings from a named preset.

    Args:
        asset_path: Path to .gltf asset file to import
        preset_name: Name of preset to load (e.g., "studio", "sunset", "dramatic")
        output_path: Path where rendered PNG should be saved

    Returns:
        str: Complete Blender Python script content

    Raises:
        ValueError: If preset_name is invalid
        FileNotFoundError: If preset file or template not found
    """
    # Load preset configuration
    preset = load_preset(preset_name)

    # Load Jinja2 template
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))

    # Register custom filters
    env.filters["hex_to_rgb"] = _hex_to_rgb
    env.filters["rgb_to_rgba"] = _rgb_to_rgba

    # Get template
    template = env.get_template("preset_scene.py.jinja2")

    # Render template
    script = template.render(
        asset_path=asset_path, output_path=output_path, preset=preset
    )

    logger.info(
        f"Generated preset scene script: preset={preset_name}, output={output_path}"
    )
    return script
