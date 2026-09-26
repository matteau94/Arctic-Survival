import bpy, math
s = bpy.context.scene; s.render.resolution_x, s.render.resolution_y = 640, 360
cam = s.camera; cam.location.z = 1500; cam.rotation_euler = (math.radians(78), 0, math.radians(160))
s.render.filepath = r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\f8f3e1a5-a64d-4376-bcb4-8359c5ce6238\scratchpad\r2.png"
bpy.ops.render.render(write_still=True)
