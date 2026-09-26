p = r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_build.py"
t = open(p, encoding="utf8").read()


def rep(a, b):
    global t
    assert t.count(a) == 1, ("NOT FOUND/UNIQUE", a[:80])
    t = t.replace(a, b)


def rep_between(start, end, new):
    """replace text from start marker (inclusive) up to end marker (exclusive)"""
    global t
    i = t.index(start); j = t.index(end, i)
    t = t[:i] + new + t[j:]


# ---------------------------------------------------------------- A. profile: stouter barrel, deeper keeled tail stock
rep("""    (0.300, 0.610, 0.630, 0.620, 0.000),
    (0.380, 0.615, 0.655, 0.650, 0.000),
    (0.460, 0.590, 0.640, 0.630, 0.000),
    (0.540, 0.530, 0.585, 0.560, 0.010),
    (0.620, 0.440, 0.510, 0.470, 0.015),
    (0.700, 0.330, 0.420, 0.370, 0.020),
    (0.770, 0.225, 0.325, 0.280, 0.020),
    (0.830, 0.145, 0.240, 0.205, 0.020),
    (0.880, 0.095, 0.165, 0.145, 0.015),
    (0.920, 0.070, 0.105, 0.095, 0.010),""",
"""    (0.300, 0.625, 0.645, 0.640, 0.000),
    (0.380, 0.635, 0.675, 0.675, 0.000),
    (0.460, 0.605, 0.660, 0.650, 0.000),
    (0.540, 0.540, 0.600, 0.575, 0.010),
    (0.620, 0.445, 0.525, 0.485, 0.015),
    (0.700, 0.330, 0.435, 0.385, 0.020),
    (0.770, 0.220, 0.345, 0.300, 0.020),
    (0.830, 0.140, 0.265, 0.230, 0.020),
    (0.880, 0.092, 0.190, 0.165, 0.015),
    (0.920, 0.068, 0.120, 0.105, 0.010),""")

# ---------------------------------------------------------------- B. ring distribution: dense at snout / eye / blowhole / keel
rep("""NR = 46
ss = [0.003 + (S_END - 0.003) * (i / (NR - 1)) ** 1.3 for i in range(NR)]""",
"""# ring spacing (fraction of L) as a function of s: fine at the snout, the eye and around the
# blowhole (so the crescent can be sculpted), coarse along the barrel, medium on the keeled tail
DENS = [(0.0, 0.006), (0.03, 0.009), (0.13, 0.010), (0.150, 0.0040), (0.192, 0.0040), (0.215, 0.012),
        (0.28, 0.030), (0.66, 0.030), (0.72, 0.020), (0.945, 0.016)]
ss = [0.003]
while ss[-1] < S_END - 0.012:
    ss.append(ss[-1] + float(np.interp(ss[-1], [d[0] for d in DENS], [d[1] for d in DENS])))
ss[-1] = S_END
NR = len(ss)
S_TAB = np.linspace(0.0, S_END, 1200)
P_TAB = np.array([prof(v) for v in S_TAB])


def prof_np(sv):
    sv = np.clip(sv, 0.0, S_END)
    return [np.interp(sv, S_TAB, P_TAB[:, k]) for k in range(4)]""")

# ---------------------------------------------------------------- C. sculpt pass on the body
rep("""bm.to_mesh(body.data); bm.free()
subdivide(body, 2)
bvh_body = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())""",
"""bm.to_mesh(body.data); bm.free()
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
    d -= 0.009 * g(sv, 0.016, 0.008) * g(ang, 0.0, 1.1) * (sv > 0.004)
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
bvh_body = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())""")

rep("PLUG, TOOTH_R = 0.85, 0.925", "PLUG, TOOTH_R = 0.85, 0.915")

# ---------------------------------------------------------------- E. eyes with lids
rep("""eyes = []
EYE_R = 0.028
EYE_S, EYE_PHI = 0.115, 1.40
for s in (1, -1):""", """eyes = []
EYE_FRAMES = {}
for s in (1, -1):""")
rep("""    ctr = hit - nrm * EYE_R * 0.40
    me = bpy.data.meshes.new("Eye"); bmx = bmesh.new()""", """    ctr = hit - nrm * EYE_R * 0.45
    EYE_FRAMES[s] = (ctr.copy(), nrm.copy(), hit.copy())
    me = bpy.data.meshes.new("Eye"); bmx = bmesh.new()""")
rep("""    bmesh.ops.create_uvsphere(bmx, u_segments=16, v_segments=10, radius=EYE_R, matrix=Matrix.Translation(ctr))""",
    """    bmesh.ops.create_uvsphere(bmx, u_segments=24, v_segments=16, radius=EYE_R, matrix=Matrix.Translation(ctr))""")
