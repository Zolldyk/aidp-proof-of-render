#!/usr/bin/env python3
"""
Manual test script for visual verification of all scene presets.

This script renders the test asset (Suzanne) with all three presets
and outputs comparison images for manual visual inspection.

Usage:
    python backend/scripts/test_all_presets.py

Visual Verification Checklist:
    [ ] Studio preset shows neutral lighting with even illumination
    [ ] Studio preset has light gray/white background
    [ ] Studio preset shows three-point lighting effect (no harsh shadows)

    [ ] Sunset preset shows warm orange/golden tones
    [ ] Sunset preset has directional lighting from low angle
    [ ] Sunset preset demonstrates warm color temperature

    [ ] Dramatic preset shows high contrast lighting
    [ ] Dramatic preset has dark background
    [ ] Dramatic preset shows strong shadows from spotlight
    [ ] Dramatic preset has cinematic low-angle camera view

    [ ] All three renders are clearly visually distinct
    [ ] All renders are 1024x1024 PNG files
    [ ] No renders are blank or corrupted
"""

import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from render_engine.preset_loader import list_available_presets
from render_engine.blender_renderer import execute_preset_render


def test_all_presets() -> List[Dict[str, Any]]:
    """
    Render test asset with all available presets.

    Returns:
        List of render results for each preset
    """
    # Get test asset path
    asset_path = backend_dir / "render_engine" / "test_assets" / "suzanne.gltf"

    if not asset_path.exists():
        print(f"❌ Error: Test asset not found at {asset_path}")
        print("Run 'python backend/scripts/generate_test_gltf.py' first to create test asset")
        sys.exit(1)

    # Get list of available presets
    presets = list_available_presets()
    print(f"Found {len(presets)} presets: {', '.join(presets)}\n")

    # Create output directory
    output_dir = Path("/tmp/preset_test_renders")
    output_dir.mkdir(exist_ok=True)
    print(f"Output directory: {output_dir}\n")

    # Render each preset
    results = []
    for preset_name in presets:
        output_path = output_dir / f"test_render_{preset_name}.png"

        print(f"🎨 Rendering with preset: {preset_name}")
        print(f"   Output: {output_path}")

        start_time = time.time()
        result = execute_preset_render(
            asset_path=str(asset_path),
            preset_name=preset_name,
            output_path=str(output_path)
        )

        if result["success"]:
            print(f"   ✅ Render completed in {result['duration']:.2f}s")
            print(f"   Memory used: {result['memory_used']:.2f} MB")
        else:
            print(f"   ❌ Render failed: {result.get('error')}")

        print()
        results.append(result)

    return results


def print_summary(results: List[Dict[str, Any]]) -> None:
    """Print summary table of render results."""
    print("=" * 80)
    print("RENDER SUMMARY")
    print("=" * 80)
    print()

    # Table header
    print(f"{'Preset':<15} {'Status':<10} {'Duration':<12} {'Memory (MB)':<12} {'Output Size':<12}")
    print("-" * 80)

    # Table rows
    for result in results:
        preset = result.get("preset", "unknown")
        status = "✅ Success" if result["success"] else "❌ Failed"
        duration = f"{result['duration']:.2f}s" if result["success"] else "N/A"
        memory = f"{result['memory_used']:.2f}" if result["success"] else "N/A"

        # Get file size if output exists
        output_path = Path(result["output_path"])
        if output_path.exists():
            file_size_kb = output_path.stat().st_size / 1024
            output_size = f"{file_size_kb:.1f} KB"
        else:
            output_size = "N/A"

        print(f"{preset:<15} {status:<10} {duration:<12} {memory:<12} {output_size:<12}")

    print()
    print("=" * 80)
    print()

    # Print output locations
    print("📂 Output Files:")
    for result in results:
        output_path = Path(result["output_path"])
        if output_path.exists():
            print(f"   {result.get('preset', 'unknown')}: {output_path}")

    print()
    print("🔍 Manual Verification:")
    print("   Open the output files side-by-side to verify distinct visual styles")
    print("   See script header for visual verification checklist")
    print()


def main():
    """Main entry point."""
    print("=" * 80)
    print("PRESET RENDERING TEST - VISUAL VERIFICATION")
    print("=" * 80)
    print()

    try:
        results = test_all_presets()
        print_summary(results)

        # Check if any renders failed
        failed = [r for r in results if not r["success"]]
        if failed:
            print(f"⚠️  Warning: {len(failed)} preset(s) failed to render")
            for result in failed:
                print(f"   - {result.get('preset', 'unknown')}: {result.get('error')}")
            print()
            print("Note: Blender must be installed and accessible for renders to succeed")
            sys.exit(1)
        else:
            print("✅ All presets rendered successfully!")
            sys.exit(0)

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
