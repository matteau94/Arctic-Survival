"""Close the salmon's mouth and rig it for swimming.

    blender -b --python fish_prep.py        (reads Fish.glb, writes Fish_Rigged.blend)

Fish.glb is an unrigged salmon: RootNode (empty, scale 0.01) > 'fish.1' (mesh). Mesh-local
units (used everywhere below): snout at y = -2.33, caudal fin tip at y = +3.61, belly z = 0,
back z ~ 1.45. The fish faces -Y, so +X is its left side.

1. Mouth: the lower jaw is modelled dropped ~10 deg. Every vertex below the lip line
   (from the snout (-2.30, 0.775) back to the mouth corner) is rotated up about the jaw
   joint; the weight fades out behind the joint and across the lip line so the throat and
   mouth corners bend instead of tearing. Lower teeth (separate islands) go up rigidly with
   the jaw. The result is baked into the mesh, so the rest pose is shut.
2. Rig 'FishRig' (child of RootNode, identity) with the mesh parented to it:
     root (no deform, near the centre of mass)
       spine_01 > head > jaw, operculum.L/R, eye.L/R
       spine_02 > spine_03 > spine_04 > spine_05 > caudal > caudal_tip
       pectoral.L/R (on spine_01), pelvic.L/R (spine_03), dorsal (spine_02),
       adipose (spine_05), anal (spine_04)
   Body weights are smooth blends along the chain; fins (separate islands) blend from
   their body bone at the fin root to their own bone at the fin tip.
"""
import bpy, bmesh, math
from mathutils import Vector as V, Matrix

SRC = r"C:\Users\leosp\Documents\Blender\Artic-Survival\Fish.glb"
OUT = r"C:\Users\leosp\Documents\Blender\Artic-Survival\Fish_Rigged.blend"

JAW_PIVOT = V((0, -1.80, 0.60))
JAW_CLOSE = math.radians(-10.0)          # about +X; negative lifts the tip


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def lip_z(y):                           # lip line (gap between the jaws)
    return 0.703 - 0.24 * (y + 2.0)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
root_node = bpy.data.objects["RootNode.0"]
fish = bpy.data.objects["fish.1"]
fish.name = "Fish"
me = fish.data

# ----------------------------------------------------------------- islands
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
island = [-1] * len(bm.verts); islands = []
for v in bm.verts:
    if island[v.index] >= 0:
        continue
    k = len(islands); island[v.index] = k; st = [v]; members = [v.index]
    while st:
        x = st.pop()
        for e in x.link_edges:
            w = e.other_vert(x)
            if island[w.index] < 0:
                island[w.index] = k; st.append(w); members.append(w.index)
    islands.append(members)
bm.free()
co = [v.co.copy() for v in me.vertices]


def centre(ids):
    return sum((co[i] for i in ids), V()) / len(ids)


body_k = max(range(len(islands)), key=lambda k: len(islands[k]))
kind = {}
for k, ids in enumerate(islands):
    if k == body_k:
        kind[k] = "body"; continue
    c = centre(ids)
    if c.y < -1.7 and len(ids) < 100:
        kind[k] = "tooth_lo" if c.z < lip_z(c.y) else "tooth_up"
    elif len(ids) > 200 and c.y < -1.8 and abs(c.x) < 0.05:
        kind[k] = "mouth"
    elif -2.0 < c.y < -1.8 and abs(c.x) > 0.15:
        kind[k] = "eye"
    elif -1.1 < c.y < -0.35 and abs(c.x) > 0.25:
        kind[k] = "pectoral"
    elif 0.1 < c.y < 0.9 and c.z < 0.3 and abs(c.x) > 0.15:
        kind[k] = "pelvic"
    elif -0.1 < c.y < 0.9 and c.z > 1.2:
        kind[k] = "dorsal"
    elif 1.7 < c.y < 2.3 and c.z > 1.0:
        kind[k] = "adipose"
    else:
        kind[k] = "other"
