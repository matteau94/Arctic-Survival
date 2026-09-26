"""Model, texture and rig an orca (killer whale) in the style of the other Artic-Survival animals.

    blender -b --python orca_build.py        (writes Orca_Rigged.blend + textures/Orca_*.png)

Real-world metres, ~6.1 m long (adult), body axis on z = 0, facing -Y (so +X is its left side).
~40k verts, one object 'Orca', one material 'Orca_Skin', armature 'OrcaRig'.

1. Mesh (one object, one material, like the fox / bear / fish / penguin): subdivided lofts
     body      snout -> melon -> barrel -> keeled, laterally compressed tail stock as one ring
               loft (rings packed densely at the snout, eye and blowhole); the ring vertex on the
               lip line is split from the snout back to the mouth corner so the lower jaw opens.
               A numpy 'sculpt' pass then displaces it along its normals: melon + rostrum
               crease, mouth-line groove curving up at the gape, lower-lip bead, chin, eye
               socket / brow / cheek, crescent blowhole (slit, raised rear lip, nasal plug),
               throat folds, epaxial / hypaxial muscle masses, dorsal and ventral tail keels,
               genital / umbilical slits
     mouth     a soft interior 'plug' inside the head (seen through the open jaw) + conical teeth
               sitting between plug and skin (hidden when the jaw is closed)
     eyes      eyeballs with a painted iris / pupil (glassy roughness) and almond eyelid skirts
               draped onto the sculpted skin
     fins      tall back-leaning dorsal fin (flared root, thin wavy trailing edge), broad paddle
               pectorals with faint digit ridges, flukes with a median notch, thin trailing edge
               and slightly drooping tips
   Every part carries a 'part' point attribute used when texturing and weighting.
2. Textures (2048^2, PBR like the other assets): object-space position / normal / part /
   noise / AO are baked from the mesh and the pattern is painted from them in numpy: charcoal
   back (darker along the spine, lighter flank mottling), white lower jaw / throat / belly /
   flank lobes, oval eye patch, feathered striated grey saddle, rake-mark scars, diatom tint,
   white fluke undersides.  A height map (wrinkles at eye / blowhole / gape / armpit, throat
   folds, scars, slits) plus procedural micro-pores is baked through a bump node into the
   tangent-space normal map.
     textures/Orca_BaseColor.png, Orca_ORM.png (R=AO, G=roughness, B=metal), Orca_Normal.png
3. Rig 'OrcaRig':
     root (no deform)
       body > chest > head > jaw                    (jaw: local -X rotation opens the mouth)
       head > blowhole                              (local +X rotation lifts the rear lip = open)
       body > tail_01 > tail_02 > tail_03 > tail_04 > tail_05 > fluke > fluke_tip.L / fluke_tip.R
                                                    (fluke_tip: local X rotation curls the blade tip)
       body > dorsal_01 > dorsal_02
       chest > pectoral_01.L/R > pectoral_02.L/R
"""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector as V, Matrix
from mathutils.bvhtree import BVHTree

DIR = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
OUT = os.path.join(DIR, "Orca_Rigged.blend")
TEX = os.path.join(DIR, "textures")
RES = 2048

BODY, DORSAL, PECTORAL, FLUKE, EYE, MOUTH, TEETH = range(7)
L, Y0 = 6.0, -3.0                    # body length (snout to fluke insertion ~0.95 L), snout y
MOUTH_J, NSEG = 9, 32                # ring vertex on the lip line (and its mirror NSEG - 9)
PHI_M = 2 * math.pi * MOUTH_J / NSEG  # lip line angle from the top of the ring
S_CORNER = 0.10                      # mouth corner, fraction of L


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


def hermite_np(keys, x, n=2001):
    lo, hi = keys[0][0], keys[-1][0]
    xs = np.linspace(lo, hi, n)
    return np.interp(x, xs, [hermite(keys, v) for v in xs])


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'


# ======================================================================= mesh helpers
def mesh_from_rings(name, rings, part, cap_start=None, cap_end=None):
    """Quad loft through closed rings (equal vertex counts); caps are pole points."""
    verts, faces = [], []
    n = len(rings[0])
    for r in rings:
        verts.extend(r)
    for k in range(len(rings) - 1):
        a, b = k * n, (k + 1) * n
        for j in range(n):
            j2 = (j + 1) % n
            faces.append((a + j, a + j2, b + j2, b + j))
    if cap_start is not None:
        verts.append(cap_start); p = len(verts) - 1
        for j in range(n):
            faces.append((p, (j + 1) % n, j))
    if cap_end is not None:
        verts.append(cap_end); p = len(verts) - 1; a = (len(rings) - 1) * n
        for j in range(n):
            faces.append((p, a + j, a + (j + 1) % n))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    att = me.attributes.new("part", 'FLOAT', 'POINT')
    att.data.foreach_set("value", [float(part)] * len(me.vertices))
    att = me.attributes.new("jaw", 'FLOAT', 'POINT')
    att.data.foreach_set("value", [0.0] * len(me.vertices))
    return ob


def subdivide(ob, levels):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    m = ob.modifiers.new("Subsurf", 'SUBSURF')
    m.levels = m.render_levels = levels
    bpy.ops.object.modifier_apply(modifier=m.name)
    for p in ob.data.polygons:
        p.use_smooth = True


# ======================================================================= 1. body
# s (fraction of L from the snout), half width, top height, belly depth, centre z
PROFILE = [
    (0.000, 0.030, 0.030, 0.030, -0.100),
    (0.012, 0.165, 0.150, 0.125, -0.100),
    (0.035, 0.265, 0.250, 0.195, -0.085),
    (0.065, 0.355, 0.340, 0.260, -0.065),
    (0.100, 0.435, 0.425, 0.330, -0.045),
    (0.150, 0.510, 0.505, 0.425, -0.025),
    (0.220, 0.570, 0.570, 0.530, -0.010),
    (0.300, 0.625, 0.645, 0.640, 0.000),
    (0.380, 0.635, 0.675, 0.675, 0.000),
    (0.460, 0.605, 0.660, 0.650, 0.000),
    (0.540, 0.540, 0.600, 0.575, 0.010),
    (0.620, 0.445, 0.525, 0.485, 0.015),
    (0.700, 0.330, 0.435, 0.385, 0.020),
    (0.770, 0.220, 0.345, 0.300, 0.020),
    (0.830, 0.140, 0.265, 0.230, 0.020),
    (0.880, 0.092, 0.190, 0.165, 0.015),
    (0.920, 0.068, 0.120, 0.105, 0.010),
    (0.945, 0.055, 0.070, 0.065, 0.010),
]
S_END = PROFILE[-1][0]
KEYS = [[(r[0], r[i]) for r in PROFILE] for i in range(1, 5)]


def prof(s):
    return [hermite(k, s) for k in KEYS]


def ring_point(s, phi):
    """phi = 0 on top, pi/2 on the left flank (+x), pi under the belly."""
    hw, top, bot, zc = prof(s)
    p = 0.9 + 0.8 * sstep(0.72, 0.90, s)      # tail stock pinches into dorsal / ventral keels
    sp, cp = math.sin(phi), math.cos(phi)
    x = hw * math.copysign(abs(sp) ** p, sp)
    z = zc + (top if cp >= 0 else bot) * math.copysign(abs(cp) ** 0.95, cp)
    return V((x, Y0 + L * s, z))


def lip_point(s):
    return ring_point(s, PHI_M)


# ring spacing (fraction of L) as a function of s: fine at the snout, the eye and around the
# blowhole (so the crescent can be sculpted), coarse along the barrel, medium on the keeled tail
DENS = [(0.0, 0.006), (0.03, 0.010), (0.14, 0.011), (0.155, 0.0048), (0.186, 0.0048), (0.21, 0.014),
        (0.28, 0.040), (0.64, 0.040), (0.72, 0.030), (0.945, 0.026)]
ss = [0.003]
while ss[-1] < S_END - 0.012:
    ss.append(ss[-1] + float(np.interp(ss[-1], [d[0] for d in DENS], [d[1] for d in DENS])))
ss[-1] = S_END
NR = len(ss)
S_TAB = np.linspace(0.0, S_END, 1200)
P_TAB = np.array([prof(v) for v in S_TAB])


def prof_np(sv):
    sv = np.clip(sv, 0.0, S_END)
    return [np.interp(sv, S_TAB, P_TAB[:, k]) for k in range(4)]
