import bpy
p = bpy.ops.export_scene.gltf.get_rna_type().properties
print("OPTS", [k.identifier for k in p if 'anim' in k.identifier or 'frame' in k.identifier or 'slide' in k.identifier])
print("MODE", p['export_animation_mode'].default, [e.identifier for e in p['export_animation_mode'].enum_items])
