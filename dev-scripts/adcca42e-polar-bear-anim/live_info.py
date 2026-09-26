import bpy
arm = bpy.data.objects.get("PolarBearRig")
print("file:", bpy.data.filepath, "dirty:", bpy.data.is_dirty)
print("actions:", [(a.name, tuple(a.frame_range), a.users) for a in bpy.data.actions])
print("active action:", arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None)
print("scale:", tuple(arm.scale), "bones:", len(arm.data.bones), "fps:", bpy.context.scene.render.fps, "range:", bpy.context.scene.frame_start, bpy.context.scene.frame_end)
print("has ear/jaw/ctrl:", all(n in arm.pose.bones for n in ("ear.L", "jaw", "ctrl.FL", "ctrl_toe.HR", "scapula.FR")))
print("objects:", [(o.name, o.type) for o in bpy.data.objects])
