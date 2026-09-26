"""Preview renders: contact sheets (rows = side / 3-4 / front, cols = frames) and optional mp4.
blender -b test.blend --python render.py -- <clip> <out_prefix> [ncols] [--mp4] [--frames a,b,c] [--views side,q34,front]"""
import bpy, math, sys, os
import numpy as np
from mathutils import Vector as V

argv = sys.argv[sys.argv.index("--") + 1:]
clip, out = argv[0], argv[1]
ncols = int(argv[2]) if len(argv) > 2 and argv[2].isdigit() else 8
mp4 = "--mp4" in argv
frames_arg = argv[argv.index("--frames") + 1] if "--frames" in argv else None
views_arg = argv[argv.index("--views") + 1].split(",") if "--views" in argv else ["side", "q34", "front"]
W, H = (int(argv[argv.index("--res") + 1].split("x")[0]), int(argv[argv.index("--res") + 1].split("x")[1])) if "--res" in argv else (300, 420)

scene = bpy.context.scene
arm = bpy.data.objects["HumanRig"]
body = bpy.data.objects["Human"]
act = bpy.data.actions[clip]
arm.animation_data.action = act
if act.slots:
    arm.animation_data.action_slot = act.slots[0]
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
v = act.get("speed_mps", 0.0)
stub = len(body.data.vertices) < 20000 and "Stub" in bpy.data.filepath or "test" in bpy.data.filepath.lower() and len(body.data.vertices) < 20000

try:
    scene.render.engine = 'BLENDER_EEVEE'
except TypeError:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
try:
    scene.eevee.taa_render_samples = 16
except Exception:
    pass
scene.view_settings.view_transform = 'Standard'

# world
wd = bpy.data.worlds.new("W")
wd.use_nodes = True
wd.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.68, 0.78, 1)
wd.node_tree.nodes["Background"].inputs[1].default_value = 0.8
scene.world = wd
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(35))
scene.collection.objects.link(sun)


def mat(name, col):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = col
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.7
    return m


if stub:
    # own rigid mannequin: one bone-parented piece per bone (the stub's skinning is not reliable)
    import bmesh
    from mathutils import Matrix
    body.hide_render = True
    MT = {"T": mat("Trunk", (0.75, 0.72, 0.66, 1)), "L": mat("Left", (0.15, 0.35, 0.85, 1)),
          "R": mat("Right", (0.85, 0.25, 0.15, 1)), "H": mat("Head", (0.9, 0.75, 0.6, 1)),
          "E": mat("Eye", (0.05, 0.05, 0.05, 1)), "D": mat("Hood", (0.45, 0.33, 0.2, 1))}
    RAD = {"pelvis": 0.15, "spine_01": 0.14, "spine_02": 0.15, "spine_03": 0.16, "neck": 0.055,
           "head": 0.10, "jaw": 0.035, "hood_01": 0.07, "hood_02": 0.06, "clavicle": 0.045,
           "upper_arm": 0.065, "forearm": 0.055, "hand": 0.04, "thigh": 0.09, "shin": 0.065}
    for b in arm.data.bones:
        base = b.name.split(".")[0]
        if base in ("root", "prop", "brow", "lid_upper", "lid_lower"):
            continue
        bm = bmesh.new()
        m = b.matrix_local.copy()
        side = b.name[-1] if b.name[-2:] in (".L", ".R") else "T"
        if base == "foot" or base == "toe":
            h, t = b.head_local, b.tail_local
            if base == "foot":
                y0, y1, z1 = h.y + 0.068, t.y, 0.11
            else:
                y0, y1, z1 = h.y, t.y - 0.01, 0.055
            cx = h.x
            geom = bmesh.ops.create_cube(bm, size=1.0)
            for vv in geom["verts"]:
                c = vv.co.copy()
                vv.co = V((cx + c.x * 0.10, (y0 + y1) / 2 + c.y * abs(y1 - y0), (c.z + 0.5) * z1))
        elif base == "eye":
            geom = bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=0.014)
            for vv in geom["verts"]:
                vv.co = m @ V((vv.co.x, vv.co.y + 0.012, vv.co.z))
            side = "E"
        else:
            r = RAD.get(base, 0.012)
            geom = bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=9, radius=1.0)
            for vv in geom["verts"]:
                c = vv.co
                vv.co = m @ V((c.x * r, (c.y * 0.5 + 0.5) * b.length, c.z * r))
            if base in ("head", "neck", "jaw"):
                side = "H"
            if base.startswith("hood"):
                side = "D"
        me = bpy.data.meshes.new("pc_" + b.name)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(MT[side])
        ob = bpy.data.objects.new("pc_" + b.name, me)
        scene.collection.objects.link(ob)
        ob.parent = arm
        ob.parent_type = 'BONE'
        ob.parent_bone = b.name
        ob.matrix_parent_inverse = (b.matrix_local @ Matrix.Translation((0, b.length, 0))).inverted()

