"""Close the polar bear's mouth for good, in every animation.

Runs inside Blender on a file with 'PolarBearRig' / 'PolarBear' (after polar_bear_run.py and,
if wanted, polar_bear_walk.py):
    blender -b "Polar Bear Walking.blend" --python polar_bear_mouth.py

The model is sculpted mid-roar: jaw dropped, upper lip lifted off the teeth, lip corners
drawn up and back. Posing it shut with bones alone leaves the upper lip draped over the lower
one and the corners curling up. Instead the closed mouth is baked into the rigged mesh's rest
shape (the source 'Polar Bear.glb' is not touched), matched to photos of real polar bears:
  - jaw closed 30 degrees
  - lips meet edge to edge along one thin line that runs straight back from under the nose
    and droops slightly into a soft corner; the slit left by the sculpt is collapsed
  - side upper-lip hem drawn in so it no longer overhangs; front upper lip lowered back over
    the incisors; incisor tips tucked behind it
  - the lower jaw, which hangs too deep once rotated shut, lifted so it tucks under the muzzle
  - a Taubin relax (no shrinkage) over the lip band so the seam reads soft and rounded
UV-split duplicate vertices are moved together, so no seams open.
The jaw bone is then held at rest in every action (the mouth stays closed).
Safe to run more than once: it always rebuilds from the original open-mouth geometry
(kept in the mesh attribute 'rest_open', or read from 'Polar Bear.glb' next to this script).
"""
import bpy, math, os
import numpy as np
from mathutils import Quaternion, Vector as V

JAW_CLOSE = math.radians(-30)
RELAX_ITERS = 35
SNAP_SIG = 0.07          # half-width of the band snapped exactly onto the lip line, cm
GROOVE_DEPTH = 0.045     # how far the seam is creased inward, cm

# Optional extension scripts (';'-separated paths in MOUTH_EXT). Each may register functions
# in HOOKS["line"] (before the seam is snapped; may redefine line_z / SNAP_SIG / GROOVE_DEPTH),
# HOOKS["shape"] (after snapping, may edit Q) and HOOKS["color"] (may edit shade).
HOOKS = {"line": [], "shape": [], "color": []}
# By default the four refinements next to this script are used, in this order:
#   _1_corners  lip line level-to-slightly-down at the corners (no smile)
#   _2_crease   clean geometric edge where the lips meet
#   _3_lipband  crisp black lip edge along both lips (vertex colour)
#   _4_philtrum groove with dark skin between the nose and the upper lip
#   _5_lipflush upper and lower lips flush at the seam (no upper-lip overhang)
_here = os.path.dirname(bpy.data.filepath)       # the .blend sits next to these scripts
_default = ";".join(os.path.join(_here, f"polar_bear_mouth_{n}.py")
                    for n in ("1_corners", "2_crease", "3_lipband", "4_philtrum", "5_lipflush"))
for _p in [p for p in os.environ.get("MOUTH_EXT", _default).split(";") if p and os.path.exists(p)]:
    exec(open(_p, encoding="utf-8").read(), globals())
def run_hooks(name):
    for fn in HOOKS[name]:
        fn(globals())

arm = bpy.data.objects["PolarBearRig"]
me = bpy.data.objects["PolarBear"]
pb = arm.pose.bones

def ramp(x, a, b):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

def interp(tab, y):
    if y <= tab[0][0]:
        return tab[0][1]
    for (y0, v0), (y1, v1) in zip(tab, tab[1:]):
        if y <= y1:
            return v0 + (v1 - v0) * (y - y0) / (y1 - y0)
    return tab[-1][1]

# ---------------------------------------------------------------- undo the earlier lip-bone rig
lip_groups = [g for g in me.vertex_groups if g.name.startswith("lip_")]
if lip_groups:
    ids = {g.index for g in lip_groups}
    for v in me.data.vertices:
        t = sum(g.weight for g in v.groups if g.group in ids)
        if t > 0:
            for g in v.groups:
                if g.group not in ids:
                    g.weight /= max(1e-6, 1 - t)       # weights were scaled by (1 - t)
    for g in lip_groups:
        me.vertex_groups.remove(g)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    for b in [b for b in arm.data.edit_bones if b.name.startswith("lip_")]:
        arm.data.edit_bones.remove(b)
    bpy.ops.object.mode_set(mode='OBJECT')
    print("[mouth] removed old lip bones")

