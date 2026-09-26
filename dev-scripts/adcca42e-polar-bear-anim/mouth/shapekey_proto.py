# exec'd by test2.py/test_zoom2.py (pre-lip rig): bake a relaxed closed mouth into a shape key
import bpy, math, os
import numpy as np
from mathutils import Quaternion, Vector as V
arm = bpy.data.objects["PolarBearRig"]; me = bpy.data.objects["PolarBear"]
pb = arm.pose.bones
JAW = math.radians(float(os.environ.get("SK_JAW", "-30")))
ITERS = int(os.environ.get("SK_ITERS", "40"))

def ramp(x, a, b):
    t = min(1.0, max(0.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)

# 1. closed-jaw geometry (only the jaw posed)
for p in pb: p.matrix_basis.identity()
j = pb["jaw"]; j.rotation_mode = 'QUATERNION'
r = j.bone.matrix_local.to_quaternion(); j.rotation_quaternion = r.inverted() @ Quaternion((1, 0, 0), JAW) @ r
bpy.context.view_layer.update()
ev = me.evaluated_get(bpy.context.evaluated_depsgraph_get()); m = ev.to_mesh()
P = np.array([v.co[:] for v in m.vertices]); ev.to_mesh_clear()
j.rotation_quaternion = Quaternion()
n = len(P)

# 2. weld UV-split duplicates so the seam smooths as one surface
key = np.round(np.array([v.co[:] for v in me.data.vertices]) * 2000).astype(np.int64)
_, uid, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
inv = inv.ravel(); U = len(uid)
Q = P[uid].copy()
nbr = [set() for _ in range(U)]
for e in me.data.edges:
    a, b = inv[e.vertices[0]], inv[e.vertices[1]]
    if a != b: nbr[a].add(b); nbr[b].add(a)
nbr = [np.array(sorted(s)) for s in nbr]

# 3. mask: the lip seam band around the mouth (rest coordinates), smooth falloff
R = np.array([v.co[:] for v in me.data.vertices])[uid]
mask = np.zeros(U)
for i, (x, y, z) in enumerate(R):
    if y > -6.5 or y < -7.95: continue
    ax = abs(x)
    # band hugging the lip line: from under the nose back to the corners
    q = (ax / 0.85) ** 2 + ((y + 7.25) / 0.72) ** 2 + ((z - 6.8) / 0.42) ** 2
    mask[i] = math.exp(-q * 1.0)
mask[mask < 0.03] = 0

jaw_i = me.vertex_groups["jaw"].index
JW = np.zeros(n)
for v in me.data.vertices:
    for g in v.groups:
        if g.group == jaw_i: JW[v.index] = g.weight
JWu = JW[uid]

# 3b. lip seam, measured by ray-casting the closed jaw (where outer skin switches from
# jaw- to skull-weighted): level under the nose, then curling up 2.7 mm into the corner.
SEAM = [(-7.8, 6.95), (-7.7, 6.90), (-7.6, 6.87), (-7.5, 6.82), (-7.4, 6.815), (-7.3, 6.80),
        (-7.2, 6.895), (-7.1, 6.985), (-7.0, 7.065), (-6.9, 7.035), (-6.8, 6.95), (-6.7, 6.9)]
def interp(tab, y):
    if y <= tab[0][0]: return tab[0][1]
    for (y0, v0), (y1, v1) in zip(tab, tab[1:]):
        if y <= y1: return v0 + (v1 - v0) * (y - y0) / (y1 - y0)
    return tab[-1][1]
# target: a real closed bear mouth runs back and slightly DOWN to a soft corner
TARGET = [(-7.8, 6.95), (-7.6, 6.90), (-7.3, 6.85), (-7.0, 6.80), (-6.85, 6.77), (-6.7, 6.78)]
OUT = float(os.environ.get("SK_OUT", "0.07"))
cnt = 0
for i in range(U):
    x, y, z = Q[i]
    if not (-7.95 < y < -6.6) or abs(x) > 1.15: continue
    zs, zt = interp(SEAM, y), interp(TARGET, y)
    d = z - zs
    fy = ramp(-y, 6.62, 6.8) * (1 - ramp(-y, 7.8, 7.95))
    fx = 1 - ramp(abs(x), 0.85, 1.15)
    carry = math.exp(-(d / 0.45) ** 2)          # region around the seam moves with it
    sig = 0.24 + 0.10 * (1 - ramp(-y, 7.05, 7.3))   # wider at the corner
    close = 1.0 * math.exp(-(d / sig) ** 2)     # the slit itself collapses onto the line
    Q[i][2] = z + fy * fx * ((zt - zs) * carry - d * close)
    # side lips meet flush: upper-lip hem in, lower lip out (blended by jaw weight -> no tearing)
    if y < -6.9 and abs(d) < 0.4 and abs(x) > 0.05:
        g = math.exp(-(d / 0.2) ** 2) * ramp(-y, 6.9, 7.1) * fx
        sgn = 1 if x > 0 else -1
        Q[i][0] = x + sgn * g * (-0.13 * (1 - JWu[i]) - 0.02 * JWu[i])
    # upper-lip hem: drawn down/back onto the lower lip so it rests on it (no shelf)
    if JWu[i] < 0.5 and 0 < d < 0.45:
        h = math.exp(-(d / 0.22) ** 2) * fy * fx * ramp(-y, 7.2, 7.5)
        Q[i][1] = Q[i][1] + 0.10 * h
        Q[i][2] = Q[i][2] - 0.05 * h
    # lower jaw: the sculpt's dropped jaw, rotated shut, hangs too deep; lift its underside
    # (one broad smooth field over the whole lower jaw, deeper points lifted more)
    if JWu[i] > 0.05 and z < zs and y < -5.6:
        depth = ramp(zs - z, 0.05, 1.8)
        f = ramp(JWu[i], 0.05, 0.95) * depth * ramp(-y, 5.6, 6.8) * (1 - ramp(abs(x), 0.9, 1.4))
        Q[i][2] = Q[i][2] + 0.34 * f
        Q[i][1] = Q[i][1] + 0.06 * f
    cnt += 1
print("[sk] reshaped", cnt)

# 3c. front upper lip: the sculpt has it lifted off the incisors (snarl); lower it onto the
# lower lip under the nose, keeping the nose itself (above z 7.25) where it is
import bmesh
bm = bmesh.new(); bm.from_mesh(me.data); bm.verts.ensure_lookup_table()
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
# separate small islands (the upper incisors) are tucked back and up behind the lip
isl = {}
seen = set()
for v in bm.verts:
    if v.index in seen: continue
    comp, stack = [], [v]; seen.add(v.index)
    while stack:
        a = stack.pop(); comp.append(a.co.copy())
        for e in a.link_edges:
            o = e.other_vert(a)
            if o.index not in seen: seen.add(o.index); stack.append(o)
    if len(comp) < 1000:
        c = sum(comp, V()) / len(comp)
        if -7.9 < c.y < -7.5 and abs(c.x) < 0.3 and 6.7 < c.z < 7.2:
            isl["teeth"] = c
bm.free()
tc = isl.get("teeth")
for i in range(U):
    x, y, z = Q[i]
    if tc is not None and abs(R[i][0]) < 0.25 and -7.8 < R[i][1] < -7.6 and 6.84 < R[i][2] < 7.1 and JWu[i] < 0.5 and False:
        pass
    if y < -7.45 and abs(x) < 0.5 and JWu[i] < 0.5 and 6.8 < z < 7.25:
        f = (1 - ramp(abs(x), 0.3, 0.5)) * ramp(-y, 7.45, 7.6)
        if z >= 7.0:   znew = 6.86 + (z - 7.0) * (7.25 - 6.86) / 0.25
        else:          znew = 6.86 - (7.0 - z) * 0.3
        Q[i][2] = z + f * (znew - z)
print("[sk] front lip lowered; teeth island", tc)


TEETH = [i for i in range(U) if -7.8 < R[i][1] < -7.62 and abs(R[i][0]) < 0.22 and 6.85 < R[i][2] < 7.08 and JWu[i] < 0.5]
LTEETH = [i for i in range(U) if -7.6 < R[i][1] < -6.9 and abs(R[i][0]) < 0.45 and 6.3 < R[i][2] < 6.62 and JWu[i] > 0.7 and abs(R[i][0]) > 0.05]
for i in LTEETH[:0]:
    pass
print("[sk] lower teeth sunk", len(LTEETH))
for i in TEETH:
    Q[i] = Q[i] + np.array([0.0, 0.15, 0.10])
print("[sk] teeth tucked", len(TEETH))

# 4. Taubin smoothing (no shrinking) restricted to the mask
lam, mu = 0.55, -0.58
act = np.nonzero(mask)[0]
for it in range(ITERS):
    for f in (lam, mu):
        new = Q.copy()
        for i in act:
            nb = nbr[i]
            if len(nb) == 0: continue
            new[i] = Q[i] + f * mask[i] * (Q[nb].mean(axis=0) - Q[i])
        Q = new

# 5. store as shape key (all duplicates of a welded vertex get the same position)
if not me.data.shape_keys: me.shape_key_add(name="Basis", from_mix=False)
sk = me.shape_key_add(name="MouthClosed", from_mix=False)
for vi in range(n):
    sk.data[vi].co = V(Q[inv[vi]])
sk.value = 1.0
print("[sk] mouth shape key baked; masked verts", len(act))
