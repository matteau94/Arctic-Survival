import bpy, math, sys, os
from mathutils import Vector as V, Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SRC = argv[0] if argv else r"C:\Users\leosp\Documents\Blender\Artic-Survival\Orca_Rigged.blend"
OUTD = r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\7bb4c7a2-2c8e-4793-b5ee-2fc544b80253\scratchpad\r"
TAG = argv[1] if len(argv) > 1 else "orca"
VIEWS = argv[2].split(",") if len(argv) > 2 else ["side", "front34", "top", "under", "head", "jaw", "bend", "rear34"]
os.makedirs(OUTD, exist_ok=True)

if SRC.lower().endswith(".glb"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=SRC)
else:
    bpy.ops.wm.open_mainfile(filepath=SRC)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = 1280, 800
sc.render.film_transparent = False
sc.view_settings.view_transform = 'AgX'
w = bpy.data.worlds.new("W"); sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.62, 0.7, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
for n, rot, e in (("Key", (50, 10, -40), 3.5), ("Fill", (60, 0, 140), 1.2), ("Under", (180 - 30, 0, 20), 0.8)):
    ld = bpy.data.lights.new(n, 'SUN'); ld.energy = e
    lo = bpy.data.objects.new(n, ld); sc.collection.objects.link(lo)
    lo.rotation_euler = Euler([math.radians(a) for a in rot])

meshes = [o for o in sc.objects if o.type == "MESH"]
if os.environ.get("NONRM"):
    for m_ in bpy.data.materials:
        for l_ in list(m_.node_tree.links):
            if l_.to_socket.name == "Normal" and l_.to_node.type == "BSDF_PRINCIPLED":
                m_.node_tree.links.remove(l_)
arm = next((o for o in sc.objects if o.type == 'ARMATURE'), None)
# bounds
import itertools
dg = bpy.context.evaluated_depsgraph_get()
pts = []
for o in meshes:
    pts += [o.matrix_world @ V(c) for c in o.bound_box]
lo = V([min(p[i] for p in pts) for i in range(3)]); hi = V([max(p[i] for p in pts) for i in range(3)])
ctr = (lo + hi) / 2; size = max(hi - lo)

cam_d = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cam_d); sc.collection.objects.link(cam)
sc.camera = cam
cam_d.lens = 50


def look(pos, tgt, ortho=None):
    cam.location = pos
    d = V(tgt) - V(pos)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    if ortho:
        cam_d.type = 'ORTHO'; cam_d.ortho_scale = ortho
    else:
        cam_d.type = 'PERSP'


def reset_pose():
    if arm:
        for pb in arm.pose.bones:
            pb.rotation_mode = 'XYZ'; pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)


def rot(name, x=0, y=0, z=0):
    pb = arm.pose.bones.get(name)
    if pb:
        pb.rotation_mode = 'XYZ'; pb.rotation_euler = (math.radians(x), math.radians(y), math.radians(z))


