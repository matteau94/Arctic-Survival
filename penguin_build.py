"""Model, texture and rig an emperor penguin for Artic-Survival (v2).

    blender -b --python penguin_build.py        (writes Penguin_Rigged.blend + textures/Penguin_*.png)

Real-world metres, standing on z = 0, facing -Y (so +X is its left side), ~1.0 m tall.

1. Mesh 'Penguin' (one object, one material, like the fox / bear / fish), built from lofts:
     body     trunk + neck + head as one ring loft with its own cylindrical UV layout
              (seam down the back, ~70 % of the texture) for high feather density
     beak     upper and lower mandible as separate lofts so the jaw can open; a tongue
              sits inside the lower mandible and the mouth lining is painted pink
     flippers flat tapered paddles with a blunt leading edge
     feet     three clawed toes joined by partial webs, heel pad
     tail     stiff wedge plus a fan of spiky tail feathers
     eyes     small spheres with iris / pupil painted on
   Every part carries a 'part' point attribute used when texturing and weighting.
2. Textures (2048^2, PBR like the other assets). Object-space position / normal / part /
   noise / AO are baked, then everything is painted in numpy:
     - thousands of individual overlapping feathers (per-feather size, colour, gloss and
       height), fine velvety feathers on the head, tiny scale feathers on the flippers
     - emperor plumage: black hood, slate-blue back with glossy feather tips, white belly
       with soft down and a soiled underside, broad orange ear patches fading into a golden
       breast, orange-pink mandible plate, dark brown iris, pink mouth lining
     - the tangent-space normal map is derived from the painted height field
     textures/Penguin_BaseColor.png, Penguin_ORM.png (R=AO, G=roughness, B=metal), Penguin_Normal.png
3. Rig 'PenguinRig':
     root (no deform)
       body > spine > chest > neck > head > jaw
                          chest > flipper_upper.L/R > flipper_lower.L/R
              body > tail, thigh.L/R > shin.L/R > foot.L/R
   Weights are computed per part: smooth blends up the trunk, lower belly partly on the
   thighs, flippers blend from the chest at the root, beak/eyes rigid on head/jaw.
"""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector as V, Matrix
from mathutils.bvhtree import BVHTree

DIR = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
# PENG_OUTDIR / PENG_RES let test builds go elsewhere at lower resolution
_od = os.environ.get("PENG_OUTDIR")
OUT = os.path.join(_od or DIR, "Penguin_Rigged.blend")
TEX = os.path.join(_od, "textures") if _od else os.path.join(DIR, "textures")
os.makedirs(TEX, exist_ok=True)
RES = int(os.environ.get("PENG_RES", "2048"))
BODY_U = 0.70                      # body UVs fill u in [0, BODY_U]; other parts pack beside it

BODY, BEAK_UP, BEAK_LO, FLIPPER, FOOT, EYE, TAIL, MOUTH = range(8)
CLAW = FOOT + 0.5


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, dtype=float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def sstep(e0, e1, x):
    return float(smoothstep(e0, e1, x))


def hermite(keys, t):
    """Smooth interpolation through (t, value) keys (finite-difference tangents)."""
    n = len(keys)
    if t <= keys[0][0]:
        return keys[0][1]
    if t >= keys[-1][0]:
        return keys[-1][1]

    def slope(i):
        a, b = keys[max(i - 1, 0)], keys[min(i + 1, n - 1)]
        return (b[1] - a[1]) / (b[0] - a[0])
    for i in range(n - 1):
        (t0, v0), (t1, v1) = keys[i], keys[i + 1]
        if t <= t1:
            h = t1 - t0; u = (t - t0) / h
            return ((2*u**3 - 3*u**2 + 1) * v0 + (u**3 - 2*u**2 + u) * h * slope(i)
                    + (-2*u**3 + 3*u**2) * v1 + (u**3 - u**2) * h * slope(i + 1))


bpy.ops.wm.read_factory_settings(use_empty=True)
for o in list(bpy.data.objects):          # startup add-ons may drop objects in the scene
    bpy.data.objects.remove(o)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'


# ======================================================================= mesh helpers
def tag_part(me, part):
    att = me.attributes.get("part") or me.attributes.new("part", 'FLOAT', 'POINT')
    att.data.foreach_set("value", [float(part)] * len(me.vertices))


def mesh_from_rings(name, rings, part, cap_start=None, cap_end=None, uv=None):
    """Quad loft through closed rings (equal vertex counts); caps are pole points.
    uv(k, j) -> (u, v) for ring k, ring vertex j (j may equal n on the wrap-around)."""
    verts, faces, fuv = [], [], []
    n = len(rings[0]); K = len(rings)
    for r in rings:
        verts.extend(r)
    for k in range(K - 1):
        a, b = k * n, (k + 1) * n
        for j in range(n):
            j2 = (j + 1) % n
            faces.append((a + j, a + j2, b + j2, b + j))
            if uv:
                fuv.append((uv(k, j), uv(k, j + 1), uv(k + 1, j + 1), uv(k + 1, j)))
    if cap_start is not None:
        verts.append(cap_start); p = len(verts) - 1
        for j in range(n):
            faces.append((p, (j + 1) % n, j))
            if uv:
                u0 = uv(0, j + 0.5)
                fuv.append(((u0[0], 0.0), uv(0, j + 1), uv(0, j)))
    if cap_end is not None:
        verts.append(cap_end); p = len(verts) - 1; a = (K - 1) * n
        for j in range(n):
            faces.append((p, a + j, a + (j + 1) % n))
            if uv:
                u0 = uv(K - 1, j + 0.5)
                fuv.append(((u0[0], 1.0), uv(K - 1, j), uv(K - 1, j + 1)))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    if uv:
        lay = me.uv_layers.new(name="UVMap")
        flat = [c for f in fuv for co in f for c in co]
        lay.data.foreach_set("uv", flat)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)     # mirrored parts come out inside-out
    bm.to_mesh(me); bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    tag_part(me, part)
    return ob


def activate(ob):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)


def subdivide(ob, levels):
    activate(ob)
    m = ob.modifiers.new("Subsurf", 'SUBSURF')
    m.levels = m.render_levels = levels
    m.uv_smooth = 'PRESERVE_BOUNDARIES'
    bpy.ops.object.modifier_apply(modifier=m.name)
    for p in ob.data.polygons:
        p.use_smooth = True


def blob(name, centre, radii, part, segs=(16, 10)):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=1.0,
                              matrix=Matrix.Translation(centre) @ Matrix.Diagonal((*radii, 1)))
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob)
    tag_part(me, part)
    for p in me.polygons:
        p.use_smooth = True
    return ob


# ======================================================================= 1. body
# Side silhouette as front line / back line (y) plus half width, per height z.
# Heavy low belly, puffed breast, shoulders where the flippers hang, a thick neck leaning
# forward, a slight chin recess under the bill, forehead sloping up from the bill base,
# rounded crown and occiput.
#          z      front y  back y   half width
SIL = [(0.020, -0.020,  0.050,  0.040),
       (0.040, -0.104,  0.142,  0.112),
       (0.085, -0.178,  0.188,  0.170),
       (0.160, -0.216,  0.196,  0.199),
       (0.250, -0.231,  0.188,  0.208),
       (0.350, -0.230,  0.175,  0.204),
       (0.450, -0.225,  0.158,  0.193),
       (0.550, -0.219,  0.138,  0.176),
       (0.630, -0.207,  0.116,  0.157),
       (0.690, -0.190,  0.096,  0.138),
       (0.745, -0.170,  0.068,  0.110),
       (0.790, -0.153,  0.036,  0.087),
       (0.818, -0.145,  0.024,  0.078),
       (0.845, -0.139,  0.034,  0.085),
       (0.872, -0.146,  0.041,  0.083),
       (0.900, -0.137,  0.044,  0.078),
       (0.928, -0.119,  0.041,  0.072),
       (0.952, -0.097,  0.032,  0.064),
       (0.970, -0.076,  0.018,  0.052),
       (0.982, -0.058,  0.002,  0.036),
       (0.989, -0.044, -0.012,  0.018)]