rings = [[ring_point(s, 2 * math.pi * j / NSEG) for j in range(NSEG)] for s in ss]
body = mesh_from_rings("Body", rings, BODY, cap_start=V((0, Y0 - 0.004, PROFILE[0][4])),
                       cap_end=V((0, Y0 + L * (S_END + 0.010), PROFILE[-1][4])))

# split the lip line so the lower jaw can drop away from the upper jaw
KM = max(k for k, s in enumerate(ss) if s <= S_CORNER)
bm = bmesh.new(); bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
pole = NR * NSEG
cut = []
for j in (MOUTH_J, NSEG - MOUTH_J):
    cut.append(bm.edges.get((bm.verts[pole], bm.verts[j])))
    for k in range(KM):
        cut.append(bm.edges.get((bm.verts[k * NSEG + j], bm.verts[(k + 1) * NSEG + j])))
bmesh.ops.split_edges(bm, edges=[e for e in cut if e])
# tag the lower jaw side: a vertex whose faces all lie below the lip line
zc_of = lambda y: hermite(KEYS[3], (y - Y0) / L)
jaw_layer = bm.verts.layers.float.get("jaw")
for v in bm.verts:
    below = [abs(math.atan2(f.calc_center_median().x, f.calc_center_median().z - zc_of(f.calc_center_median().y))) > PHI_M
             for f in v.link_faces]
    v[jaw_layer] = sum(below) / max(1, len(below))
bm.to_mesh(body.data); bm.free()
subdivide(body, 2)

# ----------------------------------------------------------------------- sculpt (numpy displacement)
EYE_R = 0.030
EYE_S, EYE_PHI = 0.115, 1.40
BLOW_S = 0.170                       # blowhole (crescent, horns pointing forward)
YB = Y0 + L * BLOW_S
CRES = 1.6                           # crescent curvature: v = y - YB + CRES x^2
LIP_ANG = math.atan2(math.sin(PHI_M) ** 0.9, -abs(math.cos(PHI_M)) ** 0.95)


def g(x, c, w):
    return np.exp(-((x - c) / w) ** 2)


def body_params(P):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    sv = (y - Y0) / L
    hw, top, bot, zc = prof_np(sv)
    u = x / hw
    w = (z - zc) / np.where(z > zc, top, bot)
    ang = np.arctan2(np.abs(u), w)              # 0 top, pi belly (ellipse-normalised)
    rad = np.hypot(x, z - zc)
    return sv, ang, rad, zc


def blow_v(x, y):
    return y - YB + CRES * x * x


def sculpt(P):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    sv, ang, rad, zc = body_params(P)
    d = np.zeros(len(P))
    # melon and the soft crease where it meets the short rostrum
    d += 0.030 * g(sv, 0.058, 0.034) * g(ang, 0.0, 1.0)
    d -= 0.008 * g(sv, 0.018, 0.008) * g(ang, 0.0, 1.1) * smoothstep(0.006, 0.013, sv)
    # mouth line: shallow groove on the lip line that curves up at the corner, lower lip bead
    lip = LIP_ANG - 0.30 * smoothstep(0.092, 0.128, sv)
    dl = (ang - lip) * rad                             # + below the lip line
    front = 1 - smoothstep(0.118, 0.140, sv)
    d -= 0.0045 * g(dl, 0.0, 0.011) * front
    d += 0.0055 * g(dl, 0.022, 0.012) * (1 - smoothstep(0.085, 0.11, sv))
    # chin: slight fullness under the lower jaw tip
    d += 0.010 * g(sv, 0.03, 0.025) * g(ang, 2.6, 0.5)
    # eye socket, brow above and a soft cheek below
    ex = ring_point(EYE_S, EYE_PHI)
    for sd in (1, -1):
        e = np.array((ex.x * sd, ex.y, ex.z))
        r = np.linalg.norm(P - e, axis=1)
        above = np.clip((z - e[2]) / 0.06, -1, 1)
        d -= 0.007 * g(r, 0.0, 0.030)
        d += 0.007 * g(r, 0.060, 0.022) * np.clip(0.4 + above, 0, 1)
        d += 0.004 * g(r, 0.070, 0.030) * np.clip(-above, 0, 1)
    # blowhole: crescent slit, raised rear lip, shallow nasal plug in front
    v = blow_v(x, y)
    lat = 1 - smoothstep(0.075, 0.115, np.abs(x))
    topm = (ang < 0.6)
    d -= 0.020 * g(v, 0.0, 0.0085) * lat * topm
    d += 0.008 * g(v, 0.020, 0.012) * lat * topm
    d -= 0.005 * g(v, -0.030, 0.022) * lat * topm
    d += 0.004 * g(v, 0.0, 0.10) * g(x, 0.0, 0.16) * topm        # the nasal mound
    # subtle ventral throat / chest folds
    fold = 0.5 + 0.5 * np.cos(2 * np.pi * x / 0.085)
    d -= 0.0035 * fold * smoothstep(0.12, 0.15, sv) * (1 - smoothstep(0.22, 0.28, sv)) * smoothstep(2.35, 2.75, ang)
    # epaxial muscle masses along the back, hypaxial below the flank
    d += 0.014 * g(ang, 0.62, 0.22) * smoothstep(0.17, 0.30, sv) * (1 - smoothstep(0.62, 0.82, sv))
    d += 0.008 * g(ang, 2.25, 0.25) * smoothstep(0.30, 0.45, sv) * (1 - smoothstep(0.62, 0.78, sv))
    d -= 0.004 * g(ang, 1.55, 0.18) * smoothstep(0.35, 0.5, sv) * (1 - smoothstep(0.7, 0.85, sv))
    # sharp dorsal / ventral keels on the tail stock
    keel = smoothstep(0.70, 0.80, sv) * (1 - smoothstep(0.925, 0.945, sv))
    d += 0.022 * keel * (g(ang, 0.0, 0.16) + 0.8 * g(ang, np.pi, 0.16))
    # genital / umbilical slit hints
    mid = g(x, 0.0, 0.006) * (ang > 2.8)
    d -= 0.006 * mid * smoothstep(0.600, 0.606, sv) * (1 - smoothstep(0.650, 0.656, sv))
    d -= 0.005 * g(np.hypot(x, (y - (Y0 + L * 0.50))), 0.0, 0.012) * (ang > 2.8)
    return d


me_b = body.data
nb = len(me_b.vertices)
co_b = np.zeros(nb * 3, np.float32); me_b.vertices.foreach_get("co", co_b); co_b = co_b.reshape(-1, 3).astype(np.float64)
nr_b = np.zeros(nb * 3, np.float32); me_b.vertex_normals.foreach_get("vector", nr_b); nr_b = nr_b.reshape(-1, 3).astype(np.float64)
_, inv = np.unique(np.round(co_b / 1e-4).astype(np.int64), axis=0, return_inverse=True)   # weld the lip seam normals
inv = inv.reshape(-1)
acc = np.zeros((inv.max() + 1, 3)); np.add.at(acc, inv, nr_b); nr_b = acc[inv]
nr_b /= np.linalg.norm(nr_b, axis=1, keepdims=True)
co_b += nr_b * sculpt(co_b)[:, None]
me_b.vertices.foreach_set("co", co_b.astype(np.float32).ravel())
me_b.update()
bvh_body = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())


def surface(origin, direction):
    hit, nrm, _, _ = bvh_body.ray_cast(V(origin), V(direction).normalized())
    return hit, nrm


# ======================================================================= 2. mouth interior + teeth
# The mouth lining is one folded sheet: palate (under the upper jaw, facing down) -> throat fold at
# S_BACK -> floor + tongue (over the lower jaw, facing up) back to the chin.  Its side and front edges
# tuck up / down inside the lips, so the open mouth shows a real cavity (palate, gum ridges, tongue,
# dark throat) instead of a slab.  The palate is weighted to 'head', the floor to 'jaw', blending to
# 'head' near the throat fold so it stretches instead of folding through the palate.
TOOTH_R = 0.905                      # tooth row, as a fraction of the lip half-width
S_BACK = 0.135                       # throat fold (just behind the gape)
NA, NU = 33, 22


def lip_w(s):
    return abs(lip_point(s).x)


