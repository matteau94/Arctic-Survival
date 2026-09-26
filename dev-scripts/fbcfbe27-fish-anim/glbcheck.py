import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\Fish Swim Calm.glb")
for a in bpy.data.actions: print("[glb]", a.name, tuple(a.frame_range), len(a.fcurves) if hasattr(a,'fcurves') else '')
print("[glb] objs", [o.name for o in bpy.data.objects])