# z, half width (x), front depth (-y), back depth (+y), centre y
PROFILE = []
for z_, yf_, yb_, hw_ in SIL:
    yc_ = 0.5 * (yf_ + yb_)
    PROFILE.append((z_, hw_, yc_ - yf_, yb_ - yc_, yc_))
KEYS = [[(r[0], r[i]) for r in PROFILE] for i in range(1, 5)]


def prof(z):
    return [hermite(k, z) for k in KEYS]


def headness(z):
    return sstep(0.80, 0.86, z)


def ring_point(z, th):
    """th = 0 straight ahead (-Y), +pi/2 the left (+X) flank."""
    hw, fr, bk, yc = prof(z)
    c = math.cos(th)
    depth = fr if c >= 0 else bk
    s = math.sin(th)
    x = hw * math.copysign(abs(s) ** 0.9, s)          # slightly squarer than an ellipse
    y = yc - depth * math.copysign(abs(c) ** 0.95, c)
    if c > 0:
        # the face narrows toward the bill; the breast is a touch flatter across the front
        h = headness(z)
        x *= 1.0 - (0.30 * h) * c ** 2 + (0.04 * (1 - h) * sstep(0.45, 0.75, z)) * c ** 2
    return V((x, y, z))


NSEG, NR = 32, 36
z0, z1 = PROFILE[0][0], PROFILE[-1][0]
zs = [z0 + (z1 - z0) * ((0.5 - 0.5 * math.cos(math.pi * i / (NR - 1))) * 0.6 + 0.4 * i / (NR - 1))
      for i in range(NR)]
# seam straight down the back: j = 0 at th = pi
rings = [[ring_point(z, math.pi + 2 * math.pi * j / NSEG) for j in range(NSEG)] for z in zs]
# v by arc length along the flank so feathers are not stretched
arc = [0.0]
prev = ring_point(zs[0], math.pi / 2)
for z in zs[1:]:
    p = ring_point(z, math.pi / 2); arc.append(arc[-1] + (p - prev).length); prev = p
pad = 0.035
vv = [pad + (1 - 2 * pad) * a / arc[-1] for a in arc]
body = mesh_from_rings("Body", rings, BODY, cap_start=V((0, PROFILE[0][4], 0.012)), cap_end=V((0, PROFILE[-1][4], z1 + 0.004)),
                       uv=lambda k, j: (j / NSEG, vv[k]))
subdivide(body, 2)

bvh_body = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())


def surface(origin, direction):
    hit, nrm, _, _ = bvh_body.ray_cast(V(origin), V(direction).normalized())
    return hit, nrm


# ======================================================================= 2. beak + tongue
beak_base, _ = surface((0, -0.5, 0.872), (0, 1, 0))
BEAK_DIR = V((0, -1, -0.20)).normalized()
BEAK_UPV = V((0, -0.20, 1)).normalized()
BEAK_UPV = (BEAK_UPV - BEAK_UPV.dot(BEAK_DIR) * BEAK_DIR).normalized()
BEAK_ORIGIN = beak_base + BEAK_DIR * -0.020          # start inside the head
BEAK_LEN = 0.122


def beak_centre(u, L):
    return BEAK_ORIGIN + BEAK_DIR * (L * u) - BEAK_UPV * (0.019 * u ** 2.3)


def beak_rings(upper):
    rs = []
    n = 18
    L = BEAK_LEN if upper else BEAK_LEN * 0.94
    for i in range(20):
        u = i / 19
        c = beak_centre(u, L)
        w = 0.0185 * (1 - u) ** 0.8 + 0.0012
        if upper:
            h = 0.0215 * (1 - u) ** 0.95 + 0.0015
            h *= 1.0 + 0.3 * sstep(0.82, 1.0, u)       # slight hook at the tip
        else:
            h = 0.0135 * (1 - u) ** 0.9 + 0.0012
        if i == 0:                                  # flare into the face
            w *= 1.3; h *= 1.25
        ring = []
        for j in range(n):
            ph = 2 * math.pi * j / n
            sx, sy = math.cos(ph), math.sin(ph)
            outer = sy > 0 if upper else sy < 0      # the mouth side is nearly flat
            up = h * sy if outer else 0.10 * h * sy
            ring.append(c + V((w * sx, 0, 0)) + BEAK_UPV * up)
        rs.append(ring)
    return rs, beak_centre(1.012, L)


r_up, tip_up = beak_rings(True)
r_lo, tip_lo = beak_rings(False)
beak_up = mesh_from_rings("BeakUpper", r_up, BEAK_UP, cap_start=BEAK_ORIGIN - BEAK_DIR * 0.004, cap_end=tip_up)
beak_lo = mesh_from_rings("BeakLower", r_lo, BEAK_LO, cap_start=BEAK_ORIGIN - BEAK_DIR * 0.004, cap_end=tip_lo)
subdivide(beak_up, 1); subdivide(beak_lo, 1)
JAW_PIVOT = BEAK_ORIGIN + BEAK_DIR * 0.012 - BEAK_UPV * 0.004
JAW_TIP = tip_lo

rs = []
for i in range(10):
    u = i / 9
    c = beak_centre(0.08 + 0.52 * u, BEAK_LEN * 0.94) + BEAK_UPV * 0.0009
    w = 0.0085 * (1 - u) ** 0.6 + 0.001
    h = 0.0022 * (1 - u) + 0.0006
    rs.append([c + V((w * math.cos(2 * math.pi * j / 10), 0, 0)) + BEAK_UPV * (h * math.sin(2 * math.pi * j / 10))
               for j in range(10)])
tongue = mesh_from_rings("Tongue", rs, MOUTH, cap_start=beak_centre(0.05, BEAK_LEN), cap_end=beak_centre(0.62, BEAK_LEN * 0.94))
subdivide(tongue, 1)

# ======================================================================= 3. eyes
eyes = []
EYE_R = 0.0092
for s in (1, -1):
    d = V((s * math.sin(1.10), -math.cos(1.10), 0.06)).normalized()
    hit, nrm = surface(V((0, prof(0.884)[3], 0.884)) + d * 0.4, -d)
    ctr = hit - nrm * EYE_R * 0.40
    eyes.append((blob("Eye", ctr, (EYE_R,) * 3, EYE, (20, 12)), ctr, nrm.copy()))

# ======================================================================= 4. flippers
FLIP_LEN = 0.355
FLIP_TILT = math.radians(17)          # out from the flank
FLIP_SWEEP = math.radians(9)          # tip slightly back
flip_frames = {}


