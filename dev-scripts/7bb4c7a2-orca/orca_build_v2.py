"""Model, texture and rig an orca (killer whale) in the style of the other Artic-Survival animals.

    blender -b --python orca_build.py        (writes Orca_Rigged.blend + textures/Orca_*.png)

Real-world metres, ~6.2 m long (adult), body axis on z = 0, facing -Y (so +X is its left side).

1. Mesh 'Orca' (one object, one material, like the fox / bear / fish / penguin): subdivided lofts
     body      snout -> melon -> barrel -> laterally compressed tail stock as one ring loft; the
               ring vertex at the lip line is split from the snout back to the mouth corner so
               the lower jaw can open
     mouth     a soft interior 'plug' inside the head (seen through the open jaw) + conical teeth
     fins      tall back-leaning dorsal fin, rounded paddle pectorals, swept flukes with a notch
     eyes      small spheres
   Every part carries a 'part' point attribute used when texturing and weighting.
2. Textures (2048^2, PBR like the other assets): object-space position / normal / part /
   noise / AO are baked from the mesh, the orca pattern (black back, white lower jaw, throat,
   belly and flank lobes, white eye patch, grey saddle, white fluke undersides) is painted from
   them in numpy, and a tangent-space skin normal map is baked from a bump shader.
     textures/Orca_BaseColor.png, Orca_ORM.png (R=AO, G=roughness, B=metal), Orca_Normal.png
3. Rig 'OrcaRig':
     root (no deform)
       body > chest > head > jaw
       body > tail_01 > tail_02 > tail_03 > tail_04 > tail_05 > fluke
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
    (0.300, 0.610, 0.630, 0.620, 0.000),
    (0.380, 0.615, 0.655, 0.650, 0.000),
    (0.460, 0.590, 0.640, 0.630, 0.000),
    (0.540, 0.530, 0.585, 0.560, 0.010),
    (0.620, 0.440, 0.510, 0.470, 0.015),
    (0.700, 0.330, 0.420, 0.370, 0.020),
    (0.770, 0.225, 0.325, 0.280, 0.020),
    (0.830, 0.145, 0.240, 0.205, 0.020),
    (0.880, 0.095, 0.165, 0.145, 0.015),
    (0.920, 0.070, 0.105, 0.095, 0.010),
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


NR = 46
ss = [0.003 + (S_END - 0.003) * (i / (NR - 1)) ** 1.3 for i in range(NR)]
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
bvh_body = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())


def surface(origin, direction):
    hit, nrm, _, _ = bvh_body.ray_cast(V(origin), V(direction).normalized())
    return hit, nrm


# ======================================================================= 2. mouth interior + teeth
PLUG, TOOTH_R = 0.85, 0.925          # mouth plug / tooth row, as fractions of the lip radius
plug_rings = []
for s in [0.004 + (0.125 - 0.004) * i / 13 for i in range(14)]:
    c = V((0, Y0 + L * s, lip_point(s).z))
    plug_rings.append([c + PLUG * (ring_point(s, 2 * math.pi * j / 24) - c) for j in range(24)])
plug = mesh_from_rings("Mouth", plug_rings, MOUTH, cap_start=V((0, Y0 + 0.01, lip_point(0.0).z)),
                       cap_end=V((0, Y0 + L * 0.128, lip_point(0.125).z)))
subdivide(plug, 1)

teeth = []


def tooth(s, side, upper):
    lp = lip_point(s)
    lp.x *= side
    c = V((0, lp.y, lp.z))
    # teeth sit in the gap between the skin and the mouth plug, hidden when the jaw is closed
    rad = (lp - c).length
    base = c + TOOTH_R * (lp - c) + V((0, 0, 0.012 if upper else -0.012))
    rt = min(0.012, 0.36 * (1 - PLUG) * rad)
    ln = 0.030 + 0.018 * sstep(0.015, 0.05, s)
    tip = base + V((-side * 0.012, 0.004, -ln if upper else ln))
    d = (tip - base).normalized()
    a = d.orthogonal().normalized(); b = d.cross(a)
    rs = []
    for i in range(4):
        u = i / 3
        r = rt * (1 - u) + 0.0015
        cc = base + (tip - base) * u
        rs.append([cc + a * (r * math.cos(2 * math.pi * q / 6)) + b * (r * math.sin(2 * math.pi * q / 6)) for q in range(6)])
    ob = mesh_from_rings("Tooth", rs, TEETH + (0.0 if upper else 0.5), cap_start=base - d * 0.01, cap_end=tip + d * 0.004)
    teeth.append(ob)


for side in (1, -1):
    for i in range(11):
        tooth(0.022 + 0.068 * i / 10, side, True)
        tooth(0.025 + 0.068 * (i + 0.5) / 10.5, side, False)

# ======================================================================= 3. eyes
eyes = []
EYE_R = 0.028
EYE_S, EYE_PHI = 0.115, 1.40
for s in (1, -1):
    ys = Y0 + L * EYE_S
    zc = hermite(KEYS[3], EYE_S)
    d = V((s * math.sin(EYE_PHI), 0, math.cos(EYE_PHI)))
    hit, nrm = surface(V((0, ys, zc)) + d * 2.0, -d)
    ctr = hit - nrm * EYE_R * 0.40
    me = bpy.data.meshes.new("Eye"); bmx = bmesh.new()
    bmesh.ops.create_uvsphere(bmx, u_segments=16, v_segments=10, radius=EYE_R, matrix=Matrix.Translation(ctr))
    bmx.to_mesh(me); bmx.free()
    ob = bpy.data.objects.new("Eye", me); scene.collection.objects.link(ob)
    for nm_, val in (("part", float(EYE)), ("jaw", 0.0)):
        att = me.attributes.new(nm_, 'FLOAT', 'POINT')
        att.data.foreach_set("value", [val] * len(me.vertices))
    for p in me.polygons:
        p.use_smooth = True
    eyes.append(ob)


# ======================================================================= 4. dorsal fin
def dorsal_le(h):
    return -0.82 + 0.80 * h ** 1.15


def dorsal_te(h):
    return 0.14 - 0.10 * h - 0.06 * math.sin(math.pi * h)   # slightly concave trailing edge


DORSAL_Z0, DORSAL_H = 0.48, 1.22


def airfoil(p):
    """Thickness distribution along the chord (0 = leading edge), peak 1.0 at p = 1/3."""
    return 2.6 * math.sqrt(max(p, 0.0)) * (1 - p)


rs = []
for i in range(22):
    h = i / 21 * 0.985
    z = DORSAL_Z0 + DORSAL_H * h
    le, te = dorsal_le(h), dorsal_te(h)
    T = 0.10 * (1 - h) + 0.012
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
    for i in range(22):
        u = i / 21
        w = hermite(WK, u)
        t = 0.10 * (1 - u) + 0.022
        c = shoulder + down * (PEC_LEN * u)
        ring = []
        for j in range(16):
            ph = 2 * math.pi * j / 16
            a, b = math.cos(ph), math.sin(ph)
            lead = a > 0
            ww = w * (0.45 if lead else 0.55)
            tt = t * (1.0 if lead else 0.6 + 0.4 * (1 + a))
            ring.append(c + fwd * (ww * a) + thick * (tt * b * 0.5))
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
    return 2.50 + 0.55 * u ** 1.7


def fluke_te(u):
    return 2.90 + 0.28 * u ** 1.2          # central notch at u = 0


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
        ring.append(V((x, le + p * (te - le), FLUKE_Z + (math.copysign(0.5 * T * airfoil(p), sn) if abs(sn) > 1e-6 else 0.0))))
    rs.append(ring)
flukes = mesh_from_rings("Flukes", rs, FLUKE, cap_start=V((-FLUKE_SPAN * 1.04, 3.14, FLUKE_Z)),
                         cap_end=V((FLUKE_SPAN * 1.04, 3.14, FLUKE_Z)))
subdivide(flukes, 1)

# ======================================================================= join
objs = [body, plug, dorsal, flukes] + eyes + pectorals + teeth
for o in bpy.context.view_layer.objects:
    o.select_set(o in objs)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
orca = body
orca.name = "Orca"; orca.data.name = "Orca"
me = orca.data
print("[build] mesh verts", len(me.vertices), "faces", len(me.polygons))

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

s = (y - Y0) / L
zc = np.interp(s, [r[0] for r in PROFILE], [r[4] for r in PROFILE])
ang = np.arctan2(np.abs(x), z - zc)               # 0 on top, pi under the belly


def col(*c):
    return np.array(c, dtype=np.float32)


def mix(a, b, t):
    t = np.asarray(t)[..., None]
    return a * (1 - t) + b * t


BLACK = col(0.010, 0.011, 0.014)
WHITE = col(0.88, 0.88, 0.86)
DIATOM = col(0.90, 0.86, 0.74)
SADDLE = col(0.40, 0.41, 0.43)

jit = (n_med - 0.5) * 0.04
# white underside: lower jaw from the lip line, throat, a narrow band between the flippers,
# the belly, and the flank lobes sweeping up and back behind the dorsal fin
THR = [(0.00, PHI_M), (0.095, PHI_M), (0.13, 1.95), (0.18, 2.30), (0.24, 2.62), (0.30, 2.62),
       (0.38, 2.42), (0.47, 2.22), (0.54, 1.95), (0.59, 1.55), (0.635, 1.22), (0.665, 1.20),
       (0.695, 1.55), (0.725, 2.20), (0.76, 2.75), (0.79, 3.40), (1.0, 3.40)]
thr = hermite_np(THR, np.clip(s, 0, 1))
white = smoothstep(thr - 0.010, thr + 0.010, ang + jit * (s > 0.12))

# eye patch: a tilted oval above and behind the eye (side projection)
a = math.radians(13)
dy, dz = y - (Y0 + L * 0.183), z - 0.19
ey = dy * math.cos(a) + dz * math.sin(a)
ez = -dy * math.sin(a) + dz * math.cos(a)
ey = ey / np.where(ey > 0, 0.38, 0.24)
ez = ez / np.where(ey > 0, 0.100 - 0.02 * np.clip(ey, 0, 1), 0.100)
eyep = (1 - smoothstep(0.92, 1.05, ey * ey + ez * ez + jit)) * smoothstep(0.25, 0.5, np.abs(N[..., 0]))
white = np.maximum(white, eyep)

dark = BLACK * (0.8 + 0.45 * n_broad[..., None])
dark_fin = dark.copy()
# faint pale scars along the flanks
scar = (1 - smoothstep(0.0, 0.012, np.abs(n_streak - 0.5))) * smoothstep(0.55, 0.7, n_broad)
dark = mix(dark, col(0.10, 0.10, 0.11), 0.5 * scar)
# grey saddle patch behind the dorsal fin
# (front edge hugs the fin's trailing base, rear edge curves back and down, soft mottled rim)
ds = s - 0.522 + 0.020 * ang
saddle = ((1 - smoothstep(0.80, 0.90, ang + 2 * jit)) * smoothstep(0.0, 0.012, ds)
          * (1 - smoothstep(0.085, 0.115, ds + 1.5 * jit - 0.04 * ang)))
dark = mix(dark, SADDLE * (0.9 + 0.25 * n_med[..., None]), 0.9 * saddle)
light = mix(WHITE, DIATOM, 0.25 * smoothstep(0.45, 0.8, n_broad)) * (0.95 + 0.07 * n_med[..., None])
c_body = mix(dark, light, white)

# flukes: black above, white below with a black margin
u = np.clip(np.abs(x) / FLUKE_SPAN, 0, 1)
inside = np.minimum(y - (2.50 + 0.55 * u ** 1.7), (2.90 + 0.28 * u ** 1.2) - y)
under = smoothstep(0.15, -0.25, N[..., 2])
fw = smoothstep(0.1, -0.1, N[..., 2]) * smoothstep(0.035, 0.06, inside) * (1 - smoothstep(0.76, 0.84, u)) * smoothstep(2.66, 2.72, y)
c_fluke = mix(dark_fin, light, fw)

c_eye = col(0.030, 0.020, 0.016)
mouth_d = np.clip((y - Y0) / (L * 0.12), 0, 1)
c_mouth = mix(col(0.60, 0.30, 0.32), col(0.25, 0.10, 0.12), mouth_d) * (0.9 + 0.2 * n_med[..., None])
c_teeth = col(0.86, 0.83, 0.74)

base = c_body.copy()
for pid, cc in ((DORSAL, dark_fin), (PECTORAL, dark_fin), (FLUKE, c_fluke), (EYE, c_eye), (MOUTH, c_mouth),
                (TEETH, c_teeth), (TEETH + 0.5, c_teeth)):
    m = part == pid
    base[m] = (cc if cc.ndim == 1 else cc[m])
ao = np.clip(px_ao, 0, 1)
base = base * (0.6 + 0.4 * ao)[..., None]
base = np.clip(base, 0, 1)

rough = np.where(white > 0.5, 0.40, 0.30).astype(np.float32)
rough[part == EYE] = 0.05
rough[part == MOUTH] = 0.45
rough[(part == TEETH) | (part == TEETH + 0.5)] = 0.30
rough += (n_med - 0.5) * 0.08


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
orm = np.stack([0.4 + 0.6 * ao, np.clip(rough, 0, 1), np.zeros_like(ao)], -1)
img_orm = save("Orca_ORM", orm, 'Non-Color')

# ----------------------------------------------------------------------- skin normal map
for n in list(nodes):
    nodes.remove(n)
out = nodes.new("ShaderNodeOutputMaterial")
bsdf = nodes.new("ShaderNodeBsdfPrincipled")
links.new(bsdf.outputs[0], out.inputs[0])
tc = nodes.new("ShaderNodeTexCoord")
vm = nodes.new("ShaderNodeVectorMath"); vm.operation = 'MULTIPLY'; vm.inputs[1].default_value = (1, 0.3, 1)
links.new(tc.outputs["Object"], vm.inputs[0])
wr = nodes.new("ShaderNodeTexNoise"); wr.inputs["Scale"].default_value = 30; wr.inputs["Detail"].default_value = 3
links.new(vm.outputs[0], wr.inputs["Vector"])
nz = nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 90; nz.inputs["Detail"].default_value = 2
links.new(tc.outputs["Object"], nz.inputs["Vector"])
add = nodes.new("ShaderNodeMath"); add.operation = 'MULTIPLY_ADD'; add.inputs[1].default_value = 3.0
links.new(wr.outputs["Fac"], add.inputs[0]); links.new(nz.outputs["Fac"], add.inputs[2])
att = nodes.new("ShaderNodeAttribute"); att.attribute_name = "part"
skin = nodes.new("ShaderNodeMapRange")          # skin parts 0..3 get the bump, eyes / mouth / teeth barely
skin.inputs["From Min"].default_value = 3.5; skin.inputs["From Max"].default_value = 3.6
skin.inputs["To Min"].default_value = 0.12; skin.inputs["To Max"].default_value = 0.02
links.new(att.outputs["Fac"], skin.inputs["Value"])
bump = nodes.new("ShaderNodeBump"); bump.inputs["Distance"].default_value = 0.0008
links.new(skin.outputs[0], bump.inputs["Strength"])
links.new(add.outputs[0], bump.inputs["Height"])
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
for nm_ in ("_pos", "_nrm", "_part", "_noise", "_ao", "_normal"):
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
    if b.name.startswith(("root", "body", "chest", "head", "jaw", "tail", "fluke", "dorsal")):
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
    elif pid == MOUTH:
        lz = lip_point(max(0.0, min(0.125, sv))).z
        wj = (1 - sstep(lz - 0.05, lz + 0.03, p.z)) * (1 - sstep(S_CORNER - 0.01, S_CORNER + 0.03, sv))
        ws = {"head": 1 - wj, "jaw": wj}
    elif pid == TEETH:
        ws = {"head": 1.0}
    elif pid == TEETH + 0.5:
        ws = {"jaw": 1.0}
    elif pid == EYE:
        ws = {"head": 1.0}
    elif pid == DORSAL:
        h = (p.z - DORSAL_Z0) / DORSAL_H
        root = sstep(0.08, 0.20, h)
        top = sstep(0.45, 0.65, h)
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
        ws = {"tail_05": 1 - t, "fluke": t}
    for n, w in ws.items():
        if w > 1e-4:
            groups[n].add([i], w, 'REPLACE')

bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("[build] saved", OUT)
