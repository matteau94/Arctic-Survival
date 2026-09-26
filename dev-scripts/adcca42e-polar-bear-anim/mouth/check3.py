import bpy
A = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
for f in ("Polar Bear Running.glb", "Polar Bear Walking.glb", "Polar Bear Animated.glb"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=A + "\\" + f)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    print(f"CHECK {f}: bones {len(arm.data.bones)}, lip bones {sum(b.name.startswith('lip_') for b in arm.data.bones)}, clips {sorted(a.name for a in bpy.data.actions)}")
