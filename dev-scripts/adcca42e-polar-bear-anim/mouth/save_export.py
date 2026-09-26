import bpy, sys
clip, glb = sys.argv[sys.argv.index("--") + 1:][:2]
arm = bpy.data.objects["PolarBearRig"]
act = bpy.data.actions[clip]
arm.animation_data.action = act
sc = bpy.context.scene
f0, f1 = (int(round(x)) for x in act.frame_range)
sc.frame_start, sc.frame_end = f0, f1 - 1          # last key == first frame (loop)
sc.frame_set(f0)
bpy.ops.wm.save_mainfile()
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', export_animations=True,
                          export_animation_mode='ACTIVE_ACTIONS', export_force_sampling=True,
                          export_frame_range=False, use_selection=False)
print("[save]", bpy.data.filepath, "->", glb, "clip", clip, f0, f1)
