# Head close-ups: rows = rest pose, animated frame; columns = side, 3/4 front, front
import bpy, sys, math
import numpy as np
from mathutils import Vector
out = sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\Documents\Polar Bear Running.blend")
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading; sh.color_type = 'TEXTURE'; sh.light = 'STUDIO'; sh.show_cavity = True
sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new("w"); w.color = (0.8, 0.86, 0.92); sc.world = w
W = H = 420
sc.render.resolution_x, sc.render.resolution_y = W, H
arm = bpy.data.objects["PolarBearRig"]
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 0.04
rows = []
for state in (1, 9):
    if False: pass
    else: arm.data.pose_position = 'POSE'; sc.frame_set(state)
    bpy.context.view_layer.update()
    hb = arm.pose.bones["head"]
    # focus on the muzzle: 70% along the skull bone, a bit below it
    c = arm.matrix_world @ (hb.head.lerp(hb.tail, 0.62)) + Vector((0, 0, -0.004))
    fwd = (arm.matrix_world.to_3x3() @ (hb.tail - hb.head)).normalized()
    tiles = []
    for d in (Vector((1, 0.3, 0.9)).normalized(), Vector((-0.6, 0.8, 0.9)).normalized(), fwd):
        cam.location = c + d * 0.3 + Vector((0, 0, 0.02 if d is not None else 0))
        cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
        p = f"{out}.tmp.png"; sc.render.filepath = p; bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(p); tiles.append(np.array(im.pixels[:], dtype=np.float32).reshape(H, W, 4)); bpy.data.images.remove(im)
    rows.append(np.concatenate(tiles, axis=1))
sheet = np.concatenate(rows[::-1], axis=0)
im = bpy.data.images.new("s", sheet.shape[1], sheet.shape[0]); im.pixels = sheet.ravel()
im.filepath_raw = out; im.file_format = 'PNG'; im.save()