rep("""    eyes.append(ob)
""", """    eyes.append(ob)
    # almond-shaped lid rim (a flattened torus) sitting on the skin around the eyeball
    t1 = V((0, 1, 0)); t1 = (t1 - t1.dot(nrm) * nrm).normalized()
    t2 = nrm.cross(t1).normalized()
    a_, b_, rl = EYE_R * 1.30, EYE_R * 0.92, 0.011
    lr = []
    for i in range(32):
        th = 2 * math.pi * i / 32
        c = hit + t1 * (a_ * math.cos(th)) + t2 * (b_ * math.sin(th) * (1 + 0.12 * math.cos(th)))
        radial = (t1 * (b_ * math.cos(th)) + t2 * (a_ * math.sin(th))).normalized()
        thick = 1.0 + 0.35 * max(0.0, math.sin(th) * (1 if s > 0 else 1))   # heavier upper lid
        lr.append([c + radial * (rl * math.cos(2 * math.pi * q / 10)) + nrm * (rl * 0.70 * thick * math.sin(2 * math.pi * q / 10) - 0.004)
                   for q in range(10)])
    lr.append([v_.copy() for v_ in lr[0]])
    lid = mesh_from_rings("Lid", lr, BODY)
    bml = bmesh.new(); bml.from_mesh(lid.data)
    bmesh.ops.remove_doubles(bml, verts=bml.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bml, faces=bml.faces)
    bml.to_mesh(lid.data); bml.free()
    subdivide(lid, 1)
    eyes.append(lid)
""")

# ---------------------------------------------------------------- F. dorsal fin: thin, slightly wavy trailing edge
rep("""def dorsal_te(h):
    return 0.14 - 0.10 * h - 0.06 * math.sin(math.pi * h)   # slightly concave trailing edge""",
"""def dorsal_te(h):
    # slightly concave, gently wavy trailing edge
    return 0.14 - 0.10 * h - 0.06 * math.sin(math.pi * h) + 0.010 * math.sin(7.0 * math.pi * h) * math.sin(math.pi * h)""")
rep("""    T = 0.10 * (1 - h) + 0.012
    ring = []
    for j in range(20):""", """    T = 0.11 * (1 - h) + 0.014
    ring = []
    for j in range(20):""")
rep("""def airfoil(p):
    \"\"\"Thickness distribution along the chord (0 = leading edge), peak 1.0 at p = 1/3.\"\"\"
    return 2.6 * math.sqrt(max(p, 0.0)) * (1 - p)""",
"""def airfoil(p):
    \"\"\"Thickness distribution along the chord (0 = leading edge), peak 1.0 at p ~ 0.3,
    thinning to a knife-like trailing edge.\"\"\"
    return 2.6 * math.sqrt(max(p, 0.0)) * (1 - p) ** 1.25""")

# ---------------------------------------------------------------- G. pectorals: broad paddles with digit ridges
rep("""            ww = w * (0.45 if lead else 0.55)
            tt = t * (1.0 if lead else 0.6 + 0.4 * (1 + a))
            ring.append(c + fwd * (ww * a) + thick * (tt * b * 0.5))""",
"""            ww = w * (0.45 if lead else 0.55)
            tt = t * (1.0 if lead else 0.6 + 0.4 * (1 + a))
            # four faint digit ridges running down the paddle
            ridge = 1 + 0.16 * max(0.0, math.cos(4 * math.pi * a)) * sstep(0.08, 0.2, u) * (1 - sstep(0.7, 0.9, u))
            ring.append(c + fwd * (ww * a) + thick * (tt * ridge * b * 0.5))""")
rep("""        for j in range(16):
            ph = 2 * math.pi * j / 16""", """        for j in range(24):
            ph = 2 * math.pi * j / 24""")

# ---------------------------------------------------------------- H. flukes: tips droop slightly
rep("""        ring.append(V((x, le + p * (te - le), FLUKE_Z + (math.copysign(0.5 * T * airfoil(p), sn) if abs(sn) > 1e-6 else 0.0))))""",
    """        droop = -0.06 * u ** 2.2
        ring.append(V((x, le + p * (te - le), FLUKE_Z + droop + (math.copysign(0.5 * T * airfoil(p), sn) if abs(sn) > 1e-6 else 0.0))))""")
rep("""flukes = mesh_from_rings("Flukes", rs, FLUKE, cap_start=V((-FLUKE_SPAN * 1.04, 3.14, FLUKE_Z)),
                         cap_end=V((FLUKE_SPAN * 1.04, 3.14, FLUKE_Z)))""",
    """flukes = mesh_from_rings("Flukes", rs, FLUKE, cap_start=V((-FLUKE_SPAN * 1.03, 3.15, FLUKE_Z - 0.062)),
                         cap_end=V((FLUKE_SPAN * 1.03, 3.15, FLUKE_Z - 0.062)))""")

open(p, "w", encoding="utf8").write(t)
print("edited ed2")
