#!/usr/bin/env python3
"""
Standalone Blender render test script for manual verification.

This script tests the Blender headless rendering pipeline and opens
the output image for visual inspection.

Run with: python backend/scripts/test_render.py
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from render_engine import blender_renderer, scene_generator


def open_image(image_path: str):
    """
    Open image file using system default viewer.

    Args:
        image_path: Path to image file to open
    """
    system = platform.system()

    # Check if running in headless environment (Docker, CI, etc.)
    if system == "Linux" and not os.getenv("DISPLAY"):
        print("   ℹ Headless environment detected (no display available)")
        print(f"   Image saved to: {image_path}")
        print("   To view: Copy file from Docker container or mount volume")
        return

    try:
        if system == "Darwin":  # macOS
            subprocess.run(["open", image_path], check=True)
        elif system == "Linux":
            subprocess.run(["xdg-open", image_path], check=True)
        elif system == "Windows":
            subprocess.run(["start", image_path], shell=True, check=True)
        else:
            print(f"Unknown system: {system}. Please open {image_path} manually.")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Failed to open image: {e}")
        print(f"Please open manually: {image_path}")


def main():
    """Execute manual render test"""
    print("=" * 60)
    print("Blender Headless Rendering - Manual Test")
    print("=" * 60)

    # Define output path
    output_path = "/tmp/manual_test_render.png"
    print(f"\nOutput path: {output_path}")

    # Generate test scene
    print("\n1. Generating test scene script...")
    try:
        script = scene_generator.generate_test_scene(output_path)
        print("   ✓ Scene script generated")
        print(f"   - Scene includes: cube, camera, area light")
        print(f"   - Resolution: 1024x1024")
        print(f"   - Samples: 128")
    except Exception as e:
        print(f"   ✗ Failed to generate scene: {e}")
        return 1

    # Execute render
    print("\n2. Executing Blender render...")
    print("   (This may take 10-60 seconds depending on your hardware)")
    try:
        result = blender_renderer.execute_render(script, output_path)
    except Exception as e:
        print(f"   ✗ Render execution failed: {e}")
        return 1

    # Display results
    print("\n3. Render Results:")
    print(f"   - Success: {result['success']}")
    print(f"   - Duration: {result['duration']:.2f} seconds")
    print(f"   - Memory Used: {result['memory_used']:.2f} MB")

    if result['error']:
        print(f"   - Error: {result['error']}")

    if not result['success']:
        print("\n✗ Render failed!")
        return 1

    # Verify output exists
    output_file = Path(output_path)
    if not output_file.exists():
        print(f"\n✗ Output file not found: {output_path}")
        return 1

    print(f"   - Output file size: {output_file.stat().st_size / 1024:.2f} KB")

    # Validate with PIL
    print("\n4. Validating output...")
    try:
        from PIL import Image
        img = Image.open(output_path)
        print(f"   ✓ Valid PNG image")
        print(f"   - Dimensions: {img.size[0]}x{img.size[1]}")
        print(f"   - Format: {img.format}")
        print(f"   - Mode: {img.mode}")
    except Exception as e:
        print(f"   ✗ Validation failed: {e}")
        return 1

    # Open image for visual inspection
    print("\n5. Opening image for visual inspection...")
    open_image(output_path)

    print("\n" + "=" * 60)
    print("✓ Manual test completed successfully!")
    print("=" * 60)
    print("\nVisual Inspection Checklist:")
    print("  [ ] Image shows a rendered cube")
    print("  [ ] Cube has proper lighting and shadows")
    print("  [ ] Camera angle is correct (viewing from upper-right)")
    print("  [ ] Background is visible")
    print("  [ ] No rendering artifacts or corruption")
    print("\nIf all items are checked, the render pipeline is working correctly.")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