def flipper(s):
    """The flipper hangs along the flank: its centreline is laid on the body surface
    (raycast) plus a gap that grows toward the tip, so it never sinks into the belly."""
    zc = 0.690
    yc_ = prof(zc)[3] + 0.022
    hit, _ = surface((s * 0.5, yc_, zc), (-s, 0, 0))
    shoulder = V((hit.x - s * 0.010, yc_, zc))
    NS = 24
    cl = []
    for i in range(NS):
        u = i / (NS - 1)
        zz = zc - FLIP_LEN * 0.955 * u
        yy = yc_ + FLIP_LEN * math.sin(FLIP_SWEEP) * u
        h_, _ = surface((s * 0.6, yy, zz), (-s, 0, 0))
        gap = 0.008 * sstep(0.0, 0.25, u) + 0.009 * u ** 1.5 - 0.010 * (1 - sstep(0.0, 0.12, u))
        cl.append(V((h_.x + s * gap, yy, zz)))
    cl[0] = shoulder.copy()
    # re-space by arc length so the flipper keeps its length
    L = [0.0]
    for a, b in zip(cl, cl[1:]):
        L.append(L[-1] + (b - a).length)
    scale = FLIP_LEN / L[-1]

    def at(u):
        d = u * L[-1]
        for k in range(NS - 1):
            if d <= L[k + 1] or k == NS - 2:
                f = (d - L[k]) / max(L[k + 1] - L[k], 1e-9)
                return cl[k].lerp(cl[k + 1], min(max(f, 0), 1))
    down = (cl[-1] - cl[0]).normalized()
    rs = []
    WK = [(0.0, 0.040), (0.12, 0.084), (0.33, 0.100), (0.62, 0.080), (0.86, 0.046), (1.0, 0.012)]
    for i in range(24):
        u = i / 23
        w = hermite(WK, u)
        t = 0.018 * (1 - u) + 0.0045 - 0.006 * (1 - sstep(0.0, 0.10, u))
        c = at(u)
        dl = (at(min(u + 0.03, 1)) - at(max(u - 0.03, 0))).normalized()
        fwd = V((0, -1, 0)); fwd = (fwd - fwd.dot(dl) * dl).normalized()
        thick = dl.cross(fwd).normalized() * s
        c = c + fwd * (0.012 * (1 - u))
        ring = []
        n = 18
        for j in range(n):
            ph = 2 * math.pi * j / n
            a, b = math.cos(ph), math.sin(ph)
            lead = a > 0                                    # blunt leading edge, thin trailing edge
            ww = w * (0.40 if lead else 0.60)
            tt = t * (1.0 if lead else 0.55 + 0.45 * (1 + a))
            ring.append(c + fwd * (ww * a) + thick * (tt * b * 0.5))
        rs.append(ring)
    tip = at(1.0) + down * (FLIP_LEN * 0.025)
    fwd = V((0, -1, 0)); fwd = (fwd - fwd.dot(down) * down).normalized()
    thick = down.cross(fwd).normalized() * s
    ob = mesh_from_rings("Flipper", rs, FLIPPER, cap_start=shoulder - down * 0.010 - thick * 0.006, cap_end=tip)
    subdivide(ob, 1)
    flip_frames[s] = (shoulder, down, fwd, thick)
    flip_joints[s] = (shoulder, at(0.45), at(1.0))
    return ob


flip_joints = {}
flippers = [flipper(1), flipper(-1)]

# ======================================================================= 5. feet
LEG = {}   # side -> dict of joints


def foot(s):
    ankle = V((s * 0.076, -0.004, 0.030))
    heel = V((s * 0.076, 0.004, 0.015))
    parts = [blob("Heel", heel + V((0, -0.016, 0)), (0.030, 0.040, 0.016), FOOT)]
    yaw = math.radians(6)
    toe_lines = []
    for ang, ln in ((-15, 0.050), (0, 0.060), (15, 0.052)):
        a = math.radians(ang) + yaw
        d = V((math.sin(a) * s, -math.cos(a), 0))
        base = heel + V((0, -0.018, 0)) + d * 0.004
        side = V((-d.y, d.x, 0)).normalized()
        rs = []; line = []
        for i in range(12):
            u = i / 11
            r = 0.0118 * (1 - u) + 0.0048
            c = base + d * (ln * u)
            c.z = r * 0.85 + 0.0015 + 0.0035 * math.sin(math.pi * u)   # knuckle arch
            line.append(c.copy())
            # knobbly toe pads: the radius swells at each joint
            r *= 1.0 + 0.10 * math.cos(u * 3 * 2 * math.pi)
            rs.append([c + side * (r * math.cos(2 * math.pi * j / 12)) + V((0, 0, r * 0.8 * math.sin(2 * math.pi * j / 12)))
                       for j in range(12)])
        toe_lines.append(line)
        tipc = base + d * ln; tipc.z = 0.0042 * 0.85 + 0.0015
        parts.append(mesh_from_rings("Toe", rs, FOOT, cap_start=base - d * 0.003, cap_end=tipc + d * 0.004))
        cb = tipc + d * 0.002
        rs = []
        for i in range(6):
            u = i / 5
            r = 0.0038 * (1 - u) + 0.0004
            c = cb + d * (0.008 * u); c.z = cb.z - 0.0030 * u ** 1.5
            rs.append([c + side * (r * math.cos(2 * math.pi * j / 8)) + V((0, 0, r * 0.7 * math.sin(2 * math.pi * j / 8)))
                       for j in range(8)])
        claw = mesh_from_rings("Claw", rs, CLAW, cap_start=cb - d * 0.002, cap_end=cb + d * 0.0095 - V((0, 0, 0.0032)))
        parts.append(claw)
    # partial webs between neighbouring toes (to ~60 % of their length, scalloped edge)
    for A, B in ((toe_lines[0], toe_lines[1]), (toe_lines[1], toe_lines[2])):
        verts, faces = [], []
        cols = 8
        for i in range(cols):
            ia = min(int(i / (cols - 1) * 7), 11)
            reach = 1.0 - 0.35 * math.sin(math.pi * i / (cols - 1))     # scallop
            pa, pb = A[ia], B[ia]
            m = (pa + pb) / 2
            for k, q in enumerate((pa, m.lerp(pa, reach) if i else m, pb)):
                verts.append((q.x, q.y, 0.004 + 0.002 * (k == 1)))
        for i in range(cols - 1):
            for k in range(2):
                a = i * 3 + k
                faces.append((a, a + 1, a + 4, a + 3))
        me = bpy.data.meshes.new("Web"); me.from_pydata(verts, [], faces); me.update()
        ob = bpy.data.objects.new("Web", me); scene.collection.objects.link(ob)
        tag_part(me, FOOT)
        activate(ob)
        sol = ob.modifiers.new("Solidify", 'SOLIDIFY'); sol.thickness = 0.0016; sol.offset = 0
        bpy.ops.object.modifier_apply(modifier=sol.name)
        parts.append(ob)
    for ob in parts:
        subdivide(ob, 1)
    LEG[s] = dict(hip=V((s * 0.070, 0.012, 0.200)), knee=V((s * 0.075, -0.036, 0.110)),
                  ankle=ankle, toe=V((s * 0.084, -0.082, 0.012)))
    return parts


feet = foot(1) + foot(-1)

# ======================================================================= 6. tail
rs = []
for i in range(10):
    u = i / 9
    c = V((0, 0.118 + 0.100 * u, 0.112 - 0.070 * u - 0.01 * u * u))
    w = 0.052 * (1 - u) + 0.018
    t = 0.021 * (1 - u) + 0.005
    rs.append([c + V((w * math.cos(2 * math.pi * j / 12), 0, t * math.sin(2 * math.pi * j / 12)))
               for j in range(12)])
