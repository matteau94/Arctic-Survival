import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\Fish Swim Flee.glb")
for a in bpy.data.actions: print("GLBACT", a.name, tuple(a.frame_range))
