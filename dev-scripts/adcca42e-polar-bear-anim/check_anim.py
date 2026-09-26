import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\Polar Bear Animated.glb")
for a in bpy.data.actions: print("ACTION", a.name, [round(x, 2) for x in a.frame_range])
print("BONES", [len(o.data.bones) for o in bpy.data.objects if o.type == 'ARMATURE'])
