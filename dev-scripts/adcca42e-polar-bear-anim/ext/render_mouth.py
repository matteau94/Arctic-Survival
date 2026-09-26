# Usage: blender -b --python render_mouth.py -- <blend> <out.png>
# Renders the (baked, jaw at rest) head in EEVEE: row 1 zoom on the mouth (side, 3/4, front),
# row 2 whole head (side, 3/4, front).
import bpy, sys, math
import numpy as np
from mathutils import Vector
blend, out = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
arm = bpy.data.objects["PolarBearRig"]; arm.animation_data.action = None
for p in arm.pose.bones: p.matrix_basis.identity()
sc.render.engine = 'BLENDER_EEVEE'; sc.eevee.taa_render_samples = 16
sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new('ww'); w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.8, 0.85, 0.9, 1); sc.world = w
l = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(l)
l.data.energy = 3.0; l.rotation_euler = (0.9, 0.2, 0.6)
W = H = 400
sc.render.resolution_x, sc.render.resolution_y = W, H
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'
bpy.context.view_layer.update()
rows = []
for scale, c in ((0.013, Vector((0, -7.3, 6.75))), (0.03, Vector((0, -6.6, 7.0)))):
    cam.data.ortho_scale = scale
    cw = arm.matrix_world @ c
    tiles = []
    for d in (Vector((1, 0, 0)), Vector((0.8, -0.45, 0.3)).normalized(), Vector((0, -1, 0.08)).normalized()):
        cam.location = cw + d * 0.3
        cam.rotation_euler = (cw - cam.location).to_track_quat('-Z', 'Y').to_euler()
        pth = out + ".tmp.png"; sc.render.filepath = pth; bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(pth); tiles.append(np.array(im.pixels[:], dtype=np.float32).reshape(H, W, 4)); bpy.data.images.remove(im)
    rows.append(np.concatenate(tiles, axis=1))
sheet = np.concatenate(rows[::-1], axis=0)
im = bpy.data.images.new("s", sheet.shape[1], sheet.shape[0]); im.pixels = sheet.ravel()
im.filepath_raw = out; im.file_format = 'PNG'; im.save()
import os; os.remove(out + ".tmp.png")