D = size * 1.9
for v in VIEWS:
    reset_pose()
    if v == "side":
        look(ctr + V((D, 0, 0)), ctr, ortho=size * 1.08)
    elif v == "sideR":
        look(ctr + V((-D, 0, 0)), ctr, ortho=size * 1.08)
    elif v == "front34":
        look(ctr + V((D * 0.55, -D * 0.6, D * 0.25)), ctr)
    elif v == "rear34":
        look(ctr + V((D * 0.5, D * 0.6, D * 0.35)), ctr)
    elif v == "top":
        look(ctr + V((0, 0, D)), ctr, ortho=size * 1.08)
    elif v == "under":
        look(ctr + V((0.001, 0, -D)), ctr, ortho=size * 1.08)
    elif v == "front":
        look(ctr + V((0, -D, 0)), ctr, ortho=size * 0.45)
    elif v == "head":
        h = V((0, -2.45, -0.02)); look(h + V((1.9, -1.2, 0.35)), h)
    elif v == "jaw":
        rot("jaw", x=-30)
        h = V((0, -2.6, -0.2)); look(h + V((1.5, -1.3, -0.2)), h)
    elif v == "eye":
        h = V((0.45, -2.25, 0.07)); look(h + V((0.75, -0.3, 0.12)), h)
    elif v == "blow":
        h = V((0, -1.98, 0.52)); look(h + V((0.35, -0.55, 0.55)), h)
    elif v == "blowopen":
        rot("blowhole", x=25)
        h = V((0, -1.98, 0.52)); look(h + V((0.35, -0.55, 0.55)), h)
    elif v == "flukeflex":
        rot("fluke_tip.L", x=20); rot("fluke_tip.R", x=20); rot("fluke", x=10)
        h = V((0, 2.8, 0)); look(h + V((1.6, 0.9, 0.6)), h)
    elif v == "saddle":
        h = V((0.2, 0.3, 0.45)); look(h + V((2.2, 0.6, 1.2)), h)
    elif v == "pecs":
        rot("pectoral_01.L", x=30, z=-20); rot("pectoral_02.L", x=20); rot("pectoral_01.R", x=-30, z=20)
        h = V((0.4, -1.6, -0.4)); look(h + V((1.8, -1.2, -1.0)), h)
    elif v == "dorsalflex":
        rot("dorsal_01", z=18); rot("dorsal_02", z=18)
        h = V((0, -0.3, 1.0)); look(h + V((1.2, 2.5, 0.9)), h)
    elif v == "fluketop":
        h = V((0, 2.8, 0)); look(h + V((0.0, 0.0, 3.0)), h, ortho=2.0)
    elif v == "fluketopflex":
        rot("fluke_tip.L", x=25); rot("fluke_tip.R", x=-25)
        h = V((0, 2.8, 0)); look(h + V((0.6, 1.6, 1.4)), h)
    elif v == "flukerear":
        rot("fluke_tip.L", x=25); rot("fluke_tip.R", x=25)
        h = V((0, 2.8, -0.05)); look(h + V((0.0, 3.0, 0.3)), h, ortho=2.0)
    elif v == "mouthin":
        rot("jaw", x=-32)
        h = V((0, -2.62, -0.16)); look(h + V((0.35, -1.1, 0.15)), h)
    elif v == "teeth":
        rot("jaw", x=-32)
        h = V((0.2, -2.62, -0.14)); look(h + V((0.55, -0.35, -0.05)), h)
    elif v == "pecroot":
        h = V((0.45, -1.72, -0.3)); look(h + V((1.2, -0.6, -0.2)), h)
    elif v == "dorsalroot":
        h = V((0.0, -0.3, 0.65)); look(h + V((1.6, -0.9, 0.4)), h)
    elif v == "lips":
        h = V((0, -2.7, -0.12)); look(h + V((0.9, -0.5, -0.05)), h)
    elif v == "jawfront":
        rot("jaw", x=-30)
        h = V((0, -2.7, -0.2)); look(h + V((0.5, -2.0, 0.1)), h)
    elif v == "bend":
        for n in ("tail_01", "tail_02", "tail_03", "tail_04", "tail_05", "fluke"):
            rot(n, x=14)
        rot("jaw", x=-20); rot("pectoral_01.L", x=25); rot("pectoral_02.L", x=15); rot("dorsal_01", z=15); rot("dorsal_02", z=15)
        rot("head", x=-8)
        look(ctr + V((D, 0, 0)), ctr, ortho=size * 1.2)
    elif v == "bendneg":
        for n in ("tail_01", "tail_02", "tail_03", "tail_04", "tail_05", "fluke"):
            rot(n, x=-14)
        rot("pectoral_01.L", z=35); rot("pectoral_01.R", z=-35)
        look(ctr + V((D * 0.6, -D * 0.5, D * 0.3)), ctr)
    elif v == "yaw":
        for n in ("tail_01", "tail_02", "tail_03", "tail_04", "tail_05", "fluke"):
            rot(n, z=12)
        look(ctr + V((0, 0, D)), ctr, ortho=size * 1.2)
    bpy.context.view_layer.update()
    sc.render.filepath = os.path.join(OUTD, f"{TAG}_{v}.png")
    bpy.ops.render.render(write_still=True)
    print("[render]", sc.render.filepath)