tail_parts = [mesh_from_rings("Tail", rs, TAIL, cap_start=V((0, 0.10, 0.12)), cap_end=V((0, 0.222, 0.030)))]
# stiff, spiky tail feathers fanning out of the wedge
for k in range(7):
    a = (k - 3) / 3.0
    root = V((0.016 * a, 0.185, 0.050 - 0.004 * abs(a)))
    d = V((0.30 * a, 1.0, -0.42 - 0.05 * abs(a))).normalized()
    ln = 0.062 - 0.010 * abs(a)
    side = V((d.y, -d.x, 0)).normalized()
    up = d.cross(side).normalized()
    rs = []
    for i in range(7):
        u = i / 6
        c = root + d * (ln * u)
        w = 0.0065 * (1 - u) ** 0.7 + 0.0006
        th = 0.0016 * (1 - u) + 0.0004
        rs.append([c + side * (w * math.cos(2 * math.pi * j / 8)) + up * (th * math.sin(2 * math.pi * j / 8))
                   for j in range(8)])
    tail_parts.append(mesh_from_rings("TailFeather", rs, TAIL, cap_start=root - d * 0.004, cap_end=root + d * (ln * 1.06)))
for ob in tail_parts:
    subdivide(ob, 1)

# ======================================================================= join + UVs
objs = [body, beak_up, beak_lo, tongue] + [e for e, _, _ in eyes] + flippers + feet + tail_parts
for o in objs:
    if not o.data.uv_layers:
        o.data.uv_layers.new(name="UVMap")
for o in bpy.context.view_layer.objects:
    o.select_set(o in objs)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
peng = body
peng.name = "Penguin"; peng.data.name = "Penguin"
me = peng.data
print("[build] mesh verts", len(me.vertices), "faces", len(me.polygons))

vpart = np.zeros(len(me.vertices), np.float32)
me.attributes["part"].data.foreach_get("value", vpart)
is_body_face = [vpart[p.vertices[0]] == BODY for p in me.polygons]

# body: squeeze the cylindrical layout into its strip
uvl = me.uv_layers["UVMap"]
for p, b in zip(me.polygons, is_body_face):
    if b:
        for li in p.loop_indices:
            u, v = uvl.data[li].uv
            uvl.data[li].uv = (u * BODY_U, v)
# everything else: smart project, then pack into the remaining strip
scene.tool_settings.use_uv_select_sync = True
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(me)
bm.faces.ensure_lookup_table()
for v in bm.verts:
    v.select_set(False)
for e in bm.edges:
    e.select_set(False)
for f, b in zip(bm.faces, is_body_face):
    f.select_set(False)
for f, b in zip(bm.faces, is_body_face):
    if not b:
        f.select_set(True)
bm.select_flush_mode()
bmesh.update_edit_mesh(me)
print("[build] faces to smart-project:", sum(1 for f in bm.faces if f.select))
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.01, area_weight=0.0, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')
uvl = me.uv_layers["UVMap"]                  # layer references go stale across mode switches
g = BODY_U + 0.008
SW = 1 - g - 0.004                           # strip width
# pre-stretch in u, pack without rotation, then squash into the strip: islands keep aspect
for p, b in zip(me.polygons, is_body_face):
    if not b:
        for li in p.loop_indices:
            u, v = uvl.data[li].uv
            uvl.data[li].uv = (u / SW, v)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.uv.pack_islands(rotate=False, scale=True, margin=0.006)
bpy.ops.object.mode_set(mode='OBJECT')
uvl = me.uv_layers["UVMap"]
for p, b in zip(me.polygons, is_body_face):
    if not b:
        for li in p.loop_indices:
            u, v = uvl.data[li].uv
            uvl.data[li].uv = (g + u * SW, v)
uvl = me.uv_layers["UVMap"]
us = np.array([uvl.data[li].uv[0] for p, b in zip(me.polygons, is_body_face) if not b for li in p.loop_indices])
print(f"[build] non-body UVs u in [{us.min():.3f}, {us.max():.3f}]")

# ======================================================================= textures
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 1
scene.render.bake.margin = 12
scene.render.bake.margin_type = 'EXTEND'

mat = bpy.data.materials.new("Penguin_Feathers")
me.materials.append(mat)
nt = mat.node_tree
nodes, links = nt.nodes, nt.links


def new_image(name, float_buffer=False, color=(0, 0, 0, 1)):
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, RES, RES, alpha=False, float_buffer=float_buffer)
    img.generated_color = color
    return img


def bake_emit(build_socket, img):
    for n in list(nodes):
        nodes.remove(n)
    out = nodes.new("ShaderNodeOutputMaterial")
    em = nodes.new("ShaderNodeEmission")
    links.new(em.outputs[0], out.inputs[0])
    links.new(build_socket(), em.inputs[0])
    tn = nodes.new("ShaderNodeTexImage"); tn.image = img
    nodes.active = tn
    bpy.ops.object.bake(type='EMIT')
    return np.array(img.pixels[:], dtype=np.float32).reshape(RES, RES, 4)


activate(peng)
LO, SPAN = V((-0.45, -0.45, -0.05)), 1.1


def pos_socket():
    tc = nodes.new("ShaderNodeTexCoord")
    mp = nodes.new("ShaderNodeVectorMath"); mp.operation = 'MULTIPLY_ADD'
    links.new(tc.outputs["Object"], mp.inputs[0])
    mp.inputs[1].default_value = (1 / SPAN,) * 3
    mp.inputs[2].default_value = tuple(-c / SPAN for c in LO)
    return mp.outputs[0]


def nrm_socket():
    g_ = nodes.new("ShaderNodeNewGeometry")
    tr = nodes.new("ShaderNodeVectorTransform"); tr.vector_type = 'NORMAL'
    tr.convert_from = 'WORLD'; tr.convert_to = 'OBJECT'
    links.new(g_.outputs["Normal"], tr.inputs[0])
    mp = nodes.new("ShaderNodeVectorMath"); mp.operation = 'MULTIPLY_ADD'
    links.new(tr.outputs[0], mp.inputs[0])
    mp.inputs[1].default_value = (0.5,) * 3; mp.inputs[2].default_value = (0.5,) * 3
    return mp.outputs[0]


def part_socket():
    a = nodes.new("ShaderNodeAttribute"); a.attribute_name = "part"
    m = nodes.new("ShaderNodeMath"); m.operation = 'DIVIDE'; m.inputs[1].default_value = 10.0
    links.new(a.outputs["Fac"], m.inputs[0])
    c = nodes.new("ShaderNodeCombineColor")
    for k in range(3):
        links.new(m.outputs[0], c.inputs[k])
    return c.outputs[0]


def noise_socket():
    """R: broad mottling, G: fine speckle (stretched along z), B: medium."""
    tc = nodes.new("ShaderNodeTexCoord")
    c = nodes.new("ShaderNodeCombineColor")
    for k, (sc, stretch, det) in enumerate([(9.0, (1, 1, 1), 3.0), (260.0, (1, 1, 0.35), 2.0), (45.0, (1, 1, 0.6), 4.0)]):
        vm = nodes.new("ShaderNodeVectorMath"); vm.operation = 'MULTIPLY'
        links.new(tc.outputs["Object"], vm.inputs[0]); vm.inputs[1].default_value = stretch
        nz = nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = sc
        nz.inputs["Detail"].default_value = det
        links.new(vm.outputs[0], nz.inputs["Vector"])
        links.new(nz.outputs["Fac"], c.inputs[k])
    return c.outputs[0]


