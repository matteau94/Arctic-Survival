import bpy
D = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
arm = bpy.data.objects["PolarBearRig"]
walk, run = bpy.data.actions["Walk"], bpy.data.actions["Run"]
arm.animation_data.action = walk
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 56
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=D + r"\Polar Bear Walking.blend", copy=True)
common = dict(export_format='GLB', export_animations=True, export_force_sampling=True,
              export_frame_range=False, use_selection=False)
# walk clip only
bpy.ops.export_scene.gltf(filepath=D + r"\Polar Bear Walking.glb", export_animation_mode='ACTIVE_ACTIONS', **common)
# both clips in one file for the game
bpy.ops.export_scene.gltf(filepath=D + r"\Polar Bear Animated.glb", export_animation_mode='ACTIONS', **common)
print("saved; active action:", arm.animation_data.action.name, "file still:", bpy.data.filepath)
