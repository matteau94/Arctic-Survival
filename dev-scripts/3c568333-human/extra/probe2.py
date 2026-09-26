import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\ArcticFox_Animated.glb")
for a in bpy.data.actions: print(a.name, a.frame_range[:], len(a.slots))
for o in bpy.data.objects: print(o.name,o.type, o.dimensions[:])
print([i.name for i in bpy.data.images])