px_pos = bake_emit(pos_socket, new_image("_pos", True))
px_nrm = bake_emit(nrm_socket, new_image("_nrm", True))
px_part = bake_emit(part_socket, new_image("_part", True))
px_noise = bake_emit(noise_socket, new_image("_noise", True))

for n in list(nodes):
    nodes.remove(n)
out = nodes.new("ShaderNodeOutputMaterial"); bs = nodes.new("ShaderNodeBsdfDiffuse")
links.new(bs.outputs[0], out.inputs[0])
ao_img = new_image("_ao", True, (1, 1, 1, 1)); tn = nodes.new("ShaderNodeTexImage"); tn.image = ao_img
nodes.active = tn
scene.cycles.samples = 64 if RES >= 2048 else 16
scene.world = bpy.data.worlds.new("BakeWorld")
bpy.ops.object.bake(type='AO')
px_ao = np.array(ao_img.pixels[:], dtype=np.float32).reshape(RES, RES, 4)[..., 0]
print("[build] baked position / normal / part / noise / AO")

# ----------------------------------------------------------------------- per-texel frames
P = px_pos[..., :3] * SPAN + np.array(LO)
x, y, z = P[..., 0], P[..., 1], P[..., 2]
N = px_nrm[..., :3] * 2 - 1
part = np.rint(px_part[..., 0] * 10 * 2) / 2
n_broad, n_fine, n_med = px_noise[..., 0], px_noise[..., 1], px_noise[..., 2]
ao = np.clip(px_ao, 0, 1)

# dense tables of the body loft: ring centre, perimeter fraction around each ring (from the
# back seam) and meridian arc length, so feathers are laid out in true surface metres and
# wrap seamlessly across the seam down the back
NZT, NTH = 320, 256
ZT = np.linspace(z0, z1, NZT)
THT = np.linspace(-math.pi, math.pi, NTH + 1)
RP = np.array([[tuple(ring_point(zz, th)) for th in THT] for zz in ZT])      # (NZT, NTH+1, 3)
seg = np.linalg.norm(np.diff(RP[:, :, :2], axis=1), axis=-1)
cum = np.concatenate([np.zeros((NZT, 1)), np.cumsum(seg, axis=1)], 1)
PERIM = cum[:, -1]
FRAC = cum / PERIM[:, None]
mer = np.linalg.norm(np.diff(RP, axis=0), axis=-1).mean(axis=1)             # mean over angles
S_T = np.concatenate([[0.0], np.cumsum(mer)])
YC_T = np.array([prof(zz)[3] for zz in ZT])

yc = np.interp(z, ZT, YC_T)
th_s = np.arctan2(x, -(y - yc))            # signed: 0 ahead, +pi/2 left flank
theta = np.abs(th_s)
fz = np.clip((z - z0) / (z1 - z0) * (NZT - 1), 0, NZT - 1.001)
fth = np.clip((th_s + math.pi) / (2 * math.pi) * NTH, 0, NTH - 0.001)
iz, ith = fz.astype(int), fth.astype(int)
wz, wt = fz - iz, fth - ith
frac_b = ((FRAC[iz, ith] * (1 - wt) + FRAC[iz, ith + 1] * wt) * (1 - wz)
          + (FRAC[iz + 1, ith] * (1 - wt) + FRAC[iz + 1, ith + 1] * wt) * wz)
perim_b = np.interp(z, ZT, PERIM)
S_b = np.interp(z, ZT, S_T)
R_z = perim_b / (2 * math.pi)


def col(*c):
    return np.array(c, dtype=np.float32)


def mix(a, b, t):
    t = np.asarray(t)[..., None]
    return a * (1 - t) + b * t


def hash2(a, b, k=0.0):
    h = np.sin(a * 127.1 + b * 311.7 + k * 74.7) * 43758.5453
    return h - np.floor(h)


def feathers(s, t, w, l, dx, dy, seed=0.0):
    """Overlapping tip-down feathers on a staggered grid in surface metres (s across, t up).
    Returns (height 0..1 rising toward each feather tip, per-feather random 0..1,
    tip mask 0..1, edge crease 0..1)."""
    r0 = np.floor(t / dy)
    best_pri = np.full(s.shape, -1e9); H = np.zeros(s.shape); RND = np.zeros(s.shape)
    TIP = np.zeros(s.shape); EDGE = np.ones(s.shape)
    for dr in (-1, 0, 1, 2):
        r = r0 + dr
        off = 0.5 * (np.mod(r, 2))
        c0 = np.floor(s / dx - off)
        for dc in (-1, 0, 1):
            c = c0 + dc
            j1 = hash2(r, c, seed); j2 = hash2(c, r, seed + 1.3); j3 = hash2(r + 7.1, c - 3.3, seed)
            sc = (c + off + 0.5 + 0.35 * (j1 - 0.5)) * dx
            tc = (r + 0.5 + 0.30 * (j2 - 0.5)) * dy
            ww = w * (0.85 + 0.3 * j3); ll = l * (0.85 + 0.3 * j1)
            a = (s - sc) / (0.5 * ww)
            b = (t - tc) / (0.5 * ll)
            # teardrop: narrower toward the (hidden) base at the top
            a = a / (1.0 - 0.25 * np.clip(b, -1, 1))
            q = a * a + b * b
            inside = q < 1.0
            pri = r + 0.2 * j2                         # higher rows lie on top
            take = inside & (pri > best_pri)
            h = (0.55 - 0.45 * b) * np.sqrt(np.clip(1 - q, 0, 1))
            h = h + 0.12 * np.exp(-(a / 0.10) ** 2) * (b < 0.8)      # rachis
            best_pri = np.where(take, pri, best_pri)
            H = np.where(take, h, H)
            RND = np.where(take, j3, RND)
            TIP = np.where(take, smoothstep(0.0, -0.8, b), TIP)
            EDGE = np.where(take, smoothstep(0.55, 1.0, q), EDGE)
    return H, RND, TIP, EDGE


def feathers_ring(frac, perim, t, w, l, dx, dy, seed=0.0, soft=0.0):
    """Like feathers(), on the body loft: each row gets a whole number of feathers around
    its ring, so the pattern closes seamlessly at the back. soft > 0 gives downy feathers
    with rounded, low-contrast edges."""
    r0 = np.floor(t / dy)
    best_pri = np.full(t.shape, -1e9); H = np.zeros(t.shape); RND = np.zeros(t.shape)
    TIP = np.zeros(t.shape); EDGE = np.ones(t.shape)
    for dr in (-1, 0, 1, 2):
        r = r0 + dr
        zr = np.interp((r + 0.5) * dy, S_T, ZT)
        ncol = np.maximum(np.round(np.interp(zr, ZT, PERIM) / dx), 3)
        cu = frac * ncol
        spacing = perim / ncol
        off = 0.5 * np.mod(r, 2)
        c0 = np.floor(cu - off)
        for dc in (-1, 0, 1):
            c = c0 + dc
            cm = np.mod(c, ncol)
            j1 = hash2(r, cm, seed); j2 = hash2(cm, r, seed + 1.3); j3 = hash2(r + 7.1, cm - 3.3, seed)
            cc = c + off + 0.5 + 0.50 * (j1 - 0.5)
            tc = (r + 0.5 + 0.45 * (j2 - 0.5)) * dy
            ww = w * (0.80 + 0.4 * j3); ll = l * (0.80 + 0.4 * j1)
            a = (cu - cc) * spacing / (0.5 * ww)
            b = (t - tc) / (0.5 * ll)
            a = a / (1.0 - 0.25 * np.clip(b, -1, 1))
            q = a * a + b * b
            inside = q < 1.0
            pri = r + 0.2 * j2
            take = inside & (pri > best_pri)
            if soft:
                h = (0.6 - 0.3 * b) * (1 - q) ** (1 + soft)
            else:
                h = (0.55 - 0.45 * b) * np.sqrt(np.clip(1 - q, 0, 1))
                h = h + 0.12 * np.exp(-(a / 0.10) ** 2) * (b < 0.8)      # rachis
            best_pri = np.where(take, pri, best_pri)
            H = np.where(take, h, H)
            RND = np.where(take, j3, RND)
            TIP = np.where(take, smoothstep(0.0, -0.8, b), TIP)
            EDGE = np.where(take, smoothstep(0.55, 1.0, q), EDGE)
    return H, RND, TIP, EDGE


