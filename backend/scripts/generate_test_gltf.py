#!/usr/bin/env python3
"""
Generate a simple test .gltf file for preset rendering tests.

This creates a minimal valid .gltf file with a simple cube geometry.
For actual Suzanne model, use generate_suzanne.py with Blender in Docker.
"""

from pygltflib import GLTF2, Scene, Node, Mesh, Primitive, Accessor, BufferView, Buffer
from pygltflib import Material, PbrMetallicRoughness, Attributes
import struct
import numpy as np
from pathlib import Path

def create_cube_mesh():
    """Create vertices and indices for a simple cube."""
    # Cube vertices (8 corners)
    vertices = np.array([
        # Front face
        [-1, -1,  1],
        [ 1, -1,  1],
        [ 1,  1,  1],
        [-1,  1,  1],
        # Back face
        [-1, -1, -1],
        [ 1, -1, -1],
        [ 1,  1, -1],
        [-1,  1, -1],
    ], dtype=np.float32)

    # Cube indices (12 triangles, 2 per face)
    indices = np.array([
        # Front
        0, 1, 2,  2, 3, 0,
        # Right
        1, 5, 6,  6, 2, 1,
        # Back
        5, 4, 7,  7, 6, 5,
        # Left
        4, 0, 3,  3, 7, 4,
        # Top
        3, 2, 6,  6, 7, 3,
        # Bottom
        4, 5, 1,  1, 0, 4,
    ], dtype=np.uint16)

    return vertices, indices


def create_gltf_file(output_path: Path):
    """Create a minimal valid .gltf file with cube geometry."""
    vertices, indices = create_cube_mesh()

    # Convert to bytes
    vertices_binary = vertices.tobytes()
    indices_binary = indices.tobytes()

    # Create binary buffer
    binary_blob = vertices_binary + indices_binary

    # Create GLTF structure
    gltf = GLTF2()

    # Buffer (contains all binary data)
    buffer = Buffer()
    buffer.byteLength = len(binary_blob)
    gltf.buffers.append(buffer)

    # BufferView for vertices
    vertices_buffer_view = BufferView()
    vertices_buffer_view.buffer = 0
    vertices_buffer_view.byteOffset = 0
    vertices_buffer_view.byteLength = len(vertices_binary)
    vertices_buffer_view.target = 34962  # ARRAY_BUFFER
    gltf.bufferViews.append(vertices_buffer_view)

    # BufferView for indices
    indices_buffer_view = BufferView()
    indices_buffer_view.buffer = 0
    indices_buffer_view.byteOffset = len(vertices_binary)
    indices_buffer_view.byteLength = len(indices_binary)
    indices_buffer_view.target = 34963  # ELEMENT_ARRAY_BUFFER
    gltf.bufferViews.append(indices_buffer_view)

    # Accessor for vertices
    vertices_accessor = Accessor()
    vertices_accessor.bufferView = 0
    vertices_accessor.byteOffset = 0
    vertices_accessor.componentType = 5126  # FLOAT
    vertices_accessor.count = len(vertices)
    vertices_accessor.type = "VEC3"
    vertices_accessor.min = vertices.min(axis=0).tolist()
    vertices_accessor.max = vertices.max(axis=0).tolist()
    gltf.accessors.append(vertices_accessor)

    # Accessor for indices
    indices_accessor = Accessor()
    indices_accessor.bufferView = 1
    indices_accessor.byteOffset = 0
    indices_accessor.componentType = 5123  # UNSIGNED_SHORT
    indices_accessor.count = len(indices)
    indices_accessor.type = "SCALAR"
    gltf.accessors.append(indices_accessor)

    # Material
    material = Material()
    material.pbrMetallicRoughness = PbrMetallicRoughness()
    material.pbrMetallicRoughness.baseColorFactor = [0.8, 0.3, 0.1, 1.0]  # Orange
    material.pbrMetallicRoughness.metallicFactor = 0.2
    material.pbrMetallicRoughness.roughnessFactor = 0.5
    gltf.materials.append(material)

    # Mesh primitive
    primitive = Primitive()
    primitive.attributes.POSITION = 0
    primitive.indices = 1
    primitive.material = 0
    primitive.mode = 4  # TRIANGLES

    # Mesh
    mesh = Mesh()
    mesh.primitives.append(primitive)
    gltf.meshes.append(mesh)

    # Node
    node = Node()
    node.mesh = 0
    gltf.nodes.append(node)

    # Scene
    scene = Scene()
    scene.nodes.append(0)
    gltf.scenes.append(scene)
    gltf.scene = 0

    # Save to file
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save binary data to .bin file
    bin_path = output_path.with_suffix('.bin')
    with open(bin_path, 'wb') as f:
        f.write(binary_blob)

    # Set buffer URI to point to .bin file
    gltf.buffers[0].uri = bin_path.name

    # Save .gltf JSON file
    gltf.save(str(output_path))

    print(f"Created test .gltf file: {output_path}")
    print(f"Created binary file: {bin_path}")
    print(f"Total file size: {output_path.stat().st_size + bin_path.stat().st_size} bytes")


if __name__ == '__main__':
    script_dir = Path(__file__).parent.parent
    output_path = script_dir / 'render_engine' / 'test_assets' / 'suzanne.gltf'

    create_gltf_file(output_path)
    print("Test asset created successfully!")
