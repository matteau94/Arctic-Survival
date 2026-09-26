"""rv.py -- src prefix frames(comma|a:b) views(comma) [focus x,y,z mesh-units] [ortho scale mesh-units] [res WxH] [video 0/1] [slow factor]"""
import bpy, sys, math
from mathutils import Vector as V
a = sys.argv[sys.argv.index("--")+1:]
src, prefix, frames, views = a[0], a[1], a[2], a[3].split(",")
focus = V([float(x) for x in a[4].split(",")]) if len(a) > 4 and a[4] != "-" else V((0, 0.6, 0.75))
scale = float(a[5]) if len(a) > 5 else 7.0
res = [int(x) for x in a[6].split("x")] if len(a) > 6 else [960, 540]
video = len(a) > 7 and a[7] == "1"
slow = int(a[8]) if len(a) > 8 else 1
bpy.ops.wm.open_mainfile(filepath=src)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 8
sc.render.resolution_x, sc.render.resolution_y = res
sc.render.resolution_percentage = 100
sc.render.fps = 60
w = sc.world or bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.35, 0.5, 0.6, 1); bg.inputs[1].default_value = 1.0
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
sun.rotation_euler = (0.5, 0.2, 0.6); sun.data.energy = 3.5
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = scale * 0.01
cam.data.clip_start = 0.0001; cam.data.clip_end = 10
c = focus * 0.01
D = {"side": V((1, 0, 0)), "otherside": V((-1, 0, 0)), "top": V((0, 0, 1)), "under": V((0, 0, -1)),
     "front": V((0, -1, 0)), "back": V((0, 1, 0)), "persp": V((1, -0.6, 0.8)).normalized()}
def place(name):
    d = D[name]
    cam.location = c + d * 1.0
    up = 'X' if name in ("top", "under") else 'Y'
    cam.rotation_euler = (-d).to_track_quat("-Z", up).to_euler()
    if name == "top": cam.rotation_euler = (0, 0, math.pi / 2)
if video:
    sc.render.image_settings.media_type = 'VIDEO'
    sc.render.image_settings.file_format = 'FFMPEG'
    sc.render.ffmpeg.format = 'MPEG4'; sc.render.ffmpeg.codec = 'H264'
    sc.render.ffmpeg.constant_rate_factor = 'HIGH'
    f0, f1 = [int(x) for x in frames.split(":")]
    if slow > 1:
        sc.render.frame_map_old = 1; sc.render.frame_map_new = slow
        f0, f1 = (f0 - 1) * slow + 1, f1 * slow
    sc.frame_start, sc.frame_end = f0, f1
    place(views[0])
    sc.render.filepath = prefix
    bpy.ops.render.render(animation=True)
else:
    fr = [int(x) for x in frames.split(",")]
    for v in views:
        place(v)
        for f in fr:
            sc.frame_set(f)
            sc.render.filepath = f"{prefix}_{v}_{f:03d}.png"
            bpy.ops.render.render(write_still=True)