def blur(img, mask, passes=2):
    """Separable [1 2 1] blur limited to texels inside mask."""
    out = img.copy(); m = mask.astype(np.float32)
    for _ in range(passes):
        for ax in (0, 1):
            num = out * m
            num = np.roll(num, 1, ax) + 2 * num + np.roll(num, -1, ax)
            den = np.roll(m, 1, ax) + 2 * m + np.roll(m, -1, ax)
            out = np.where(mask, num / np.maximum(den, 1e-6), out)
    return out


is_body = (part == BODY)

# ----------------------------------------------------------------------- feather fields
Hb, RNDb, TIPb, EDGEb = feathers_ring(frac_b, perim_b, S_b, 0.0115, 0.0160, 0.0078, 0.0058, 0.0)   # back
Hh, RNDh, TIPh, EDGEh = feathers_ring(frac_b, perim_b, S_b, 0.0036, 0.0068, 0.0025, 0.0030, 5.0)   # head velvet
# belly: small dense downy feathers, two offset layers averaged and blurred -> soft plush
Hs1, RNDs, _, EDGEs = feathers_ring(frac_b, perim_b, S_b, 0.0080, 0.0098, 0.0052, 0.0036, 11.0, soft=1.0)
Hs2, RNDs2, _, _ = feathers_ring(frac_b, perim_b, S_b + 0.0017, 0.0062, 0.0080, 0.0041, 0.0029, 17.0, soft=1.0)
Hs = blur(0.6 * Hs1 + 0.4 * Hs2, is_body, 2)
EDGEs = blur(EDGEs, is_body, 2)
head_w = smoothstep(0.70, 0.78, z)

# flipper frame coordinates (length along the flipper, width across it)
s_fl = np.zeros_like(x); t_fl = np.zeros_like(x)
for sgn, (sh, dn, fw, tk) in flip_frames.items():
    m = (part == FLIPPER) & (np.sign(x) == sgn)
    rel = P - np.array(sh)
    s_fl = np.where(m, rel @ np.array(fw), s_fl)
    t_fl = np.where(m, -(rel @ np.array(dn)), t_fl)          # "up" = toward the shoulder
Hf, RNDf, TIPf, EDGEf = feathers(s_fl, t_fl, 0.0048, 0.0060, 0.0034, 0.0024, 9.0)

# ----------------------------------------------------------------------- plumage colours
jit = (n_med - 0.5) * 0.08 + (n_fine - 0.5) * 0.025
tw = np.where(z < 0.60, 1.42 - 0.10 * smoothstep(0.35, 0.60, z),
              1.32 * np.sqrt(np.clip((0.770 - z) / 0.170, 0, 1)))
tw = np.where(z < 0.08, 1.42 + 0.5 * (1 - smoothstep(0.03, 0.08, z)), tw)
# feathered edge: the boundary follows individual feathers
fe = (RNDb * (1 - head_w) + RNDh * head_w - 0.5) * 0.04
ew = 0.025 + 0.030 * smoothstep(0.66, 0.76, z)          # softer bib edge under the chin
white = (1 - smoothstep(tw - ew, tw + ew, theta + jit * (1 - 0.5 * head_w) + fe)) * smoothstep(0.02, 0.12, tw)

BLACK = col(0.008, 0.008, 0.011)
SLATE = col(0.060, 0.068, 0.085)
SHEEN = col(0.16, 0.18, 0.22)
WHITE = col(0.88, 0.88, 0.85)
CREAM = col(0.94, 0.87, 0.63)
YELLOW = col(0.98, 0.76, 0.26)
ORANGE = col(0.99, 0.56, 0.08)

hood = smoothstep(0.66, 0.76, z)
Hd = Hb * (1 - head_w) + Hh * head_w
RNDd = RNDb * (1 - head_w) + RNDh * head_w
TIPd = TIPb * (1 - head_w) + TIPh * head_w
EDGEd = EDGEb * (1 - head_w) + EDGEh * head_w
dark = mix(SLATE, BLACK, hood)
dark = mix(dark, SHEEN, (0.55 - 0.35 * hood) * TIPd * (0.5 + 0.5 * RNDd))   # glossy feather tips
dark = dark * (0.80 + 0.35 * RNDd)[..., None] * (0.88 + 0.24 * n_broad)[..., None]
dark = dark * (1 - (0.30 - 0.18 * head_w) * EDGEd)[..., None]
seam = smoothstep(tw + 0.02, tw + 0.08, theta + jit) * (1 - smoothstep(tw + 0.12, tw + 0.25, theta + jit))
dark = mix(dark, BLACK, 0.6 * seam)

light = mix(WHITE, CREAM, 0.20 * smoothstep(0.35, 0.10, z))
breast = smoothstep(0.50, 0.68, z + 0.03 * (n_broad - 0.5)) * (1 - smoothstep(1.00, 1.50, theta))
GOLD = col(0.98, 0.80, 0.38)
light = mix(light, mix(CREAM, GOLD, smoothstep(0.56, 0.72, z)), 0.90 * breast)
# soft plush: shading follows the downy height field, only faint feather outlines
light = light * (0.90 + 0.14 * Hs)[..., None] * (0.97 + 0.04 * RNDs)[..., None]
light = light * (1 - 0.05 * EDGEs)[..., None] * (0.955 + 0.06 * n_broad)[..., None]
light = light * (0.975 + 0.05 * n_fine)[..., None]
# soiled underside and lower belly from lying on snow / guano
soil = (1 - smoothstep(0.05, 0.20, z)) * (0.5 + 0.7 * n_broad) * (1 - smoothstep(1.0, 1.6, theta))
light = mix(light, col(0.55, 0.52, 0.47), np.clip(0.45 * soil, 0, 0.45))

c_body = mix(dark, light, white)

# ear patches: a broad comma behind the eye sweeping forward and down into the breast
# broad oval on the side of the head behind / below the eye ...
d_head = np.sqrt(((theta - 1.36 - 3.5 * (z - 0.830)) / 0.68) ** 2 + ((z - 0.828) / 0.052) ** 2)
# ... narrowing as it runs down and forward along the neck into the golden breast
k = (0.800 - z) / 0.14
th_c = 1.22 - 0.36 * k
half = 0.46 - 0.24 * np.clip(k, 0, 1)
d_neck = np.where((k > -0.1) & (k < 1.25), np.abs(theta - th_c) / half, 9.0)
d_neck = d_neck + smoothstep(0.9, 1.3, k) * 0.4
ear = 1 - smoothstep(0.78, 1.0, np.minimum(d_head, d_neck) + jit + 0.8 * fe)
ear_col = mix(ORANGE, YELLOW, smoothstep(0.82, 0.70, z))
ear_col = mix(ear_col, col(1.0, 0.68, 0.14), 0.30 * n_med)
ear_col = mix(ear_col, GOLD, smoothstep(0.72, 0.66, z))
ear_col = ear_col * (0.93 + 0.12 * RNDh)[..., None] * (1 - 0.12 * EDGEh)[..., None]
c_body = mix(c_body, ear_col, np.clip(ear, 0, 1))