print("[prep] islands:", {l: sum(1 for k in kind if kind[k] == l) for l in set(kind.values())})


# ----------------------------------------------------------------- 1. close the mouth
def jaw_weight(i):
    k = kind[island[i]]; p = co[i]
    if k == "tooth_lo":
        return 1.0
    if k in ("body", "mouth"):
        below = 1.0 - smoothstep(-0.02, 0.02, p.z - lip_z(p.y))
        behind = 1.0 - smoothstep(-1.85, -1.50, p.y)
        return below * behind
    return 0.0


jw = [jaw_weight(i) for i in range(len(co))]
for i, w in enumerate(jw):
    if w > 0:
        R = Matrix.Rotation(JAW_CLOSE * w, 3, 'X')
        me.vertices[i].co = JAW_PIVOT + R @ (co[i] - JAW_PIVOT)
me.update()
co = [v.co.copy() for v in me.vertices]
print("[prep] mouth closed:", sum(1 for w in jw if w > 0.5), "verts moved with the jaw")

# ----------------------------------------------------------------- 2. armature
ZC = 0.77
arm_data = bpy.data.armatures.new("FishRig")
arm = bpy.data.objects.new("FishRig", arm_data)
bpy.context.scene.collection.objects.link(arm)
arm.parent = root_node
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones


def bone(name, h, t, parent=None, deform=True):
    b = eb.new(name); b.head = V(h); b.tail = V(t)
    if parent:
        b.parent = eb[parent]
    b.use_deform = deform
    return b


bone("root", (0, -0.4, ZC), (0, -0.4, ZC + 0.5), deform=False)
bone("spine_01", (0, -0.4, ZC), (0, -1.2, ZC), "root")
bone("head", (0, -1.2, ZC), (0, -2.33, 0.80), "spine_01").use_connect = True
bone("jaw", tuple(JAW_PIVOT), (0, -2.30, 0.70), "head")
chain = [("spine_02", -0.4, 0.4), ("spine_03", 0.4, 1.1), ("spine_04", 1.1, 1.7),
         ("spine_05", 1.7, 2.3), ("caudal", 2.3, 3.0), ("caudal_tip", 3.0, 3.62)]
par = "root"
for n, y0, y1 in chain:
    bone(n, (0, y0, ZC), (0, y1, ZC), par)
    eb[n].use_connect = par != "root"; par = n
for sd, sx in (("L", 1), ("R", -1)):
    bone(f"operculum.{sd}", (sx * 0.30, -1.72, 0.72), (sx * 0.34, -1.42, 0.72), "head")
    bone(f"pectoral.{sd}", (sx * 0.30, -1.02, 0.42), (sx * 0.42, -0.45, 0.30), "spine_01")
    bone(f"pelvic.{sd}", (sx * 0.20, 0.22, 0.20), (sx * 0.55, 0.80, 0.03), "spine_03")
    bone(f"eye.{sd}", (sx * 0.21, -1.89, 0.85), (sx * 0.31, -1.89, 0.85), "head")
bone("dorsal", (0, 0.0, 1.36), (0, 0.80, 1.62), "spine_02")
bone("adipose", (0, 1.85, 1.10), (0, 2.20, 1.17), "spine_05")
bone("anal", (0, 1.62, 0.50), (0, 2.25, 0.28), "spine_04")
bpy.ops.object.mode_set(mode='OBJECT')
arm.data.display_type = 'STICK'
L = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm.data.bones}

# ----------------------------------------------------------------- weights
fish.parent = arm; fish.matrix_parent_inverse = Matrix()
mod = fish.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
for b in arm.data.bones:
    if b.use_deform:
        fish.vertex_groups.new(name=b.name)

CENTRES = [("head", -1.55), ("spine_01", -0.85), ("spine_02", 0.0), ("spine_03", 0.75),
           ("spine_04", 1.4), ("spine_05", 2.0), ("caudal", 2.65), ("caudal_tip", 3.35)]


