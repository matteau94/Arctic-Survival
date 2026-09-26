"""Render stills + contact sheets of the current scene's animation.
args after --: out_dir tag views(comma: side,top,head,front,under,tail) frames(comma or a:b:step)"""
import bpy, sys, math, os
import numpy as np
from mathutils import Vector as V

argv = sys.argv[sys.argv.index("--") + 1:]
out, tag, views, frames = argv[0], argv[1], argv[2].split(","), argv[3]
if ":" in frames:
    a, b, st = map(int, frames.split(":")); frames = list(range(a, b + 1, st))
else:
    frames = [int(x) for x in frames.split(",")]
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = 640, 360
sc.render.image_settings.file_format = 'PNG'
w = sc.world or bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.6, 0.65, 1)
sun = bpy.data.objects.new("s", bpy.data.lights.new("s", "SUN")); sc.collection.objects.link(sun)
sun.rotation_euler = (0.5, 0.3, 0.6); sun.data.energy = 3
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.clip_start = 0.0001; cam.data.clip_end = 10
C = V((0, 0.0064, 0.0075))
VIEWS = {
    "side": (C, V((1, 0, 0)), (math.pi / 2, 0, math.pi / 2), 0.072),
    "top": (C, V((0, 0, 1)), (0, 0, math.pi / 2), 0.072),
    "under": (C, V((0, 0, -1)), (math.pi, 0, math.pi / 2), 0.072),
    "head": (V((0, -0.017, 0.007)), V((1, 0, 0)), (math.pi / 2, 0, math.pi / 2), 0.016),
    "headtop": (V((0, -0.013, 0.007)), V((0, 0, 1)), (0, 0, math.pi / 2), 0.024),
    "front": (V((0, 0, 0.007)), V((0, -1, 0)), (math.pi / 2, 0, 0), 0.03),
    "tail": (V((0, 0.03, 0.008)), V((0, 0, 1)), (0, 0, math.pi / 2), 0.03),
    "pec": (V((0, -0.008, 0.004)), V((0.6, 0, -0.8)).normalized(), None, 0.022),
}
os.makedirs(out, exist_ok=True)
for vn in views:
    c, d, rot, scale = VIEWS[vn]
    cam.location = c + d
    cam.rotation_euler = rot if rot else (-d).to_track_quat('-Z', 'Z').to_euler()
    cam.data.ortho_scale = scale
    paths = []
    for f in frames:
        sc.frame_set(f)
        sc.render.filepath = os.path.join(out, f"{tag}_{vn}_{f:03d}.png")
        bpy.ops.render.render(write_still=True)
        paths.append(sc.render.filepath)
    # contact sheet (columns of 4)
    ims = []
    for pth in paths:
        im = bpy.data.images.load(pth)
        a = np.array(im.pixels[:]).reshape(im.size[1], im.size[0], 4)
        ims.append(a); bpy.data.images.remove(im)
    h, wd = ims[0].shape[:2]
    cols = 4 if len(ims) > 4 else len(ims); rows = math.ceil(len(ims) / cols)
    sheet = np.ones((rows * h, cols * wd, 4))
    for i, a in enumerate(ims):
        r, cc = divmod(i, cols)
        rr = rows - 1 - r   # image origin bottom-left
        sheet[rr * h:(rr + 1) * h, cc * wd:(cc + 1) * wd] = a
        sheet[rr * h:(rr + 1) * h, cc * wd:cc * wd + 2] = 0
        sheet[rr * h:rr * h + 2, cc * wd:(cc + 1) * wd] = 0
    img = bpy.data.images.new(f"sheet_{vn}", cols * wd, rows * h, alpha=True)
    img.pixels = sheet.ravel()
    img.filepath_raw = os.path.join(out, f"{tag}_{vn}_sheet.png"); img.file_format = 'PNG'; img.save()
    for pth in paths:
        if len(paths) > 1:
            pass
print("[stills] done")