# flippers: black outside with glossy scale-feathers, white underside
side = np.sign(x)
out_face = np.clip(N[..., 0] * side * 3, -1, 1) * 0.5 + 0.5
fl_u = np.clip(t_fl * -1 / FLIP_LEN, 0, 1)
fl_dark = mix(SLATE * 0.8, SHEEN, 0.5 * TIPf) * (0.85 + 0.3 * RNDf)[..., None] * (1 - 0.4 * EDGEf)[..., None]
fl_light = mix(WHITE, col(0.72, 0.74, 0.76), 0.35 * n_med) * (1 - 0.1 * EDGEf)[..., None]
fl_under = 1 - smoothstep(0.35, 0.6, out_face)
c_flip = mix(fl_dark, fl_light, fl_under)
c_flip = mix(c_flip, BLACK, 0.75 * (1 - smoothstep(0.02, 0.10, fl_u)))

# beak
bu = np.linalg.norm(P - np.array(BEAK_ORIGIN), axis=-1) / BEAK_LEN
bup = (P - np.array(BEAK_ORIGIN)) @ np.array(BEAK_UPV)
mouth_side_up = (N @ np.array(BEAK_UPV)) < -0.55          # underside of the upper mandible
mouth_side_lo = (N @ np.array(BEAK_UPV)) > 0.55           # top of the lower mandible
MOUTHC = col(0.50, 0.16, 0.18)
c_beak_up = mix(col(0.016, 0.015, 0.017), col(0.10, 0.09, 0.085), smoothstep(0.78, 1.0, bu))
c_beak_up = c_beak_up * (0.9 + 0.2 * n_med)[..., None]
feather_base = 1 - smoothstep(0.16, 0.24, bu + 0.05 * (n_med - 0.5))       # feathering onto the bill
c_beak_up = mix(c_beak_up, BLACK * (0.8 + 0.4 * RNDh)[..., None], feather_base)
c_beak_up = np.where(mouth_side_up[..., None], mix(MOUTHC, c_beak_up, smoothstep(0.75, 1.0, bu)), c_beak_up)
plate = smoothstep(0.10, 0.18, bu) * (1 - smoothstep(0.58, 0.74, bu)) * smoothstep(0.25, 0.6, np.abs(N[..., 0]))
c_beak_lo = mix(col(0.018, 0.016, 0.018), mix(col(0.96, 0.44, 0.30), col(0.99, 0.62, 0.36), n_med), plate)
c_beak_lo = mix(c_beak_lo, BLACK, feather_base)
c_beak_lo = np.where(mouth_side_lo[..., None], mix(MOUTHC, c_beak_lo, smoothstep(0.7, 0.95, bu)), c_beak_lo)
c_mouth = col(0.62, 0.24, 0.26) * (0.9 + 0.2 * n_med)[..., None]

# feet: dark grey leathery skin, black claws
c_foot = col(0.105, 0.100, 0.104) * (0.80 + 0.4 * n_med)[..., None] * (0.85 + 0.3 * n_fine)[..., None]
c_claw = col(0.030, 0.027, 0.025)

# eyes: dark brown iris, black pupil
c_eye = np.zeros_like(P) + col(0.02, 0.012, 0.01)
for ob_, ctr, nrm in eyes:
    rel = P - np.array(ctr)
    dn = np.linalg.norm(rel, axis=-1) + 1e-9
    cosang = (rel @ np.array(nrm)) / dn
    near = dn < EYE_R * 1.5
    iris = mix(col(0.20, 0.09, 0.04), col(0.08, 0.035, 0.02), smoothstep(0.80, 0.93, cosang))
    iris = mix(iris, col(0.005, 0.005, 0.005), smoothstep(0.935, 0.95, cosang))
    c_eye = np.where((near & (cosang > 0.55))[..., None], iris, c_eye)

c_tail = SLATE * (0.75 + 0.4 * RNDb)[..., None] * (1 - 0.3 * EDGEb)[..., None]

base = c_body.copy()
for pid, cc in ((BEAK_UP, c_beak_up), (BEAK_LO, c_beak_lo), (MOUTH, c_mouth), (FLIPPER, c_flip),
                (FOOT, c_foot), (CLAW, c_claw), (EYE, c_eye), (TAIL, c_tail)):
    m = part == pid
    base[m] = (cc if cc.ndim == 1 else cc[m])
base = base * (0.50 + 0.50 * ao)[..., None]
base = np.clip(base, 0, 1)

# ----------------------------------------------------------------------- roughness
rough = np.where(white > 0.5, 0.80 - 0.06 * Hs, 0.58 - 0.22 * TIPd * (0.5 + 0.5 * RNDd))
rough = np.where((white < 0.5) & (head_w > 0), rough * (1 - head_w) + (0.50 - 0.08 * TIPh) * head_w, rough)
rough = np.where(ear > 0.5, 0.62, rough)
rough[part == FLIPPER] = (0.55 - 0.2 * TIPf)[part == FLIPPER]
rough[(part == BEAK_UP) | (part == BEAK_LO)] = 0.30
rough[part == MOUTH] = 0.35
rough[part == FOOT] = 0.62
rough[part == CLAW] = 0.35
rough[part == EYE] = 0.04
rough[part == TAIL] = 0.5
rough = rough + (n_fine - 0.5) * 0.08

# ----------------------------------------------------------------------- height -> normal map
H = np.zeros_like(x)
AMP_BACK, AMP_BELLY, AMP_HEAD = 0.0011, 0.0005, 0.00022
amp = np.where(white > 0.5, AMP_BELLY, AMP_BACK) * (1 - head_w) + AMP_HEAD * head_w
belly_fluff = (n_fine - 0.5) * 0.00012
H_belly = Hs * 0.00045 + belly_fluff
H = np.where(is_body, Hd * amp * (1 - white) + H_belly * white, H)
H = np.where(part == TAIL, Hb * 0.0012, H)
H = np.where(part == FLIPPER, Hf * 0.00035, H)
# beak: longitudinal grooves and the sulcus along the upper mandible
H = np.where((part == BEAK_UP) | (part == BEAK_LO),
             0.00012 * np.sin(bup * 1800.0) * (n_med) - 0.0004 * np.exp(-((bup - 0.004) / 0.0012) ** 2) * (part == BEAK_UP)
             + feather_base * Hh * 0.0004, H)
# feet: pebbly scales
H = np.where(part == FOOT, (n_fine - 0.5) * 0.0012 + (n_med - 0.5) * 0.0006, H)


def gradient(H, P, axis):
    Hp, Hm = np.roll(H, -1, axis), np.roll(H, 1, axis)
    Pp, Pm = np.roll(P, -1, axis), np.roll(P, 1, axis)
    dist = np.linalg.norm(Pp - Pm, axis=-1)
    same = (dist < 0.004) & (np.roll(part, -1, axis) == part) & (np.roll(part, 1, axis) == part)
    g_ = np.where(same & (dist > 1e-7), (Hp - Hm) / np.maximum(dist, 1e-7), 0.0)
    return np.clip(g_, -1.5, 1.5)