def lining_point(s, a, upper):
    lp = lip_point(s)
    w, lz = abs(lp.x), lp.z
    fold = 1 - sstep(S_BACK - 0.04, S_BACK, s)
    front = sstep(0.004, 0.030, s)
    aa = min(abs(a), 0.94) / 0.94                                     # interior: 0 midline .. 1 gum
    if upper:
        dz = 0.006 + 0.048 * (1 - aa * aa) * front                      # vaulted palate
        dz -= 0.011 * math.exp(-((aa - 0.975) / 0.05) ** 2)             # gum ridge under the tooth row
    else:
        tongue = sstep(0.030, 0.065, s) * front
        dz = -0.012 - 0.014 * (1 - aa * aa) * front                     # floor of the mouth
        dz += 0.032 * math.exp(-(aa / 0.55) ** 2) * tongue              # rounded tongue mound
        dz -= 0.005 * math.exp(-(aa / 0.075) ** 2) * tongue             # median groove
        dz += 0.011 * math.exp(-((aa - 0.975) / 0.05) ** 2)             # gum ridge under the tooth row
    inner = V((math.copysign(aa * 0.94 * 0.975 * w, a), lp.y, lz + dz * fold))
    if abs(a) <= 0.94:
        return inner
    # the last strip runs from the gum up (or down) into the jaw, ending 8 % inside the skin
    c = V((0, lp.y, lz))
    e = ring_point(s, PHI_M - (0.30 if upper else -0.30) * fold)
    e.x = math.copysign(abs(e.x), a)
    e = c + 0.92 * (e - c)
    tq = (abs(a) - 0.94) / 0.06
    return inner.lerp(e, tq)


su = [0.006 + (S_BACK - 0.006) * (i / (NU - 1)) ** 0.85 for i in range(NU)]
rows = [(s_, True) for s_ in su] + [(s_, False) for s_ in reversed(su[:-1])]
lv, lf, lpart, ljaw = [], [], [], []
for (s_, up) in rows:
    for k in range(NA):
        a = -1 + 2 * k / (NA - 1)
        lv.append(lining_point(s_, a, up))
        lpart.append(float(MOUTH) + (0.0 if up else 0.5))
        ljaw.append(0.0 if up else 1 - sstep(0.095, 0.128, s_))
for r_ in range(len(rows) - 1):
    for k in range(NA - 1):
        i0 = r_ * NA + k
        lf.append((i0, i0 + 1, i0 + NA + 1, i0 + NA))