def fcurve_bags(action):
    for layer in action.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                yield cb

# ---------------------------------------------------------------- original open geometry
def open_rest():
    att = me.data.attributes.get("rest_open")
    if att:
        buf = np.zeros(len(me.data.vertices) * 3); att.data.foreach_get("vector", buf)
        return buf.reshape(-1, 3)
    if not me.get("mouth_closed"):
        return np.array([v.co[:] for v in me.data.vertices])
    src = os.path.join(os.path.dirname(bpy.data.filepath), "Polar Bear.glb")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=src)
    new = [o for o in bpy.data.objects if o not in before]
    o = next(o for o in new if o.type == 'MESH')
    M = o.matrix_world.copy()
    co = np.array([(M @ v.co)[:] for v in o.data.vertices]) * 100
    for x in new:
        bpy.data.objects.remove(x)
    assert len(co) == len(me.data.vertices)
    return co

OPEN = open_rest()
if "rest_open" not in me.data.attributes:
    att = me.data.attributes.new("rest_open", 'FLOAT_VECTOR', 'POINT')
    att.data.foreach_set("vector", OPEN.ravel())
for vi, v in enumerate(me.data.vertices):
    v.co = V(OPEN[vi])
if me.data.shape_keys:
    for kb in me.data.shape_keys.key_blocks:
        for vi in range(len(OPEN)):
            kb.data[vi].co = V(OPEN[vi])
me.data.update()

