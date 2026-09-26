"""blender -b test.blend --python strip.py -- <action> <out.png> [ncols] [views side,3q,front] [frames f1,f2,..]
Renders a grid of frames (rows = views) with Workbench on a grid ground plane."""
import bpy, sys, math, os
import numpy as np
from mathutils import Vector as V

argv = sys.argv[sys.argv.index("--") + 1:]
act_name, out = argv[0], argv[1]
ncol = int(argv[2]) if len(argv) > 2 else 8
views = argv[3].split(",") if len(argv) > 3 else ["side", "3q"]
frames = [int(x) for x in argv[4].split(",")] if len(argv) > 4 else None
sc = bpy.context.scene
arm = bpy.data.objects["HumanRig"]
mesh = bpy.data.objects["Human"]
act = bpy.data.actions[act_name] if act_name != "REST" else bpy.data.actions[0]
arm.animation_data.action = act if act_name != "REST" else None
try:
    arm.animation_data.action_slot = act.slots[0]
except Exception:
    pass
fs, fe = int(act.frame_range[0]), int(act.frame_range[1])
if frames is None:
    frames = [int(round(fs + (fe - fs) * k / (ncol - 1))) for k in range(ncol)]
import bmesh
def make_prop(kind):
    bm = bmesh.new()
    if kind == "axe":
        segs = [(-0.12, 0.55, 0.016)]
    else:
        segs = [(-1.05, 0.95, 0.013)]
    for y0, y1, r in segs:
        g = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=r, radius2=r, depth=y1 - y0)
        for v in g["verts"]:
            v.co = V((v.co.x, v.co.z + (y0 + y1) / 2, v.co.y))
    if kind == "axe":
        g = bmesh.ops.create_cube(bm, size=1.0)
        for v in g["verts"]:
            v.co = V((v.co.x * 0.03, v.co.y * 0.06 + 0.52, v.co.z * 0.20 + 0.06))
    else:
        g = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.025, radius2=0.0, depth=0.18)
        for v in g["verts"]:
            v.co = V((v.co.x, v.co.z + 1.04, v.co.y))
    me_ = bpy.data.meshes.new("prop"); bm.to_mesh(me_)
    ob = bpy.data.objects.new("prop", me_); sc.collection.objects.link(ob)
    ob.parent = arm; ob.parent_type = 'BONE'; ob.parent_bone = "prop.R"
    ob.matrix_parent_inverse.identity()
    ob.location = (0, -arm.data.bones["prop.R"].length, 0)
    m = bpy.data.materials.new("pm"); m.diffuse_color = (0.35, 0.2, 0.1, 1); me_.materials.append(m)
if act_name == "Human_Attack":
    make_prop("axe")
if act_name == "Human_Throw":
    make_prop("spear")
# ground grid
me = bpy.data.meshes.new("g")
s = 4
verts, faces = [], []
N = 16
for i in range(N + 1):
    for j in range(N + 1):
        verts.append((-s + 2 * s * i / N, -s + 2 * s * j / N, 0))
for i in range(N):
    for j in range(N):
        a = i * (N + 1) + j
        faces.append((a, a + N + 1, a + N + 2, a + 1))
me.from_pydata(verts, [], faces)
gnd = bpy.data.objects.new("g", me)
sc.collection.objects.link(gnd)
mat = bpy.data.materials.new("gm")
mat.diffuse_color = (0.8, 0.85, 0.9, 1)
me.materials.append(mat)
for p in me.polygons:
    p.material_index = 0
mat2 = bpy.data.materials.new("gm2"); mat2.diffuse_color = (0.55, 0.6, 0.7, 1)
me.materials.append(mat2)
for p in me.polygons:
    i, j = divmod(p.index, N)
    p.material_index = (i + j) % 2
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'MATERIAL'
sc.display.shading.show_shadows = True
sc.display.shading.show_cavity = True
mesh.data.materials.clear() if False else None
sc.render.resolution_x = 360
sc.render.resolution_y = 420
sc.render.film_transparent = False
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'
cam.data.clip_end = 100
tmp = os.path.join(os.path.dirname(out), "_strip_tmp")
os.makedirs(tmp, exist_ok=True)
imgs = []
for view in views:
    row = []
    for f in frames:
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = mesh.evaluated_get(dg); m = ev.to_mesh()
        co = np.array([v.co[:] for v in m.vertices]); ev.to_mesh_clear()
        lo, hi = co.min(0), co.max(0)
        c = V(((lo + hi) / 2).tolist())
        c.z = 0.85 if hi[2] > 1.0 else (lo[2] + hi[2]) / 2 + 0.25
        cam.data.ortho_scale = 2.3
        d = {"side": V((1, 0, 0.12)), "3q": V((0.8, -1, 0.35)), "front": V((0, -1, 0.1)),
             "back": V((0.3, 1, 0.3)), "top": V((0.2, 0.3, 1)), "rside": V((-1, 0, 0.05))}[view].normalized()
        cam.location = c + d * 10
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        p = os.path.join(tmp, f"{view}_{f}.png")
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(p)
        a = np.array(img.pixels[:], np.float32).reshape(img.size[1], img.size[0], 4)
        bpy.data.images.remove(img)
        row.append(a)
    imgs.append(row)
h, w = imgs[0][0].shape[:2]
R, Cn = len(imgs), len(frames)
S = np.ones((R * h, Cn * w, 4), np.float32)
for r, row in enumerate(imgs):
    for c_, a in enumerate(row):
        y0 = (R - 1 - r) * h
        S[y0:y0 + h, c_ * w:(c_ + 1) * w] = a
        S[y0:y0 + h, c_ * w:c_ * w + 1] = 0
im = bpy.data.images.new("sheet", Cn * w, R * h)
im.pixels.foreach_set(S.ravel())
im.filepath_raw = out; im.file_format = 'PNG'; im.save()
print("frames", frames, "->", out)
