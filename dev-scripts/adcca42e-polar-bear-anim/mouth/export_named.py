import bpy, sys
clip, glb = sys.argv[sys.argv.index("--") + 1:][:2]
arm = bpy.data.objects["PolarBearRig"]
arm.animation_data.action = bpy.data.actions[clip]
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', export_animations=True,
                          export_animation_mode='ACTIVE_ACTIONS', export_nla_strips_merged_animation_name=clip,
                          export_force_sampling=True, export_frame_range=False, use_selection=False)