def hat_weights(y):
    # piecewise-linear blend between neighbouring bone centres (constant bend rate, no plateaus)
    if y <= CENTRES[0][1]:
        return {CENTRES[0][0]: 1.0}
    if y >= CENTRES[-1][1]:
        return {CENTRES[-1][0]: 1.0}
    for (a, ya), (b, yb) in zip(CENTRES, CENTRES[1:]):
        if ya <= y <= yb:
            t = (y - ya) / (yb - ya)
            return {a: 1 - t, b: t}


def blend_radius(y):
    # half-width of the smoothing window: wide along the flexible trunk, zero over the rigid
    # head/mouth (y < -1.9) so jaw, gills and the closed mouth keep their exact weights
    return 0.32 * smoothstep(-1.9, -1.2, y)


def chain_weights(y, n=9):
    """Linear hat weights box-filtered along the body: each vertex blends over up to three
    spine bones, so tight bends curve evenly instead of kinking/bulging at the joints."""
    r = blend_radius(y)
    if r < 1e-3:
        return hat_weights(y)
    out = {}
    for k in range(n):
        s = y + r * (2 * (k + 0.5) / n - 1)
        for b, w in hat_weights(s).items():
            out[b] = out.get(b, 0.0) + w / n
    return out


def operc_weight(p):
    if abs(p.x) < 0.18 or not (0.40 < p.z < 1.02):
        return 0.0
    edge = -1.40 - 1.9 * (p.z - 0.72) ** 2      # curved rear edge of the gill cover
    w = smoothstep(-1.74, edge - 0.03, p.y) * (1 - smoothstep(edge - 0.01, edge + 0.02, p.y))
    w *= smoothstep(0.40, 0.50, p.z) * (1 - smoothstep(0.92, 1.02, p.z))
    return 0.9 * w


def anal_weight(p):
    # the anal fin is part of the body shell: a thin keel under the tail stock
    if not (1.55 < p.y < 2.35) or abs(p.x) > 0.12:
        return 0.0
    belly = 0.52 - 0.35 * smoothstep(1.6, 2.3, p.y)
    return smoothstep(0.0, 0.12, belly - p.z)


def fin_weights(k, p):
    lab = kind[k]; s = "L" if p.x > 0 else "R"
    if lab == "eye":
        return {f"eye.{s}": 1.0}
    if lab == "tooth_up":
        return {"head": 1.0}
    if lab == "tooth_lo":
        return {"jaw": 1.0}
    fins = {"pectoral": (f"pectoral.{s}", "spine_01"), "pelvic": (f"pelvic.{s}", "spine_03"),
            "dorsal": ("dorsal", None), "adipose": ("adipose", "spine_05")}
    if lab not in fins:
        return None
    fb, base_bone = fins[lab]
    h, t = L[fb]
    d = (p - h).dot((t - h).normalized()) / (t - h).length
    f = smoothstep(0.0, 0.45, d)
    base = {base_bone: 1.0} if base_bone else chain_weights(p.y)
    out = {n: w * (1 - f) for n, w in base.items()}
    out[fb] = out.get(fb, 0) + f
    return out


groups = fish.vertex_groups
for i, p in enumerate(co):
    k = island[i]
    ws = fin_weights(k, p)
    if ws is None:
        ws = chain_weights(p.y)
        if kind[k] in ("body", "mouth"):
            extra = {}
            if jw[i] > 0:
                extra["jaw"] = jw[i]
            if kind[k] == "body":
                o = operc_weight(p); a = anal_weight(p)
                if o > 0:
                    extra["operculum.L" if p.x > 0 else "operculum.R"] = o
                if a > 0:
                    extra["anal"] = 0.9 * a
            tot = sum(extra.values())
            if tot > 1:
                extra = {n: w / tot for n, w in extra.items()}; tot = 1
            ws = {n: w * (1 - tot) for n, w in ws.items()}
            ws.update(extra)
    for n, w in ws.items():
        if w > 1e-4:
            groups[n].add([i], w, 'REPLACE')

bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("[prep] saved", OUT)