lme = bpy.data.meshes.new("Mouth"); lme.from_pydata([tuple(v) for v in lv], [], lf)
bml = bmesh.new(); bml.from_mesh(lme); bml.faces.ensure_lookup_table()
# palate faces must face down into the cavity
f0 = bml.faces[(NU // 2) * (NA - 1) + NA // 2]
if f0.normal.z > 0:
    bmesh.ops.reverse_faces(bml, faces=bml.faces)
bml.to_mesh(lme); bml.free()
plug = bpy.data.objects.new("Mouth", lme); scene.collection.objects.link(plug)
for nm_, vals in (("part", lpart), ("jaw", ljaw)):
    att = lme.attributes.new(nm_, 'FLOAT', 'POINT'); att.data.foreach_set("value", vals)
for p_ in lme.polygons:
    p_.use_smooth = True

teeth = []
LIP_S = np.linspace(0.0, 0.2, 400)
LIP_W = np.array([lip_w(v) for v in LIP_S]); LIP_Z = np.array([lip_point(v).z for v in LIP_S])


def tooth(s, side, upper, size):
    """Conical tooth: round section, blunt tip, curving back and slightly inward; its root sits
    in the gum ridge.  size in 0..1 (smaller at the front and back of the row)."""
    lp = lip_point(s)
    lp.x *= side
    c = V((0, lp.y, lp.z))
    rad = (lp - c).length
    base = c + TOOTH_R * (lp - c) + V((0, 0, 0.014 if upper else -0.014))
    rb = min(0.0125, 0.058 * rad) * (0.72 + 0.28 * size)
    ln = 0.036 + 0.020 * size
    dv = V((0, 0, -1 if upper else 1))
    back, inward = V((0, 1, 0)), V((-side, 0, 0))

    def ctr(u):
        return base + dv * (ln * u) + back * (0.20 * ln * u * u) + inward * (0.10 * ln * u * u)
    US = [0.0, 0.18, 0.36, 0.54, 0.70, 0.83, 0.93]
    rs = []
    for u in US:
        tng = (ctr(min(u + 0.02, 1.0)) - ctr(max(u - 0.02, 0.0))).normalized()
        a_ = tng.orthogonal().normalized(); b_ = tng.cross(a_)
        r = rb * (1 - u) ** 0.62 * (1.0 + 0.05 * (1 - u))
        cc = ctr(u)
        rs.append([cc + a_ * (r * math.cos(2 * math.pi * q / 10)) + b_ * (r * math.sin(2 * math.pi * q / 10)) for q in range(10)])
    ob = mesh_from_rings("Tooth", rs, TEETH + (0.0 if upper else 0.5), cap_start=base - dv * 0.006,
                         cap_end=ctr(1.0))
    for p_ in ob.data.polygons:
        p_.use_smooth = True
    teeth.append(ob)


NT_UP, NT_LO = 12, 11
for side in (1, -1):
    for i in range(NT_UP):                       # upper row
        tooth(0.024 + 0.070 * i / (NT_UP - 1), side, True, math.sin(math.pi * (i + 0.6) / (NT_UP + 0.2)) ** 0.7)
    for i in range(NT_LO):                       # lower row sits in the gaps (interlocking)
        tooth(0.024 + 0.070 * (i + 0.5) / (NT_UP - 1), side, False, math.sin(math.pi * (i + 0.6) / (NT_LO + 0.2)) ** 0.7)

# ======================================================================= 3. eyes
eyes = []
EYE_FRAMES = {}
for s in (1, -1):
    ys = Y0 + L * EYE_S
    zc = hermite(KEYS[3], EYE_S)
    d = V((s * math.sin(EYE_PHI), 0, math.cos(EYE_PHI)))
    hit, nrm = surface(V((0, ys, zc)) + d * 2.0, -d)
    ctr = hit - nrm * EYE_R * 0.62
    EYE_FRAMES[s] = (ctr.copy(), nrm.copy(), hit.copy())
    me = bpy.data.meshes.new("Eye"); bmx = bmesh.new()
    bmesh.ops.create_uvsphere(bmx, u_segments=24, v_segments=16, radius=EYE_R, matrix=Matrix.Translation(ctr))
    bmx.to_mesh(me); bmx.free()
    ob = bpy.data.objects.new("Eye", me); scene.collection.objects.link(ob)
    for nm_, val in (("part", float(EYE)), ("jaw", 0.0)):
        att = me.attributes.new(nm_, 'FLOAT', 'POINT')
        att.data.foreach_set("value", [val] * len(me.vertices))
    for p in me.polygons:
        p.use_smooth = True
    eyes.append(ob)
    # eyelids: an almond-shaped skirt draped over the skin (each profile point is ray-cast onto the
    # sculpted head) - its outer edge tucks tangentially under the skin, a soft ridge forms the lid
    # margin and its inner edge rolls down into the eyeball
    t1 = V((0, 1, 0)); t1 = (t1 - t1.dot(nrm) * nrm).normalized()
    t2 = nrm.cross(t1).normalized()
    a_, b_ = EYE_R * 1.22, EYE_R * 0.86                         # lid margin (ridge) ellipse
    W, Hh = 0.024, 0.0075
    PROF = [(1.00, -0.0025), (0.70, 0.18), (0.42, 0.55), (0.18, 0.88), (0.0, 1.0), (-0.16, 0.82),
            (-0.30, 0.45), (-0.40, -0.1), (-0.46, -0.8)]
    NT = 32
    lv, lf = [], []
    for i_ in range(NT):
        th = 2 * math.pi * i_ / NT
        ca, sa = math.cos(th), math.sin(th)
        corner = 1 + 0.10 * ca * ca                               # slightly pointed canthi
        e = t1 * (a_ * ca * corner) + t2 * (b_ * sa)
        radial = (t1 * (b_ * ca) + t2 * (a_ * sa)).normalized()
        heavy = 1.0 + 0.45 * max(0.0, sa)                         # heavier upper lid
        for (rq, hq) in PROF:
            q = hit + e + radial * (W * rq)
            hc, _ = surface(q + nrm * 0.08, -nrm)
            base_ = hc if hc is not None else q
            lv.append(base_ + nrm * (Hh * heavy * hq))
    npf = len(PROF)
    for i_ in range(NT):
        i2 = (i_ + 1) % NT
        for k_ in range(npf - 1):
            lf.append((i_ * npf + k_, i2 * npf + k_, i2 * npf + k_ + 1, i_ * npf + k_ + 1))
    lme = bpy.data.meshes.new("Lid"); lme.from_pydata([tuple(v_) for v_ in lv], [], lf)
    bml = bmesh.new(); bml.from_mesh(lme)
    bmesh.ops.recalc_face_normals(bml, faces=bml.faces)
    # outward = along the eye normal
    if sum((f.normal.dot(nrm)) for f in bml.faces) < 0:
        bmesh.ops.reverse_faces(bml, faces=bml.faces)
    bml.to_mesh(lme); bml.free()
    lid = bpy.data.objects.new("Lid", lme); scene.collection.objects.link(lid)
    for nm_, val in (("part", float(BODY)), ("jaw", 0.0)):
        att = lme.attributes.new(nm_, 'FLOAT', 'POINT')
        att.data.foreach_set("value", [val] * len(lme.vertices))
    subdivide(lid, 1)
    eyes.append(lid)


# ======================================================================= 4. dorsal fin
def dorsal_le(h):
    return -0.82 + 0.80 * h ** 1.15


def dorsal_te(h):
    # slightly concave, gently wavy trailing edge
    return 0.14 - 0.10 * h - 0.06 * math.sin(math.pi * h) + 0.010 * math.sin(7.0 * math.pi * h) * math.sin(math.pi * h)


DORSAL_Z0, DORSAL_H = 0.48, 1.22


def airfoil(p):
    """Thickness distribution along the chord (0 = leading edge), peak 1.0 at p ~ 0.3,
    thinning to a knife-like trailing edge."""
    return 2.6 * math.sqrt(max(p, 0.0)) * (1 - p) ** 1.25


rs = []
for i in range(22):
    h = i / 21 * 0.985
    z = DORSAL_Z0 + DORSAL_H * h
    le, te = dorsal_le(h), dorsal_te(h)
    T = 0.11 * (1 - h) + 0.014 + 0.16 * math.exp(-(h / 0.10) ** 2)   # flared root blends into the back
    ring = []
    for j in range(20):
        ph = 2 * math.pi * j / 20
        p = 0.5 - 0.5 * math.cos(ph)
        ring.append(V((math.copysign(0.5 * T * airfoil(p), math.sin(ph)) if abs(math.sin(ph)) > 1e-6 else 0.0,
                       le + p * (te - le), z)))
    rs.append(ring)
dorsal = mesh_from_rings("Dorsal", rs, DORSAL, cap_start=V((0, -0.34, DORSAL_Z0 - 0.02)),
                         cap_end=V((0, 0.02, DORSAL_Z0 + DORSAL_H * 1.0)))
subdivide(dorsal, 1)

# ======================================================================= 5. pectoral fins
PEC_LEN = 0.95
PEC_S, PEC_PHI = 0.21, 2.20
pec_frames = {}


def pectoral(s):
    root = ring_point(PEC_S, PEC_PHI); root.x *= s
    axis_c = V((0, root.y, hermite(KEYS[3], PEC_S)))
    shoulder = root + (axis_c - root).normalized() * 0.07
    down = V((s * 0.62, 0.55, -0.56)).normalized()
    fwd = V((0, -1, 0.25)); fwd = (fwd - fwd.dot(down) * down).normalized()
    thick = down.cross(fwd).normalized() * s
    WK = [(0.0, 0.28), (0.12, 0.38), (0.42, 0.52), (0.72, 0.50), (0.90, 0.36), (1.0, 0.12)]
    rs = []
    for i in range(18):
        u = i / 17
        w = hermite(WK, u)
        t = 0.10 * (1 - u) + 0.022
        c = shoulder + down * (PEC_LEN * u)
        ring = []
        for j in range(20):
            ph = 2 * math.pi * j / 20
            a, b = math.cos(ph), math.sin(ph)
            lead = a > 0
            ww = w * (0.45 if lead else 0.55)
            tt = t * (1.0 if lead else 0.6 + 0.4 * (1 + a))
            # four faint digit ridges running down the paddle
            ridge = 1 + 0.16 * max(0.0, math.cos(4 * math.pi * a)) * sstep(0.08, 0.2, u) * (1 - sstep(0.7, 0.9, u))
            ring.append(c + fwd * (ww * a) + thick * (tt * ridge * b * 0.5))
        rs.append(ring)
    tip = shoulder + down * (PEC_LEN * 1.03)
    ob = mesh_from_rings("Pectoral", rs, PECTORAL, cap_start=shoulder - down * 0.02, cap_end=tip)
    subdivide(ob, 1)
    pec_frames[s] = (shoulder, down, fwd, thick)
    return ob


pectorals = [pectoral(1), pectoral(-1)]

# ======================================================================= 6. flukes
FLUKE_SPAN = 0.75
FLUKE_Z = PROFILE[-1][4]


def fluke_le(u):
    return 2.47 + 0.61 * u ** 1.6


def fluke_te(u):
    return 2.86 + 0.34 * u - 0.12 * u ** 3 - 0.035 * math.exp(-(u / 0.06) ** 2)   # median notch at u = 0


rs = []
NF = 31
for i in range(NF):
    v = -1 + 2 * i / (NF - 1)
    x = FLUKE_SPAN * 0.985 * math.sin(0.5 * math.pi * v)
    u = abs(x) / FLUKE_SPAN
    le, te = fluke_le(u), fluke_te(u)
    T = 0.10 * (1 - u) ** 0.8 + 0.012
    ring = []
    for j in range(20):
        ph = 2 * math.pi * j / 20
        p = 0.5 - 0.5 * math.cos(ph)
        sn = math.sin(ph)
        droop = -0.06 * u ** 2.2
        ring.append(V((x, le + p * (te - le), FLUKE_Z + droop + (math.copysign(0.5 * T * airfoil(p), sn) if abs(sn) > 1e-6 else 0.0))))
    rs.append(ring)
flukes = mesh_from_rings("Flukes", rs, FLUKE, cap_start=V((-FLUKE_SPAN * 1.025, 3.09, FLUKE_Z - 0.062)),
                         cap_end=V((FLUKE_SPAN * 1.025, 3.09, FLUKE_Z - 0.062)))
subdivide(flukes, 1)

# ======================================================================= join
# fin-root junction points: fin vertices lying on the body surface (used to hide the seams)
JUNC = []
for fo, rad_ in ((dorsal, 0.012), (flukes, 0.010), (pectorals[0], 0.012), (pectorals[1], 0.012)):
    for v in fo.data.vertices:
        hit_ = bvh_body.find_nearest(v.co)
        if hit_[0] is not None and hit_[3] < rad_:
            JUNC.append(tuple(v.co))
JUNC = np.array(JUNC)
print("[build] fin-root junction points", len(JUNC))

objs = [body, plug, dorsal, flukes] + eyes + pectorals + teeth
for o in bpy.context.view_layer.objects:
    o.select_set(o in objs)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
orca = body
orca.name = "Orca"; orca.data.name = "Orca"
me = orca.data
print("[build] mesh verts", len(me.vertices), "faces", len(me.polygons), "body rings", NR)

nv_ = len(me.vertices)
co_ = np.zeros(nv_ * 3, np.float32); me.vertices.foreach_get("co", co_); co_ = co_.reshape(-1, 3)
pa_ = np.zeros(nv_, np.float32); me.attributes["part"].data.foreach_get("value", pa_)
# 'micro' mask for the pore / stretch bump: sparse on the smooth wet head, full on the body and fins
sv_ = (co_[:, 1] - Y0) / L
micro_ = np.where(pa_ < 0.5, 0.12 + 0.88 * smoothstep(0.16, 0.30, sv_), 0.0)
micro_ = np.where((pa_ > 0.5) & (pa_ < 3.5), 0.8, micro_)
att = me.attributes.new("micro", 'FLOAT', 'POINT'); att.data.foreach_set("value", micro_.astype(np.float32))

# fin-root seams: bend the fin normals toward the body normal where the fins enter the body, so the
# junction shades like one continuous surface (custom normals, exported with the glTF)
me.update()
vn_ = np.zeros(nv_ * 3, np.float32); me.vertex_normals.foreach_get("vector", vn_); vn_ = vn_.reshape(-1, 3)
fins_ = (pa_ > 0.5) & (pa_ < 3.5)
for vi in np.nonzero(fins_)[0]:
    hit_ = bvh_body.find_nearest(V(co_[vi]))
    if hit_[0] is None:
        continue
    reach = 0.035 if abs(pa_[vi] - FLUKE) < 0.5 else 0.08
    f_ = 1 - sstep(0.0, reach, hit_[3])
    if f_ > 0:
        n_ = V(vn_[vi]) * (1 - f_) + hit_[1].normalized() * f_
        vn_[vi] = n_.normalized()
try:
    me.normals_split_custom_set_from_vertices([tuple(n_) for n_ in vn_])
    print("[build] custom normals set on fin roots")
except Exception as ex:
    print("[build] custom normals failed:", ex)

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.003, area_weight=0.0,
                         scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT')
me.uv_layers[0].name = "UVMap"

# ======================================================================= textures
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 1
scene.render.bake.margin = 24
scene.render.bake.margin_type = 'EXTEND'

mat = bpy.data.materials.new("Orca_Skin")
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


for o in bpy.context.view_layer.objects:
    o.select_set(o == orca)
bpy.context.view_layer.objects.active = orca

LO, SPAN = V((-3.4, -3.4, -3.4)), 6.8


def pos_socket():
    tc = nodes.new("ShaderNodeTexCoord")
    mp = nodes.new("ShaderNodeVectorMath"); mp.operation = 'MULTIPLY_ADD'
    links.new(tc.outputs["Object"], mp.inputs[0])
    mp.inputs[1].default_value = (1 / SPAN,) * 3
    mp.inputs[2].default_value = tuple(-c / SPAN for c in LO)
    return mp.outputs[0]


def nrm_socket():
    g = nodes.new("ShaderNodeNewGeometry")
    tr = nodes.new("ShaderNodeVectorTransform"); tr.vector_type = 'NORMAL'
    tr.convert_from = 'WORLD'; tr.convert_to = 'OBJECT'
    links.new(g.outputs["Normal"], tr.inputs[0])
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
    """R: broad mottling, G: long thin streaks along the body (scars), B: medium."""
    tc = nodes.new("ShaderNodeTexCoord")
    c = nodes.new("ShaderNodeCombineColor")
    specs = [(1.6, (1, 1, 1), 3.0), (9.0, (3.0, 0.35, 3.0), 2.0), (5.0, (1, 1, 1), 4.0)]
    for k, (sc, stretch, det) in enumerate(specs):
        vm = nodes.new("ShaderNodeVectorMath"); vm.operation = 'MULTIPLY'
        links.new(tc.outputs["Object"], vm.inputs[0]); vm.inputs[1].default_value = stretch
        nz = nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = sc
        nz.inputs["Detail"].default_value = det
        links.new(vm.outputs[0], nz.inputs["Vector"])
        links.new(nz.outputs["Fac"], c.inputs[k])
    return c.outputs[0]


def noise2_socket():
    """R: fine mottling, G: voronoi specks, B: warp noise for striations / stretch lines."""
    tc = nodes.new("ShaderNodeTexCoord")
    c = nodes.new("ShaderNodeCombineColor")
    nz = nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 22; nz.inputs["Detail"].default_value = 5
    links.new(tc.outputs["Object"], nz.inputs["Vector"]); links.new(nz.outputs["Fac"], c.inputs[0])
    vo = nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 40
    links.new(tc.outputs["Object"], vo.inputs["Vector"]); links.new(vo.outputs["Distance"], c.inputs[1])
    nw = nodes.new("ShaderNodeTexNoise"); nw.inputs["Scale"].default_value = 6; nw.inputs["Detail"].default_value = 2
    links.new(tc.outputs["Object"], nw.inputs["Vector"]); links.new(nw.outputs["Fac"], c.inputs[2])
    return c.outputs[0]


px_pos = bake_emit(pos_socket, new_image("_pos", True))
px_nrm = bake_emit(nrm_socket, new_image("_nrm", True))
px_part = bake_emit(part_socket, new_image("_part", True))
px_noise = bake_emit(noise_socket, new_image("_noise", True))
px_noise2 = bake_emit(noise2_socket, new_image("_noise2", True))

for n in list(nodes):
    nodes.remove(n)
out = nodes.new("ShaderNodeOutputMaterial"); bs = nodes.new("ShaderNodeBsdfDiffuse")
links.new(bs.outputs[0], out.inputs[0])
ao_img = new_image("_ao", True, (1, 1, 1, 1)); tn = nodes.new("ShaderNodeTexImage"); tn.image = ao_img
nodes.active = tn
scene.cycles.samples = 48
scene.world = bpy.data.worlds.new("BakeWorld")
scene.render.bake.use_selected_to_active = False
bpy.ops.object.bake(type='AO')
px_ao = np.array(ao_img.pixels[:], dtype=np.float32).reshape(RES, RES, 4)[..., 0]
print("[build] baked position / normal / part / noise / AO")

# ----------------------------------------------------------------------- paint the pattern
P = px_pos[..., :3] * SPAN + np.array(LO)
x, y, z = P[..., 0], P[..., 1], P[..., 2]
N = px_nrm[..., :3] * 2 - 1
part = np.rint(px_part[..., 0] * 10 * 2) / 2
n_broad, n_streak, n_med = px_noise[..., 0], px_noise[..., 1], px_noise[..., 2]
n_fine, n_vor, n_warp = px_noise2[..., 0], px_noise2[..., 1], px_noise2[..., 2]
is_body = part == BODY

s = (y - Y0) / L
hw_t, top_t, bot_t, zc = prof_np(s)
ang = np.arctan2(np.abs(x), z - zc)               # 0 on top, pi under the belly (geometric)
rad_t = np.hypot(x, z - zc)


def col(*c):
    return np.array(c, dtype=np.float32)


def mix(a, b, t):
    t = np.asarray(t, dtype=np.float32)[..., None]
    return a * (1 - t) + b * t


BLACK = col(0.084, 0.087, 0.094)     # charcoal with a cool blue-grey cast (sRGB values)
WHITE = col(0.86, 0.87, 0.86)
DIATOM = col(0.90, 0.84, 0.66)
SADDLE = col(0.42, 0.43, 0.46)
SCAR = col(0.30, 0.31, 0.33)

jit = (n_med - 0.5) * 0.05 + (n_fine - 0.5) * 0.015
# ---- white underside: lower jaw from the lip line, throat narrowing between the flippers,
#      belly, and the flank lobes sweeping up and back behind the dorsal fin
THR = [(0.00, PHI_M + 0.05), (0.095, PHI_M + 0.05), (0.125, 1.90), (0.16, 2.15), (0.205, 2.55), (0.25, 2.76),
       (0.30, 2.74), (0.36, 2.52), (0.44, 2.30), (0.51, 2.12), (0.555, 1.90), (0.585, 1.58), (0.608, 1.30),
       (0.630, 1.14), (0.652, 1.10), (0.675, 1.20), (0.70, 1.46), (0.73, 1.90), (0.76, 2.42), (0.785, 2.90),
       (0.805, 3.40), (1.0, 3.40)]
thr = hermite_np(THR, np.clip(s, 0, 1))
edge_w = np.where(s > 0.12, 0.012, 0.022)          # wider on the head: texel density is lower there
white = smoothstep(thr - edge_w, thr + edge_w, ang + jit * (s > 0.12))

# ---- eye patch: an elongated teardrop above and behind the eye, tapering forward
a = math.radians(15)
EPC = (Y0 + L * 0.178, 0.170)
dy, dz = y - EPC[0], z - EPC[1]
ey = dy * math.cos(a) + dz * math.sin(a)
ez = -dy * math.sin(a) + dz * math.cos(a)
tq = ey / 0.325                                    # ~0.65 m long, ~0.145 m tall (4.5 : 1 flat, ~3.5 : 1 on the curved head)
half_h = (0.072 / 0.84) * np.sqrt(np.clip(1 - tq * tq, 0, 1)) * np.clip((tq + 1) / 2, 0, 1) ** 0.30
eyep = smoothstep(0.005, -0.005, np.abs(ez) - half_h + jit * 0.15) * (np.abs(tq) < 1)
eyep = eyep * smoothstep(0.2, 0.45, np.abs(N[..., 0])) * (x * np.sign(x) > 0.05)
white = np.maximum(white, eyep)

# ---- dark skin: darker along the spine, lighter mottling low on the flanks
spine = 0.55 + 0.45 * smoothstep(0.05, 1.45, ang)
mott = smoothstep(0.50, 0.78, n_broad) * smoothstep(0.6, 1.6, ang) * (0.5 + 0.5 * n_fine)
speck = smoothstep(0.10, 0.02, n_vor) * 0.5
dark = BLACK * (spine * (0.80 + 0.40 * n_med) * (0.92 + 0.16 * n_fine))[..., None]
dark = dark + col(0.055, 0.060, 0.072) * mott[..., None] + col(0.03, 0.03, 0.035) * speck[..., None]
dark_fin = BLACK * (0.80 + 0.35 * n_med + 0.2 * n_fine)[..., None]

# ---- grey saddle: hugs the fin's trailing base, feathered edges, striations sweeping back-down
ds = s - 0.520 + 0.018 * ang
feather = smoothstep(-0.006, 0.040, ds + 0.4 * jit) * (1 - smoothstep(0.07, 0.15, ds + 0.5 * jit - 0.03 * ang))
vert = 1 - smoothstep(0.85, 1.45, ang + 0.8 * jit)
stri = smoothstep(0.35, 0.75, n_streak) * (0.6 + 0.4 * n_fine)
saddle = feather * vert
dark = mix(dark, SADDLE * (0.88 + 0.10 * stri + 0.18 * (n_med - 0.5))[..., None], 0.95 * saddle * (0.88 + 0.12 * stri))

# ---- rake-mark scars: sparse parallel pairs / triplets of pale thin lines on the flanks
rng = np.random.default_rng(11)
scar_m = np.zeros_like(x)
arc = ang * rad_t
bodyside = is_body & (s > 0.12) & (s < 0.86)
for k in range(22):
    sd = 1 if k % 2 else -1
    yc = Y0 + L * rng.uniform(0.16, 0.82)
    ac = rng.uniform(0.35, 1.9) * float(np.interp((yc - Y0) / L, S_TAB, P_TAB[:, 0])) * 1.1
    th = math.radians(rng.uniform(-60, 60) + (0 if rng.random() < 0.7 else 90))
    ln = rng.uniform(0.22, 0.60)
    nl = int(rng.integers(2, 5))
    sp = rng.uniform(0.025, 0.045)
    wd = rng.uniform(0.0016, 0.0030)
    dvec = (math.cos(th), math.sin(th)); nvec = (-dvec[1], dvec[0])
    box = bodyside & (np.sign(x) == sd) & (np.abs(y - yc) < ln) & (np.abs(arc - ac) < ln)
    if not box.any():
        continue
    yy, aa = y[box] - yc, arc[box] - ac
    along_ = yy * dvec[0] + aa * dvec[1]
    across = yy * nvec[0] + aa * nvec[1]
    m = np.zeros(len(yy))
    for li in range(nl):
        off = (li - (nl - 1) / 2) * sp
        l2 = ln * 0.5 * (1 - 0.25 * abs(li - (nl - 1) / 2))
        taper = np.clip(1 - np.abs(along_ + off * 0.3) / l2, 0, 1) ** 0.5
        m = np.maximum(m, (1 - smoothstep(wd * 0.5, wd * 1.4, np.abs(across - off))) * taper)
    scar_m[box] = np.maximum(scar_m[box], m * rng.uniform(0.35, 0.8))
# plus a few faint long streaks
scar_m = np.maximum(scar_m, 0.35 * (1 - smoothstep(0.0, 0.010, np.abs(n_streak - 0.5))) * smoothstep(0.6, 0.72, n_broad) * bodyside * (s > 0.24))

light = mix(WHITE, DIATOM, 0.35 * smoothstep(0.42, 0.78, n_broad) + 0.15 * smoothstep(0.6, 0.9, n_vor))
light = light * (0.94 + 0.08 * n_med + 0.03 * n_fine)[..., None]
c_body = mix(dark, light, white)
c_body = mix(c_body, SCAR, 0.55 * scar_m * (1 - white))
c_body = mix(c_body, col(0.55, 0.55, 0.55), 0.35 * scar_m * white)
# genital / umbilical slits: thin dark marks on the white belly
slit = g(x, 0.0, 0.005) * smoothstep(0.600, 0.612, s) * (1 - smoothstep(0.640, 0.652, s)) * (ang > 2.8)
umb = g(np.hypot(x, y - (Y0 + L * 0.50)), 0.0, 0.007) * (ang > 2.8)
c_body = mix(c_body, col(0.30, 0.27, 0.27), 0.55 * np.maximum(slit, umb))
# blowhole slit: dark inside the crescent
bv = blow_v(x, y)
bslit = g(bv, 0.0, 0.0065) * (1 - smoothstep(0.07, 0.105, np.abs(x))) * (ang < 0.6)
c_body = mix(c_body, col(0.004, 0.004, 0.006), 0.8 * bslit)

# ---- flukes: black above, white below with a black margin, black leading edge
u = np.clip(np.abs(x) / FLUKE_SPAN, 0, 1)
inside = np.minimum(y - (2.47 + 0.61 * u ** 1.6), (2.86 + 0.34 * u - 0.12 * u ** 3 - 0.035 * np.exp(-(u / 0.06) ** 2)) - y)
fw = smoothstep(0.1, -0.1, N[..., 2]) * smoothstep(0.035, 0.055, inside + 0.01 * (n_med - 0.5)) \
    * (1 - smoothstep(0.76, 0.84, u)) * smoothstep(2.66, 2.72, y)
c_fluke = mix(dark_fin, light, fw)

# ---- eyes: dark brown iris, black pupil, dusky sclera
c_eye = np.zeros_like(P, dtype=np.float32)
for sd, (ec, en, eh) in EYE_FRAMES.items():
    dv = P - np.array(ec)
    dv /= np.maximum(np.linalg.norm(dv, axis=-1, keepdims=True), 1e-6)
    ca = dv @ np.array(en)
    iris = smoothstep(0.80, 0.84, ca)
    pupil = smoothstep(0.955, 0.965, ca)
    sclera = mix(col(0.30, 0.27, 0.25), col(0.12, 0.09, 0.07), smoothstep(0.6, 0.8, ca))
    irc = mix(col(0.16, 0.09, 0.05), col(0.07, 0.04, 0.025), smoothstep(0.84, 0.95, ca)) * (0.85 + 0.3 * n_fine[..., None])
    ce = mix(mix(sclera, irc, iris), col(0.004, 0.004, 0.004), pupil)
    sel = (np.sign(x) == sd)
    c_eye[sel] = ce[sel]

# ---- mouth: palate with transverse ridges, lighter gums, pink tongue, near-black throat
s_c = np.clip(s, 0, 0.2)
w_s = np.interp(s_c, LIP_S, LIP_W); lz_s = np.interp(s_c, LIP_S, LIP_Z)
a_m = np.abs(x) / np.maximum(w_s, 1e-3)
is_pal = np.abs(part - MOUTH) < 0.01
is_flr = np.abs(part - (MOUTH + 0.5)) < 0.01
depth = smoothstep(0.045, S_BACK, s)
pal_r = (0.5 + 0.5 * np.sin(2 * np.pi * (y - Y0) / 0.024)) * (1 - smoothstep(0.55, 0.8, a_m)) * (1 - depth)
gum = g(a_m, 0.905, 0.05)
tongue_m = (1 - smoothstep(0.45, 0.75, a_m))
c_mouth = mix(col(0.60, 0.33, 0.36), col(0.72, 0.42, 0.45), 0.35 * pal_r)              # palate
c_mouth = np.where(is_flr[..., None], mix(col(0.56, 0.24, 0.28), col(0.66, 0.30, 0.33), tongue_m * n_med)[...] , c_mouth)
c_mouth = mix(c_mouth, col(0.80, 0.56, 0.56), 0.75 * gum)                            # gums, lighter pink
c_mouth = mix(c_mouth, col(0.16, 0.12, 0.13), smoothstep(0.94, 0.99, a_m))           # pigmented inner lip
c_mouth = mix(c_mouth, col(0.035, 0.012, 0.016), depth ** 1.3)                        # dark throat
c_mouth = c_mouth * (0.9 + 0.15 * n_fine[..., None])
# ---- teeth: ivory, yellower at the gum line, worn paler tips, per-tooth variation
tt_up = np.clip(((lz_s + 0.014) - z) / 0.055, 0, 1)
tt_lo = np.clip((z - (lz_s - 0.014)) / 0.055, 0, 1)
tt = np.where(part > TEETH + 0.25, tt_lo, tt_up)
c_teeth = mix(col(0.70, 0.60, 0.42), col(0.90, 0.86, 0.74), smoothstep(0.15, 0.55, tt))
c_teeth = mix(c_teeth, col(0.84, 0.83, 0.78), smoothstep(0.75, 1.0, tt))
c_teeth = c_teeth * (0.90 + 0.14 * n_med[..., None]) * (0.95 + 0.08 * n_fine[..., None])

# ---- fin-root junctions: body colour and a lifted AO blend across the seam
junc = np.zeros_like(x)
finbody = (part < 3.5)
if len(JUNC):
    jlo, jhi = JUNC.min(0) - 0.12, JUNC.max(0) + 0.12
    sel = finbody & np.all((P > jlo) & (P < jhi), axis=-1)
    idx = np.nonzero(sel)
    Q = P[idx]
    dmin = np.full(len(Q), 9.0, np.float32)
    for c0 in range(0, len(Q), 16000):
        qq = Q[c0:c0 + 16000]
        dmin[c0:c0 + 16000] = np.sqrt(((qq[:, None, :] - JUNC[None, :, :]) ** 2).sum(-1).min(1))
    junc[idx] = 1 - smoothstep(0.0, 0.10, dmin)
dark_fin_j = mix(dark_fin, dark, junc)
c_fluke = mix(c_fluke, dark, junc * (1 - fw))

base = c_body.copy()
for pid, cc in ((DORSAL, dark_fin_j), (PECTORAL, dark_fin_j), (FLUKE, c_fluke), (EYE, c_eye), (MOUTH, c_mouth),
                (MOUTH + 0.5, c_mouth), (TEETH, c_teeth), (TEETH + 0.5, c_teeth)):
    m = part == pid
    base[m] = (cc if cc.ndim == 1 else cc[m])
ao = np.clip(px_ao, 0, 1)
ao = ao + (np.maximum(ao, 0.92) - ao) * junc                                   # no dark contact line at fin roots
inmouth = (part >= MOUTH - 0.01) & (part <= TEETH + 0.51)                      # closed-pose AO would blacken the open mouth
ao = np.where(inmouth, 0.9 + 0.1 * ao, ao)
base = base * (0.55 + 0.45 * ao)[..., None]
base = np.clip(base, 0, 1)

# ---- roughness: wet glossy skin, dryer along the back, glassy eye
rough = 0.26 + 0.08 * (n_med - 0.5) + 0.05 * (n_fine - 0.5)
rough = rough + 0.10 * (1 - smoothstep(0.2, 1.0, ang)) * (is_body | (part == DORSAL))
rough = rough + 0.04 * white + 0.10 * scar_m + 0.45 * bslit
rough = rough + 0.14 * smoothstep(0.55, 0.80, n_broad) * smoothstep(0.4, 0.7, n_fine) * (is_body | (part == DORSAL))  # drier matte patches
rough = np.where(part == EYE, 0.03, rough)
rough = np.where(is_pal | is_flr, 0.24 + 0.06 * gum + 0.04 * n_fine, rough)
rough = np.where((part == TEETH) | (part == TEETH + 0.5), 0.32, rough)
rough = rough.astype(np.float32)

# ---- height map for the normal bake: wrinkles, creases, scars and slits
H = np.zeros_like(x)
# eye: crow's-feet radiating from the corners plus fine concentric creases
for sd, (ec, en, eh) in EYE_FRAMES.items():
    dv = P - np.array(eh)
    r = np.linalg.norm(dv, axis=-1)
    th = np.arctan2(dv[..., 2], dv[..., 1] * sd * 0 + dv[..., 1])
    win = smoothstep(0.036, 0.046, r) * (1 - smoothstep(0.065, 0.10, r)) * (np.sign(x) == sd)
    brk = smoothstep(0.35, 0.65, n_fine)
    H += 0.45 * win * brk * np.sin(r * 2 * np.pi / 0.012 + 8 * n_warp + 3 * np.sin(th * 3))
# blowhole: concentric creases fanning behind the crescent
bw = (1 - smoothstep(0.10, 0.16, np.abs(x))) * (ang < 0.8)
H += 0.5 * bw * smoothstep(0.03, 0.045, bv) * (1 - smoothstep(0.07, 0.12, bv)) * smoothstep(0.3, 0.6, n_fine) \
    * np.sin(bv * 2 * np.pi / 0.016 + 7 * n_warp)
H -= 0.5 * bslit
# jaw corner: creases radiating back from the gape
for sd in (1, -1):
    kc = lip_point(S_CORNER)
    dyk, dzk = y - kc.y, z - kc.z
    r = np.hypot(dyk, dzk); th = np.arctan2(dzk, dyk)
    win = smoothstep(0.015, 0.03, r) * (1 - smoothstep(0.10, 0.17, r)) * smoothstep(-0.02, 0.02, dyk) * (np.sign(x) == sd) * is_body
    H += 0.55 * win * smoothstep(0.3, 0.6, n_fine) * np.sin(th * 20 + 9 * n_warp)
# pectoral armpit: folds around the flipper root
for sd in (1, -1):
    sh = pec_frames[sd][0]
    r = np.linalg.norm(P - np.array(sh), axis=-1)
    win = smoothstep(0.08, 0.14, r) * (1 - smoothstep(0.26, 0.36, r)) * (np.sign(x) == sd) * is_body
    H += 0.5 * win * smoothstep(0.35, 0.65, n_fine) * np.sin(r * 2 * np.pi / 0.035 + 9 * n_warp)
# throat folds and belly grooves
H += 0.5 * np.cos(2 * np.pi * x / 0.085) * smoothstep(0.12, 0.15, s) * (1 - smoothstep(0.22, 0.28, s)) * smoothstep(2.35, 2.75, ang) * is_body
H -= 1.2 * np.maximum(slit, umb)
# scars are slightly raised
H += 0.6 * scar_m
# faint skin stretch lines along the body
H += 0.22 * (1 - smoothstep(0.0, 0.02, np.abs(n_streak - 0.5))) * is_body * smoothstep(0.22, 0.32, s)  # sparse long stretch creases
H += (is_pal * 0.9 * (pal_r - 0.5) + is_flr * 0.6 * tongue_m * (smoothstep(0.12, 0.0, n_vor) - 0.3)) * (1 - depth)
H[(part == EYE) | (part == TEETH) | (part == TEETH + 0.5)] = 0.0
H = H.astype(np.float32)


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
    return img


img_base = save("Orca_BaseColor", base, 'sRGB')
orm = np.stack([0.35 + 0.65 * ao, np.clip(rough, 0, 1), np.zeros_like(ao)], -1)
img_orm = save("Orca_ORM", orm, 'Non-Color')

# ----------------------------------------------------------------------- skin normal map
img_h = new_image("_height", True)
img_h.colorspace_settings.name = 'Non-Color'
hr = np.zeros((RES, RES, 4), np.float32); hr[..., 0] = hr[..., 1] = hr[..., 2] = H; hr[..., 3] = 1
img_h.pixels.foreach_set(hr.ravel())
for n in list(nodes):
    nodes.remove(n)
out = nodes.new("ShaderNodeOutputMaterial")
bsdf = nodes.new("ShaderNodeBsdfPrincipled")
links.new(bsdf.outputs[0], out.inputs[0])
th_ = nodes.new("ShaderNodeTexImage"); th_.image = img_h; th_.interpolation = 'Cubic'
tc = nodes.new("ShaderNodeTexCoord")
# micro-pores + fine stretch texture (procedural, object space)
vm = nodes.new("ShaderNodeVectorMath"); vm.operation = 'MULTIPLY'; vm.inputs[1].default_value = (1, 0.25, 1)
links.new(tc.outputs["Object"], vm.inputs[0])
wr = nodes.new("ShaderNodeTexNoise"); wr.inputs["Scale"].default_value = 45; wr.inputs["Detail"].default_value = 4
links.new(vm.outputs[0], wr.inputs["Vector"])
vo = nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 340
links.new(tc.outputs["Object"], vo.inputs["Vector"])
micro = nodes.new("ShaderNodeMath"); micro.operation = 'MULTIPLY_ADD'; micro.inputs[1].default_value = 0.6
links.new(wr.outputs["Fac"], micro.inputs[0]); links.new(vo.outputs["Distance"], micro.inputs[2])
att = nodes.new("ShaderNodeAttribute"); att.attribute_name = "micro"      # ~0 on head / eyes / mouth
skin = nodes.new("ShaderNodeMath"); skin.operation = 'MULTIPLY'; skin.inputs[1].default_value = 0.16
links.new(att.outputs["Fac"], skin.inputs[0])
mm = nodes.new("ShaderNodeMath"); mm.operation = 'MULTIPLY'
links.new(micro.outputs[0], mm.inputs[0]); links.new(skin.outputs[0], mm.inputs[1])
hsum = nodes.new("ShaderNodeMath"); hsum.operation = 'ADD'
links.new(th_.outputs["Color"], hsum.inputs[0]); links.new(mm.outputs[0], hsum.inputs[1])
bump = nodes.new("ShaderNodeBump"); bump.inputs["Distance"].default_value = 0.0010
bump.inputs["Strength"].default_value = 1.0
links.new(hsum.outputs[0], bump.inputs["Height"])
links.new(bump.outputs[0], bsdf.inputs["Normal"])
img_n = new_image("_normal", False, (0.5, 0.5, 1, 1)); img_n.colorspace_settings.name = 'Non-Color'
tn = nodes.new("ShaderNodeTexImage"); tn.image = img_n; nodes.active = tn
scene.cycles.samples = 1
bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT')
img_n.filepath_raw = os.path.join(TEX, "Orca_Normal.png"); img_n.file_format = 'PNG'
img_n.save()
img_nrm = bpy.data.images.load(os.path.join(TEX, "Orca_Normal.png")); img_nrm.colorspace_settings.name = 'Non-Color'
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
nm = nodes.new("ShaderNodeNormalMap"); nm.location = (-100, -300)
links.new(t_base.outputs[0], bsdf.inputs["Base Color"])
links.new(t_orm.outputs[0], sep.inputs[0])
links.new(sep.outputs[1], bsdf.inputs["Roughness"])
links.new(sep.outputs[2], bsdf.inputs["Metallic"])
links.new(t_n.outputs[0], nm.inputs["Color"])
links.new(nm.outputs[0], bsdf.inputs["Normal"])
for nm_ in ("_pos", "_nrm", "_part", "_noise", "_noise2", "_ao", "_normal", "_height"):
    if nm_ in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[nm_])
for img in (img_base, img_orm, img_nrm):
    img.pack()

# ======================================================================= 7. armature
arm_data = bpy.data.armatures.new("OrcaRig")
arm = bpy.data.objects.new("OrcaRig", arm_data)
scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones


def bone(name, h, t, parent=None, deform=True, connect=False, roll=0.0):
    b = eb.new(name); b.head = V(h); b.tail = V(t); b.roll = roll
    if parent:
        b.parent = eb[parent]; b.use_connect = connect
    b.use_deform = deform
    return b


JAW_PIVOT = V((0, Y0 + L * 0.112, lip_point(0.10).z - 0.02))
bone("root", (0, 0, 0), (0, 1.0, 0), deform=False)
bone("body", (0, -0.60, 0), (0, 0.20, 0), "root")
bone("chest", (0, -0.60, 0), (0, -1.60, -0.01), "body")
bone("head", (0, -1.60, -0.01), (0, -2.95, -0.09), "chest", connect=True)
bone("jaw", JAW_PIVOT, (0, Y0 + 0.03, lip_point(0.0).z - 0.05), "head")
TAIL_Y = [0.20, 0.80, 1.35, 1.85, 2.30, 2.66]
prev = "body"
for i in range(5):
    nm_ = f"tail_{i + 1:02d}"
    bone(nm_, (0, TAIL_Y[i], 0.01), (0, TAIL_Y[i + 1], 0.01), prev, connect=True)
    prev = nm_
bone("fluke", (0, 2.66, 0.01), (0, 3.08, 0.01), "tail_05", connect=True)
# fluke flex: one bone per fluke blade, from the peduncle out to the tip (local X rotation curls the tip)
for s_, sd in ((1, "L"), (-1, "R")):
    bone(f"fluke_tip.{sd}", (s_ * 0.22, 2.84, FLUKE_Z - 0.01), (s_ * FLUKE_SPAN * 0.98, 3.08, FLUKE_Z - 0.055), "fluke")
# blowhole: hinge at the crescent, pointing back over the rear lip (local X rotation opens / closes)
_bt, _ = surface(V((0, YB, 2.0)), V((0, 0, -1)))
bone("blowhole", (0, YB - 0.005, _bt.z - 0.03), (0, YB + 0.10, _bt.z - 0.03), "head")


def dorsal_mid(h):
    return V((0, 0.5 * (dorsal_le(h) + dorsal_te(h)), DORSAL_Z0 + DORSAL_H * h))


bone("dorsal_01", dorsal_mid(0.12), dorsal_mid(0.55), "body")
bone("dorsal_02", dorsal_mid(0.55), dorsal_mid(0.98), "dorsal_01", connect=True)
for s_, sd in ((1, "L"), (-1, "R")):
    sh, down, fwd, thick = pec_frames[s_]
    mid = sh + down * PEC_LEN * 0.5
    b = bone(f"pectoral_01.{sd}", sh, mid, "chest"); b.align_roll(thick)
    b = bone(f"pectoral_02.{sd}", mid, sh + down * PEC_LEN, f"pectoral_01.{sd}", connect=True); b.align_roll(thick)
for b in eb:
    if b.name.startswith(("root", "body", "chest", "head", "jaw", "tail", "fluke", "dorsal", "blowhole")):
        b.align_roll(V((0, 0, 1)))
bpy.ops.object.mode_set(mode='OBJECT')
arm_data.display_type = 'STICK'
B = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm_data.bones}

