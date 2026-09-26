# Head close-ups for one clip: rows = frames; columns = side, 3/4, front
import bpy, sys
import numpy as np
from mathutils import Vector
blend, clip, frames, out = sys.argv[sys.argv.index("--") + 1:][:4]
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
arm = bpy.data.objects["PolarBearRig"]; arm.animation_data.action = bpy.data.actions[clip]
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading; sh.color_type = 'TEXTURE'; sh.light = 'STUDIO'; sh.show_cavity = True
sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new("w"); w.color = (0.8, 0.86, 0.92); sc.world = w
W = H = 300
sc.render.resolution_x, sc.render.resolution_y = W, H
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 0.03
rows = []
for f in [int(x) for x in frames.split(",")]:
    sc.frame_set(f)
    hb = arm.pose.bones["head"]
    c = arm.matrix_world @ hb.head.lerp(hb.tail, 0.62) + Vector((0, 0, -0.004))
    fwd = (arm.matrix_world.to_3x3() @ (hb.tail - hb.head)).normalized()
    tiles = []
    for d in (Vector((1, 0, 0)), (Vector((0.8, 0, 0)) + fwd).normalized(), (fwd + Vector((0, 0, 0.05))).normalized()):
        cam.location = c + d * 0.3
        cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
        p = out + ".tmp.png"; sc.render.filepath = p; bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(p); tiles.append(np.array(im.pixels[:], dtype=np.float32).reshape(H, W, 4)); bpy.data.images.remove(im)
    rows.append(np.concatenate(tiles, axis=1))
sheet = np.concatenate(rows, axis=1)
im = bpy.data.images.new("s", sheet.shape[1], sheet.shape[0]); im.pixels = sheet.ravel()
im.filepath_raw = out; im.file_format = 'PNG'; im.save()
