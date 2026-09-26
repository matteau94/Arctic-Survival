# Pose only the jaw (rest everything else) and render the head: side, 3/4, front, 3/4 low.
import bpy, sys, math
import numpy as np
from mathutils import Vector, Quaternion
args = sys.argv[sys.argv.index("--") + 1:]
out, angles = args[0], [float(a) for a in args[1].split(",")]
extra = args[2] if len(args) > 2 else ""
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-GitHub-Hockey-202609\adcca42e-ad80-4670-abe5-ecf9d0929f1f\scratchpad\mouth\line_test.blend")
sc = bpy.context.scene
arm = bpy.data.objects["PolarBearRig"]; arm.animation_data.action = None
for p in arm.pose.bones: p.matrix_basis.identity()
if extra: exec(open(extra).read())
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 16
sc.view_settings.view_transform = 'Standard'
_w = bpy.data.worlds.new('ww'); _w.use_nodes = True
_w.node_tree.nodes['Background'].inputs[0].default_value = (0.8, 0.85, 0.9, 1); _w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
sc.world = _w
_l = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(_l)
_l.data.energy = 3.0; _l.rotation_euler = (0.9, 0.2, 0.6)
sh = sc.display.shading; sh.color_type = 'TEXTURE'; sh.light = 'STUDIO'; sh.show_cavity = True
sc.view_settings.view_transform = 'Standard'

W = H = 360
sc.render.resolution_x, sc.render.resolution_y = W, H
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 0.024
pb = arm.pose.bones
def about_x(p_, a):
    r = p_.bone.matrix_local.to_quaternion(); return r.inverted() @ Quaternion((1, 0, 0), a) @ r
rows = []
for a in angles:
    pb["jaw"].rotation_mode = 'QUATERNION'
    pb["jaw"].rotation_quaternion = about_x(pb["jaw"], math.radians(a))
    bpy.context.view_layer.update()
    c = arm.matrix_world @ Vector((0, -7.05, 6.75))
    tiles = []
    for d in (Vector((1, 0, 0)), Vector((0.7, -0.7, 0.1)).normalized(), Vector((0, -1, 0.05)).normalized(), Vector((0.6, -0.6, -0.5)).normalized()):
        cam.location = c + d * 0.3
        cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
        p = out + ".tmp.png"; sc.render.filepath = p; bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(p); tiles.append(np.array(im.pixels[:], dtype=np.float32).reshape(H, W, 4)); bpy.data.images.remove(im)
    rows.append(np.concatenate(tiles, axis=1))
sheet = np.concatenate(rows[::-1], axis=0)
im = bpy.data.images.new("s", sheet.shape[1], sheet.shape[0]); im.pixels = sheet.ravel()
im.filepath_raw = out; im.file_format = 'PNG'; im.save()