# ground: checker in object space, moving back at the clip's speed
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
gp = bpy.context.active_object
gm = bpy.data.materials.new("Ground")
gm.use_nodes = True
nt = gm.node_tree
tc = nt.nodes.new("ShaderNodeTexCoord")
ck = nt.nodes.new("ShaderNodeTexChecker")
ck.inputs["Scale"].default_value = 60.0          # 60 m plane, generated coords -> 1 m squares -> use object
ck.inputs["Color1"].default_value = (0.92, 0.94, 0.97, 1)
ck.inputs["Color2"].default_value = (0.55, 0.60, 0.68, 1)
mp = nt.nodes.new("ShaderNodeMapping")
mp.inputs["Scale"].default_value = (1, 1, 1)
nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
nt.links.new(mp.outputs["Vector"], ck.inputs["Vector"])
ck.inputs["Scale"].default_value = 2.0
nt.links.new(ck.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
gp.data.materials.append(gm)
gp.location.y = 0.0
gp.keyframe_insert("location", index=1, frame=f0)
gp.location.y = v * (f1 - f0) / 60.0
gp.keyframe_insert("location", index=1, frame=f1)
for fc in (gp.animation_data.action.layers[0].strips[0].channelbags[0].fcurves if hasattr(gp.animation_data.action, "layers") else gp.animation_data.action.fcurves):
    for kp in fc.keyframe_points:
        kp.interpolation = 'LINEAR'

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam)
scene.camera = cam
VIEWS = {
    "side": (V((5.0, -0.1, 0.95)), V((0, -0.1, 0.85)), 'ORTHO'),
    "q34": (V((3.2, -3.4, 1.55)), V((0, 0, 0.8)), 'PERSP'),
    "front": (V((0.0, -5.0, 1.0)), V((0, 0, 0.85)), 'ORTHO'),
    "back": (V((0.0, 5.0, 1.2)), V((0, 0, 0.9)), 'ORTHO'),
    "face": (V((0.6, -1.6, 1.68)), V((0, 0, 1.62)), 'PERSP'),
}


def set_view(name):
    loc, tgt, typ = VIEWS[name]
    cam.location = loc
    cam.rotation_euler = (tgt - loc).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = typ
    cam.data.ortho_scale = 2.3
    cam.data.lens = 50 if name != "face" else 85


if frames_arg:
    frames = [int(x) for x in frames_arg.split(",")]
else:
    n = f1 - f0
    frames = [f0 + round(i * n / ncols) for i in range(ncols)]
tmp = out + "_tmp"
os.makedirs(tmp, exist_ok=True)
rows = []
for vn in views_arg:
    set_view(vn)
    row = []
    for f in frames:
        scene.frame_set(f)
        p = os.path.join(tmp, f"{vn}_{f:04d}.png")
        scene.render.filepath = p
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(p)
        a = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)
        a[:3, :, :3] = 0.1
        a[:, :2, :3] = 0.1
        row.append(a)
        bpy.data.images.remove(img)
    rows.append(np.concatenate(row, axis=1))
sheet = np.concatenate(rows[::-1], axis=0)       # images are bottom-up
hh, ww = sheet.shape[:2]
im = bpy.data.images.new("sheet", ww, hh, alpha=True)
im.pixels = sheet.ravel()
im.filepath_raw = out + ".png"
im.file_format = 'PNG'
im.save()
print("sheet", out + ".png", "frames", frames)

if mp4:
    set_view(views_arg[0])
    scene.frame_start, scene.frame_end = f0, f1 - 1
    scene.render.image_settings.media_type = 'VIDEO' if hasattr(scene.render.image_settings, "media_type") else None
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.filepath = out + ".mp4"
    bpy.ops.render.render(animation=True)
    print("mp4", out + ".mp4")