gx = gradient(H, P, 1)                      # image x = +u = tangent
gy = gradient(H, P, 0)                      # image y = +v = bitangent
nm = np.stack([-gx, -gy, np.ones_like(gx)], -1)
nm /= np.linalg.norm(nm, axis=-1, keepdims=True)
print("[build] painted plumage, feathers and normals")


def save(name, rgb, colorspace):
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, RES, RES, alpha=False)
    img.colorspace_settings.name = colorspace
    rgba = np.ones((RES, RES, 4), np.float32); rgba[..., :3] = rgb
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(TEX, name + ".png"); img.file_format = 'PNG'
    img.save()
    img.filepath = img.filepath_raw
    img.pack()
    return img


img_base = save("Penguin_BaseColor", base, 'sRGB')
orm = np.stack([0.35 + 0.65 * ao, np.clip(rough, 0.03, 1), np.zeros_like(ao)], -1)
img_orm = save("Penguin_ORM", orm, 'Non-Color')
img_nrm = save("Penguin_Normal", nm * 0.5 + 0.5, 'Non-Color')
print("[build] textures written to", TEX)

# ----------------------------------------------------------------------- final material
for n in list(nodes):
    nodes.remove(n)
out = nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (250, 0)
links.new(bsdf.outputs[0], out.inputs[0])
t_base = nodes.new("ShaderNodeTexImage"); t_base.image = img_base; t_base.location = (-400, 300)
t_orm = nodes.new("ShaderNodeTexImage"); t_orm.image = img_orm; t_orm.location = (-400, 0)
t_n = nodes.new("ShaderNodeTexImage"); t_n.image = img_nrm; t_n.location = (-400, -300)
sep = nodes.new("ShaderNodeSeparateColor"); sep.location = (-100, 0)
nmap = nodes.new("ShaderNodeNormalMap"); nmap.location = (-100, -300)
links.new(t_base.outputs[0], bsdf.inputs["Base Color"])
links.new(t_orm.outputs[0], sep.inputs[0])
links.new(sep.outputs[1], bsdf.inputs["Roughness"])
links.new(sep.outputs[2], bsdf.inputs["Metallic"])
links.new(t_n.outputs[0], nmap.inputs["Color"])
links.new(nmap.outputs[0], bsdf.inputs["Normal"])
for nm_ in ("_pos", "_nrm", "_part", "_noise", "_ao"):
    if nm_ in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[nm_])

# ======================================================================= 7. armature
arm_data = bpy.data.armatures.new("PenguinRig")
arm = bpy.data.objects.new("PenguinRig", arm_data)
scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones


def bone(name, h, t, parent=None, deform=True, connect=False):
    b = eb.new(name); b.head = V(h); b.tail = V(t)
    if parent:
        b.parent = eb[parent]; b.use_connect = connect
    b.use_deform = deform
    return b


bone("root", (0, 0, 0), (0, 0.25, 0), deform=False)
bone("body", (0, 0.010, 0.200), (0, 0.004, 0.450), "root")
bone("spine", (0, 0.004, 0.450), (0, -0.010, 0.620), "body", connect=True)
NECK_Y = prof(0.740)[3] + 0.012            # bones sit a little behind the ring centres
HEAD_Y = prof(0.835)[3] + 0.012
bone("chest", (0, -0.010, 0.620), (0, NECK_Y, 0.740), "spine", connect=True)
bone("neck", (0, NECK_Y, 0.740), (0, HEAD_Y, 0.835), "chest", connect=True)
bone("head", (0, HEAD_Y, 0.835), (0, HEAD_Y - 0.004, 0.965), "neck", connect=True)
bone("jaw", JAW_PIVOT, JAW_TIP, "head")
bone("tail", (0, 0.110, 0.115), (0, 0.232, 0.028), "body")
for s, sd in ((1, "L"), (-1, "R")):
    sh, down, fwd, thick = flip_frames[s]
    _, elbow, tip = flip_joints[s]
    b = bone(f"flipper_upper.{sd}", sh, elbow, "chest"); b.align_roll(thick)
    b = bone(f"flipper_lower.{sd}", elbow, tip, f"flipper_upper.{sd}", connect=True); b.align_roll(thick)
    lg = LEG[s]
    b = bone(f"thigh.{sd}", lg["hip"], lg["knee"], "body"); b.align_roll(V((1, 0, 0)))
    b = bone(f"shin.{sd}", lg["knee"], lg["ankle"], f"thigh.{sd}", connect=True); b.align_roll(V((1, 0, 0)))
    b = bone(f"foot.{sd}", lg["ankle"], lg["toe"], f"shin.{sd}", connect=True); b.align_roll(V((0, 0, 1)))
bpy.ops.object.mode_set(mode='OBJECT')
arm_data.display_type = 'STICK'
B = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm_data.bones}

# ======================================================================= 8. weights
peng.parent = arm
peng.matrix_parent_inverse = Matrix()
mod = peng.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
for b in arm_data.bones:
    if b.use_deform:
        peng.vertex_groups.new(name=b.name)

parts = np.zeros(len(me.vertices), np.float32)
me.attributes["part"].data.foreach_get("value", parts)
co = [v.co.copy() for v in me.vertices]

CHAIN = [("body", 0.20), ("spine", 0.47), ("chest", 0.66), ("neck", 0.775), ("head", 0.855)]


def chain_weights(z_):
    if z_ <= CHAIN[0][1]:
        return {CHAIN[0][0]: 1.0}
    if z_ >= CHAIN[-1][1]:
        return {CHAIN[-1][0]: 1.0}
    for (a, za), (b, zb) in zip(CHAIN, CHAIN[1:]):
        if za <= z_ <= zb:
            t = sstep(za, zb, z_)
            return {a: 1 - t, b: t}


def along(p, name):
    h, t = B[name]
    d = t - h
    return (p - h).dot(d) / d.length_squared


groups = peng.vertex_groups
for i, p in enumerate(co):
    pid = parts[i]
    sd = "L" if p.x > 0 else "R"
    if pid == BODY:
        ws = chain_weights(p.z)
        leg = 0.65 * (1 - sstep(0.06, 0.22, p.z)) * sstep(0.015, 0.09, abs(p.x)) * (1 - sstep(0.08, 0.16, p.y))
        if leg > 0:
            ws = {n: w * (1 - leg) for n, w in ws.items()}
            ws[f"thigh.{sd}"] = leg * 0.6
            ws[f"shin.{sd}"] = leg * 0.4
        tr = sstep(0.08, 0.13, p.y) * (1 - sstep(0.10, 0.20, p.z))
        if tr > 0:
            ws = {n: w * (1 - 0.5 * tr) for n, w in ws.items()}
            ws["tail"] = ws.get("tail", 0) + 0.5 * tr
    elif pid == TAIL:
        t = sstep(0.0, 0.5, along(p, "tail"))
        ws = {"body": 1 - t, "tail": t}
    elif pid in (BEAK_UP, EYE):
        ws = {"head": 1.0}
    elif pid in (BEAK_LO, MOUTH):
        ws = {"jaw": 1.0}
    elif pid == FLIPPER:
        u = along(p, f"flipper_upper.{sd}") * 0.45
        root = sstep(-0.02, 0.22, u)
        lower = sstep(0.36, 0.54, u)
        ws = {"chest": 1 - root, f"flipper_upper.{sd}": root * (1 - lower), f"flipper_lower.{sd}": root * lower}
    else:  # feet, webs, claws
        ws = {f"foot.{sd}": 1.0}
    for n, w in ws.items():
        if w > 1e-4:
            groups[n].add([i], w, 'REPLACE')

bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("[build] saved", OUT)
