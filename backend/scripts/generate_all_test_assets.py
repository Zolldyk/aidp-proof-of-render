#!/usr/bin/env python3
"""
Generate all test .gltf files for pipeline testing.

Creates: cube.gltf, sphere.gltf, cylinder.gltf, torus.gltf
Also copies suzanne.gltf from render_engine/test_assets/
"""

import math
import shutil
from pathlib import Path

import numpy as np
from pygltflib import (
    GLTF2,
    Accessor,
    Buffer,
    BufferView,
    Material,
    Mesh,
    Node,
    PbrMetallicRoughness,
    Primitive,
    Scene,
)


def create_cube_geometry():
    """Create vertices and indices for a simple cube."""
    vertices = np.array(
        [
            [-1, -1, 1],
            [1, -1, 1],
            [1, 1, 1],
            [-1, 1, 1],
            [-1, -1, -1],
            [1, -1, -1],
            [1, 1, -1],
            [-1, 1, -1],
        ],
        dtype=np.float32,
    )
    indices = np.array(
        [
            0, 1, 2, 2, 3, 0,  # Front
            1, 5, 6, 6, 2, 1,  # Right
            5, 4, 7, 7, 6, 5,  # Back
            4, 0, 3, 3, 7, 4,  # Left
            3, 2, 6, 6, 7, 3,  # Top
            4, 5, 1, 1, 0, 4,  # Bottom
        ],
        dtype=np.uint16,
    )
    return vertices, indices


def create_sphere_geometry(segments=16, rings=12):
    """Create vertices and indices for a UV sphere."""
    vertices = []
    indices = []

    for j in range(rings + 1):
        theta = j * math.pi / rings
        sin_theta = math.sin(theta)
        cos_theta = math.cos(theta)

        for i in range(segments + 1):
            phi = i * 2 * math.pi / segments
            sin_phi = math.sin(phi)
            cos_phi = math.cos(phi)

            x = cos_phi * sin_theta
            y = cos_theta
            z = sin_phi * sin_theta
            vertices.append([x, y, z])

    for j in range(rings):
        for i in range(segments):
            first = j * (segments + 1) + i
            second = first + segments + 1

            indices.extend([first, second, first + 1])
            indices.extend([second, second + 1, first + 1])

    return np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.uint16)


def create_cylinder_geometry(segments=16, height=2.0, radius=1.0):
    """Create vertices and indices for a cylinder."""
    vertices = []
    indices = []

    half_height = height / 2

    # Top center
    vertices.append([0, half_height, 0])
    top_center = 0

    # Top ring
    for i in range(segments):
        angle = i * 2 * math.pi / segments
        x = radius * math.cos(angle)
        z = radius * math.sin(angle)
        vertices.append([x, half_height, z])

    # Bottom center
    vertices.append([0, -half_height, 0])
    bottom_center = len(vertices) - 1

    # Bottom ring
    for i in range(segments):
        angle = i * 2 * math.pi / segments
        x = radius * math.cos(angle)
        z = radius * math.sin(angle)
        vertices.append([x, -half_height, z])

    # Top cap triangles
    for i in range(segments):
        next_i = (i + 1) % segments
        indices.extend([top_center, 1 + i, 1 + next_i])

    # Bottom cap triangles
    for i in range(segments):
        next_i = (i + 1) % segments
        indices.extend([bottom_center, bottom_center + 1 + next_i, bottom_center + 1 + i])

    # Side triangles
    for i in range(segments):
        next_i = (i + 1) % segments
        top1 = 1 + i
        top2 = 1 + next_i
        bot1 = bottom_center + 1 + i
        bot2 = bottom_center + 1 + next_i
        indices.extend([top1, bot1, top2])
        indices.extend([top2, bot1, bot2])

    return np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.uint16)


def create_torus_geometry(major_segments=24, minor_segments=12, major_radius=1.0, minor_radius=0.4):
    """Create vertices and indices for a torus."""
    vertices = []
    indices = []

    for i in range(major_segments):
        theta = i * 2 * math.pi / major_segments
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)

        for j in range(minor_segments):
            phi = j * 2 * math.pi / minor_segments
            cos_phi = math.cos(phi)
            sin_phi = math.sin(phi)

            x = (major_radius + minor_radius * cos_phi) * cos_theta
            y = minor_radius * sin_phi
            z = (major_radius + minor_radius * cos_phi) * sin_theta
            vertices.append([x, y, z])

    for i in range(major_segments):
        next_i = (i + 1) % major_segments
        for j in range(minor_segments):
            next_j = (j + 1) % minor_segments

            v0 = i * minor_segments + j
            v1 = i * minor_segments + next_j
            v2 = next_i * minor_segments + next_j
            v3 = next_i * minor_segments + j

            indices.extend([v0, v3, v1])
            indices.extend([v1, v3, v2])

    return np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.uint16)