# ======================================================================= 8. weights
orca.parent = arm
orca.matrix_parent_inverse = Matrix()
mod = orca.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
for b in arm_data.bones:
    if b.use_deform:
        orca.vertex_groups.new(name=b.name)

nv = len(me.vertices)
parts = np.zeros(nv, np.float32); me.attributes["part"].data.foreach_get("value", parts)
jawf = np.zeros(nv, np.float32); me.attributes["jaw"].data.foreach_get("value", jawf)
co = [v.co.copy() for v in me.vertices]

# bone centres along the body, head -> flukes
CHAIN = [("head", -2.25), ("chest", -1.10), ("body", -0.20), ("tail_01", 0.50), ("tail_02", 1.08),
         ("tail_03", 1.60), ("tail_04", 2.08), ("tail_05", 2.48), ("fluke", 2.80)]


def chain_weights(y):
    if y <= CHAIN[0][1]:
        return {CHAIN[0][0]: 1.0}
    if y >= CHAIN[-1][1]:
        return {CHAIN[-1][0]: 1.0}
    for (a, ya), (b, yb) in zip(CHAIN, CHAIN[1:]):
        if ya <= y <= yb:
            t = sstep(ya, yb, y)
            return {a: 1 - t, b: t}


def along(p, name):
    h, t = B[name]
    d = t - h
    return (p - h).dot(d) / d.length_squared