# ---------------------------------------------------------------- bake the closed mouth
if True:
    saved_action = arm.animation_data.action if arm.animation_data else None
    if arm.animation_data:
        arm.animation_data.action = None
    for p in pb:
        p.matrix_basis.identity()
    jaw = pb["jaw"]; jaw.rotation_mode = 'QUATERNION'
    r = jaw.bone.matrix_local.to_quaternion()
    jaw.rotation_quaternion = r.inverted() @ Quaternion((1, 0, 0), JAW_CLOSE) @ r
    bpy.context.view_layer.update()
    ev = me.evaluated_get(bpy.context.evaluated_depsgraph_get()); m = ev.to_mesh()
    P = np.array([v.co[:] for v in m.vertices]); ev.to_mesh_clear()
    jaw.rotation_quaternion = Quaternion()
    n = len(P)

    # weld UV-split duplicates so each surface point moves as one
    rest = np.array([v.co[:] for v in me.data.vertices])
    _, uid, inv = np.unique(np.round(rest * 2000).astype(np.int64), axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel(); U = len(uid)
    Q = P[uid].copy(); R = rest[uid]
    nbr = [set() for _ in range(U)]
    for e in me.data.edges:
        a, b = inv[e.vertices[0]], inv[e.vertices[1]]
        if a != b:
            nbr[a].add(b); nbr[b].add(a)
    nbr = [np.array(sorted(s)) for s in nbr]
    jaw_i = me.vertex_groups["jaw"].index
    JW = np.zeros(n)
    for v in me.data.vertices:
        for g in v.groups:
            if g.group == jaw_i:
                JW[v.index] = g.weight
    JWu = JW[uid]

    # lip seam of the jaw-closed sculpt (ray-cast: where the skin switches from jaw- to
    # skull-weighted) and the target line of a real closed bear mouth
    SEAM = [(-7.8, 6.95), (-7.7, 6.90), (-7.6, 6.87), (-7.5, 6.82), (-7.4, 6.815), (-7.3, 6.80),
            (-7.2, 6.895), (-7.1, 6.985), (-7.0, 7.065), (-6.9, 7.035), (-6.8, 6.95), (-6.7, 6.9)]
    TARGET = [(-7.8, 6.95), (-7.6, 6.90), (-7.3, 6.85), (-7.0, 6.80), (-6.85, 6.77), (-6.7, 6.78)]
    for i in range(U):
        x, y, z = Q[i]
        if not (-7.95 < y < -5.6) or abs(x) > 1.4:
            continue
        zs = interp(SEAM, y)
        d = z - zs
        fx = 1 - ramp(abs(x), 0.85, 1.15)
        if y < -6.6 and abs(x) <= 1.15:
            zt = interp(TARGET, y)
            fy = ramp(-y, 6.62, 6.8) * (1 - ramp(-y, 7.8, 7.95))
            carry = math.exp(-(d / 0.45) ** 2)                 # skin around the seam follows it
            sig = 0.24 + 0.10 * (1 - ramp(-y, 7.05, 7.3))      # wider toward the corner
            close = math.exp(-(d / sig) ** 2)                  # the slit collapses onto the line
            Q[i][2] = z + fy * fx * ((zt - zs) * carry - d * close)
            if y < -6.9 and abs(d) < 0.4 and abs(x) > 0.05:    # side lips meet flush
                g = math.exp(-(d / 0.2) ** 2) * ramp(-y, 6.9, 7.1) * fx
                Q[i][0] = x + math.copysign(1, x) * g * (-0.13 * (1 - JWu[i]) - 0.02 * JWu[i])
            if JWu[i] < 0.5 and 0 < d < 0.45:                  # upper-lip hem rests on the lower lip
                h = math.exp(-(d / 0.22) ** 2) * fy * fx * ramp(-y, 7.2, 7.5)
                Q[i][1] += 0.10 * h
                Q[i][2] -= 0.05 * h
        if JWu[i] > 0.05 and z < zs:                           # lower jaw tucked up under the muzzle
            f = ramp(JWu[i], 0.05, 0.95) * ramp(zs - z, 0.05, 1.8) * ramp(-y, 5.6, 6.8) * \
                (1 - ramp(abs(x), 0.9, 1.4))
            Q[i][2] += 0.34 * f
            Q[i][1] += 0.06 * f
    for i in range(U):                                         # front upper lip down over the incisors
        x, y, z = Q[i]
        if y < -7.45 and abs(x) < 0.5 and JWu[i] < 0.5 and 6.8 < z < 7.25:
            f = (1 - ramp(abs(x), 0.3, 0.5)) * ramp(-y, 7.45, 7.6)
            znew = 6.86 + (z - 7.0) * (7.25 - 6.86) / 0.25 if z >= 7.0 else 6.86 - (7.0 - z) * 0.3
            Q[i][2] = z + f * (znew - z)
    for i in range(U):                                         # incisor tips tucked behind the lip
        if -7.8 < R[i][1] < -7.62 and abs(R[i][0]) < 0.22 and 6.85 < R[i][2] < 7.08 and JWu[i] < 0.5:
            Q[i] += np.array([0.0, 0.15, 0.10])

    # Taubin relax over the lip band (rounds the seam without shrinking the muzzle)
    mask = np.zeros(U)
    for i, (x, y, z) in enumerate(R):
        if -7.95 <= y <= -6.5:
            mask[i] = math.exp(-((abs(x) / 0.85) ** 2 + ((y + 7.25) / 0.72) ** 2 + ((z - 6.8) / 0.42) ** 2))
    mask[mask < 0.03] = 0
    active = np.nonzero(mask)[0]
    for _ in range(RELAX_ITERS):
        for f in (0.55, -0.58):
            new = Q.copy()
            for i in active:
                if len(nbr[i]):
                    new[i] = Q[i] + f * mask[i] * (Q[nbr[i]].mean(axis=0) - Q[i])
            Q = new

    # crisp lip line: every point on the seam is snapped onto ONE smooth curve (no wobble),
    # and the seam is creased slightly inward so shading draws a clean continuous line
    def line_z(y):
        u = min(1.15, max(0.0, y + 7.8))
        return 6.95 - 0.23 * u + 0.06 * u * u
    run_hooks("line")
    for i in range(U):
        x, y, z = Q[i]
        if not (-7.9 < y < -6.6) or abs(x) > 1.1:
            continue
        d = z - line_z(y)
        if abs(d) > 0.2:
            continue
        fy = ramp(-y, 6.62, 6.78) * (1 - ramp(-y, 7.82, 7.9))
        fx = 1 - ramp(abs(x), 0.9, 1.1)
        snap = fy * fx * math.exp(-(d / SNAP_SIG) ** 2)
        flat = fy * fx * math.exp(-(d / 0.16) ** 2)
        # squash the band around the seam toward the line, the seam itself exactly onto it
        Q[i][2] = line_z(y) + d * (1 - 0.55 * flat) * (1 - snap)
        groove = GROOVE_DEPTH * snap
        front = 1 - ramp(abs(x), 0.15, 0.4)
        Q[i][0] -= math.copysign(1, x) * groove * (1 - front)
        Q[i][1] += groove * front

    run_hooks("shape")

    # write as the new rest shape
    coords = Q[inv]
    if me.data.shape_keys:
        for kb in me.data.shape_keys.key_blocks:
            for vi in range(n):
                kb.data[vi].co = V(coords[vi])
    for vi, v in enumerate(me.data.vertices):
        v.co = V(coords[vi])
    me.data.update()
    me["mouth_closed"] = True
    if arm.animation_data:
        arm.animation_data.action = saved_action
    print("[mouth] closed mouth baked into the rest shape")

    # dark lip line: polar bears have black lip skin, which is what draws the clean line along
    # the closed mouth. Stored as a vertex colour (white = unchanged) multiplied into the fur.
    LINE_W = 0.045                      # half-width of the dark line, cm
    shade = np.ones(U)
    for i in range(U):
        x, y, z = Q[i]
        if not (-7.9 < y < -6.6) or abs(x) > 1.1:
            continue
        d = z - line_z(y)
        fy = ramp(-y, 6.64, 6.8) * (1 - ramp(-y, 7.84, 7.9))
        fx = 1 - ramp(abs(x), 0.95, 1.1)
        dark = fy * fx * math.exp(-(d / LINE_W) ** 4)                 # crisp edges
        soft = fy * fx * math.exp(-(d / (3 * LINE_W)) ** 2) * 0.35     # thin dark lip rim
        shade[i] = 1 - max(0.88 * dark, soft)
    run_hooks("color")
    col = me.data.color_attributes.get("LipLine") or         me.data.color_attributes.new("LipLine", 'FLOAT_COLOR', 'POINT')
    rgba = np.repeat(shade[inv], 4).reshape(-1, 4); rgba[:, 3] = 1
    col.data.foreach_set("color", rgba.ravel())
    me.data.color_attributes.active_color = col
    mat = me.data.materials[0]; nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    if "LipLine" not in nt.nodes:
        tex = bsdf.inputs["Base Color"].links[0].from_node
        ca = nt.nodes.new('ShaderNodeVertexColor'); ca.name = "LipLine"; ca.layer_name = "LipLine"
        mul = nt.nodes.new('ShaderNodeMix'); mul.name = "LipLineMul"
        mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs["Factor"].default_value = 1.0
        nt.links.new(tex.outputs["Color"], mul.inputs["A"])
        nt.links.new(ca.outputs["Color"], mul.inputs["B"])
        nt.links.new(mul.outputs["Result"], bsdf.inputs["Base Color"])
    print("[mouth] lip line painted")

# ---------------------------------------------------------------- jaw at rest in every action
jaw = pb["jaw"]
jaw.rotation_mode = 'QUATERNION'
active_action = arm.animation_data.action
for action in list(bpy.data.actions):
    if not action.layers:
        continue
    arm.animation_data.action = action
    for cb in fcurve_bags(action):
        for fc in [fc for fc in cb.fcurves if fc.data_path.startswith(('pose.bones["jaw"]', 'pose.bones["lip_'))]:
            cb.fcurves.remove(fc)
    f0, f1 = (int(round(x)) for x in action.frame_range)
    jaw.rotation_quaternion = Quaternion()
    for f in (f0, f1):
        jaw.keyframe_insert("rotation_quaternion", frame=f)
    print(f"[mouth] {action.name}: jaw held closed, frames {f0}-{f1}")
arm.animation_data.action = active_action
jaw.rotation_quaternion = Quaternion()
