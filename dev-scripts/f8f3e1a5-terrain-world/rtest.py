import bpy
s = bpy.context.scene; s.render.resolution_x, s.render.resolution_y = 640, 360
s.render.filepath = r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\f8f3e1a5-a64d-4376-bcb4-8359c5ce6238\scratchpad\r.png"
cam = s.camera; cam.location.z = 400
import math; cam.rotation_euler[0] = math.radians(80)
bpy.ops.render.render(write_still=True)