groups = orca.vertex_groups
for i, p in enumerate(co):
    pid = parts[i]
    sd = "L" if p.x > 0 else "R"
    sv = (p.y - Y0) / L
    if pid == BODY:
        ws = chain_weights(p.y)
        wj = float(jawf[i]) * (1 - sstep(S_CORNER - 0.015, S_CORNER + 0.06, sv))
        if wj > 0:
            ws = {n: w * (1 - wj) for n, w in ws.items()}
            ws["jaw"] = wj
        # blowhole rear lip
        bv_ = p.y - YB + CRES * p.x * p.x
        wb = (math.exp(-((bv_ - 0.022) / 0.026) ** 2) * sstep(-0.006, 0.004, bv_)
              * (1 - sstep(0.09, 0.13, abs(p.x))) * (1.0 if p.z > 0.2 else 0.0))
        if wb > 1e-3:
            ws = {n: w * (1 - wb) for n, w in ws.items()}
            ws["blowhole"] = wb
    elif pid in (MOUTH, MOUTH + 0.5):
        wj = float(jawf[i])
        ws = {"head": 1 - wj, "jaw": wj}
    elif pid == TEETH:
        ws = {"head": 1.0}
    elif pid == TEETH + 0.5:
        ws = {"jaw": 1.0}
    elif pid == EYE:
        ws = {"head": 1.0}
    elif pid == DORSAL:
        h = (p.z - DORSAL_Z0) / DORSAL_H
        root = sstep(0.06, 0.22, h)
        top = sstep(0.30, 0.85, h)
        ws = chain_weights(p.y)
        ws = {n: w * (1 - root) for n, w in ws.items()}
        ws["dorsal_01"] = root * (1 - top)
        ws["dorsal_02"] = root * top
    elif pid == PECTORAL:
        u = along(p, f"pectoral_01.{sd}") * 0.5
        root = sstep(0.03, 0.12, u)
        lower = sstep(0.40, 0.60, u)
        ws = {"chest": 1 - root, f"pectoral_01.{sd}": root * (1 - lower), f"pectoral_02.{sd}": root * lower}
    else:  # flukes
        t = sstep(2.58, 2.76, p.y)
        tip = sstep(0.20, 0.55, abs(p.x))
        ws = {"tail_05": 1 - t, "fluke": t * (1 - tip), f"fluke_tip.{sd}": t * tip}
    for n, w in ws.items():
        if w > 1e-4:
            groups[n].add([i], w, 'REPLACE')

bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("[build] saved", OUT)