def create_gltf_file(output_path: Path, vertices: np.ndarray, indices: np.ndarray, color: list):
    """Create a .gltf file with given geometry."""
    vertices_binary = vertices.tobytes()
    indices_binary = indices.tobytes()
    binary_blob = vertices_binary + indices_binary

    gltf = GLTF2()

    # Buffer
    buffer = Buffer()
    buffer.byteLength = len(binary_blob)
    gltf.buffers.append(buffer)

    # BufferViews
    vertices_bv = BufferView()
    vertices_bv.buffer = 0
    vertices_bv.byteOffset = 0
    vertices_bv.byteLength = len(vertices_binary)
    vertices_bv.target = 34962
    gltf.bufferViews.append(vertices_bv)

    indices_bv = BufferView()
    indices_bv.buffer = 0
    indices_bv.byteOffset = len(vertices_binary)
    indices_bv.byteLength = len(indices_binary)
    indices_bv.target = 34963
    gltf.bufferViews.append(indices_bv)

    # Accessors
    vertices_acc = Accessor()
    vertices_acc.bufferView = 0
    vertices_acc.byteOffset = 0
    vertices_acc.componentType = 5126
    vertices_acc.count = len(vertices)
    vertices_acc.type = "VEC3"
    vertices_acc.min = vertices.min(axis=0).tolist()
    vertices_acc.max = vertices.max(axis=0).tolist()
    gltf.accessors.append(vertices_acc)

    indices_acc = Accessor()
    indices_acc.bufferView = 1
    indices_acc.byteOffset = 0
    indices_acc.componentType = 5123
    indices_acc.count = len(indices)
    indices_acc.type = "SCALAR"
    gltf.accessors.append(indices_acc)

    # Material
    material = Material()
    material.pbrMetallicRoughness = PbrMetallicRoughness()
    material.pbrMetallicRoughness.baseColorFactor = color
    material.pbrMetallicRoughness.metallicFactor = 0.2
    material.pbrMetallicRoughness.roughnessFactor = 0.5
    gltf.materials.append(material)

    # Mesh
    primitive = Primitive()
    primitive.attributes.POSITION = 0
    primitive.indices = 1
    primitive.material = 0
    primitive.mode = 4

    mesh = Mesh()
    mesh.primitives.append(primitive)
    gltf.meshes.append(mesh)

    # Node & Scene
    node = Node()
    node.mesh = 0
    gltf.nodes.append(node)

    scene = Scene()
    scene.nodes.append(0)
    gltf.scenes.append(scene)
    gltf.scene = 0

    # Save files
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bin_path = output_path.with_suffix(".bin")

    with open(bin_path, "wb") as f:
        f.write(binary_blob)

    gltf.buffers[0].uri = bin_path.name
    gltf.save(str(output_path))

    total_size = output_path.stat().st_size + bin_path.stat().st_size
    print(f"Created {output_path.name}: {total_size} bytes")


def main():
    """Generate all test assets."""
    project_root = Path(__file__).parent.parent.parent
    test_assets_dir = project_root / "test-assets"
    test_assets_dir.mkdir(parents=True, exist_ok=True)

    # Colors for each asset (RGBA)
    colors = {
        "cube": [0.8, 0.2, 0.2, 1.0],      # Red
        "sphere": [0.2, 0.8, 0.2, 1.0],    # Green
        "cylinder": [0.2, 0.2, 0.8, 1.0],  # Blue
        "torus": [0.8, 0.8, 0.2, 1.0],     # Yellow
    }

    # Generate cube
    vertices, indices = create_cube_geometry()
    create_gltf_file(test_assets_dir / "cube.gltf", vertices, indices, colors["cube"])

    # Generate sphere
    vertices, indices = create_sphere_geometry()
    create_gltf_file(test_assets_dir / "sphere.gltf", vertices, indices, colors["sphere"])

    # Generate cylinder
    vertices, indices = create_cylinder_geometry()
    create_gltf_file(test_assets_dir / "cylinder.gltf", vertices, indices, colors["cylinder"])

    # Generate torus
    vertices, indices = create_torus_geometry()
    create_gltf_file(test_assets_dir / "torus.gltf", vertices, indices, colors["torus"])

    # Copy suzanne from render_engine/test_assets
    suzanne_src = project_root / "backend" / "render_engine" / "test_assets" / "suzanne.gltf"
    suzanne_bin_src = project_root / "backend" / "render_engine" / "test_assets" / "suzanne.bin"

    if suzanne_src.exists() and suzanne_bin_src.exists():
        shutil.copy(suzanne_src, test_assets_dir / "suzanne.gltf")
        shutil.copy(suzanne_bin_src, test_assets_dir / "suzanne.bin")
        print(f"Copied suzanne.gltf: {(test_assets_dir / 'suzanne.gltf').stat().st_size + (test_assets_dir / 'suzanne.bin').stat().st_size} bytes")
    else:
        print("Warning: suzanne.gltf not found in render_engine/test_assets/")

    print(f"\nAll test assets created in {test_assets_dir}")


if __name__ == "__main__":
    main()
