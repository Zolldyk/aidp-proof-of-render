#!/usr/bin/env blender --python
"""
Generate Suzanne (Blender monkey head) .gltf file for testing.

This script uses Blender Python API to create Suzanne mesh and export to .gltf format.
Must be run with: blender --background --python generate_suzanne.py
"""

import bpy
from pathlib import Path

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Delete all mesh data to ensure clean state
for mesh in bpy.data.meshes:
    bpy.data.meshes.remove(mesh)

# Add Suzanne mesh (monkey head)
bpy.ops.mesh.primitive_monkey_add(location=(0, 0, 0))
suzanne = bpy.context.object
suzanne.name = 'Suzanne'

# Add subdivision surface modifier for smoother appearance
modifier = suzanne.modifiers.new(name='Subdivision', type='SUBSURF')
modifier.levels = 2
modifier.render_levels = 2

# Apply modifier
bpy.context.view_layer.objects.active = suzanne
bpy.ops.object.modifier_apply(modifier='Subdivision')

# Add material
mat = bpy.data.materials.new(name='SuzanneMaterial')
mat.use_nodes = True

# Get material nodes
nodes = mat.node_tree.nodes
nodes.clear()

# Create Principled BSDF
bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
bsdf.location = (0, 0)
bsdf.inputs['Base Color'].default_value = (0.8, 0.3, 0.1, 1.0)  # Orange color
bsdf.inputs['Metallic'].default_value = 0.2
bsdf.inputs['Roughness'].default_value = 0.5

# Create Material Output
output = nodes.new(type='ShaderNodeOutputMaterial')
output.location = (300, 0)

# Link nodes
mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

# Assign material to object
if suzanne.data.materials:
    suzanne.data.materials[0] = mat
else:
    suzanne.data.materials.append(mat)

# Select only Suzanne for export
bpy.ops.object.select_all(action='DESELECT')
suzanne.select_set(True)

# Set output path
script_dir = Path(__file__).parent.parent
output_path = script_dir / 'render_engine' / 'test_assets' / 'suzanne.gltf'
output_path.parent.mkdir(parents=True, exist_ok=True)

# Export to .gltf
print(f"Exporting Suzanne to: {output_path}")
bpy.ops.export_scene.gltf(
    filepath=str(output_path),
    export_format='GLTF_SEPARATE',  # .gltf + .bin format
    export_materials='EXPORT',
    export_colors=True,
    export_normals=True,
    export_texcoords=True,
    use_selection=True  # Export only selected objects (Suzanne)
)

print(f"Successfully exported Suzanne to {output_path}")
