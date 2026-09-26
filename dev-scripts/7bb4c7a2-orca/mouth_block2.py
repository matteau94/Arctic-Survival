# ======================================================================= 2. mouth interior + teeth
# The mouth lining is one folded sheet: inner upper lip -> upper gum -> vaulted palate -> throat fold at
# S_BACK -> floor + tongue -> lower gum -> inner lower lip.  Its lip edges sit just inside the skin
# (every vertex is ray-clamped inside the sculpted body), so the open mouth shows a real cavity.
# The palate is weighted to 'head', the floor to 'jaw', blending to 'head' near the throat fold.
# Teeth grow from the gums toward the lip line but never cross it: with the jaw closed or only
# slightly open (a few degrees) they stay inside their own jaw and cannot show between the lips.
TOOTH_RU, TOOTH_RL = 0.900, 0.845    # upper / lower tooth rows, fractions of the lip half-width
GUM_U, GUM_L = 0.028, -0.028         # gum crest height above / below the lip line (m)
S_BACK = 0.135                       # throat fold (just behind the gape)
NA, NU = 29, 22


def lip_w(s):
    return abs(lip_point(s).x)


def inside_skin(v, margin=0.003):
    """Pull a point horizontally toward the body axis until it is `margin` inside the skin."""
    sx = 1.0 if v.x >= 0 else -1.0
    hit = bvh_body.ray_cast(V((0.0, v.y, v.z)), V((sx, 0.0, 0.0)))[0]
    if hit is None:
        return v
    lim = abs(hit.x) - margin
    if abs(v.x) > lim:
        return V((sx * max(lim, 0.0), v.y, v.z))
    return v


def lining_point(s, a, upper):
    lp = lip_point(s)
    w, lz = abs(lp.x), lp.z
    fold = 1 - sstep(S_BACK - 0.04, S_BACK, s)
    front = sstep(0.004, 0.030, s)
    sa = 1.0 if a >= 0 else -1.0
    t_ = abs(a)
    TI = 0.78                                                            # interior .. gum crest
    gx = (TOOTH_RU if upper else TOOTH_RL) * fold + 0.87 * (1 - fold)
    if t_ <= TI:
        aa = t_ / TI                                                     # 0 midline .. 1 gum crest
        if upper:
            dz = GUM_U + 0.042 * (1 - aa * aa) * front                   # vaulted palate
        else:
            tongue = sstep(0.030, 0.065, s) * front
            dz = GUM_L - 0.012 * (1 - aa * aa) * front                   # floor of the mouth
            dz += 0.036 * math.exp(-(aa / 0.55) ** 2) * tongue           # rounded tongue mound
            dz -= 0.005 * math.exp(-(aa / 0.075) ** 2) * tongue          # median groove
        p_ = V((sa * aa * gx * w, lp.y, lz + dz * fold))
    else:
        # gum crest -> gum outer slope -> inner lip, ending just inside the lip edge
        u = (t_ - TI) / (1 - TI)
        gz = (GUM_U - 0.004) if upper else (GUM_L + 0.004)
        x0, z0 = gx * w, gz
        x1, z1 = 0.968 * w, (0.004 if upper else -0.004)
        k = u * u * (3 - 2 * u)
        p_ = V((sa * (x0 + (x1 - x0) * u), lp.y, lz + (z0 + (z1 - z0) * k) * fold))
    return inside_skin(p_, 0.003)


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
f0 = bml.faces[(NU // 2) * (NA - 1) + NA // 2]                            # palate faces face down
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
    """Conical tooth: round section, blunt tip, curving back and slightly inward, rooted in the
    gum; the tip stops just short of the lip line.  size 0..1 (smaller at the front / back)."""
    lp = lip_point(s)
    w, lz = abs(lp.x), lp.z
    rr = TOOTH_RU if upper else TOOTH_RL
    sg = 1.0 if upper else -1.0
    base = V((side * rr * w, lp.y, lz + sg * 0.046))
    tipz = lz + sg * (0.002 + 0.010 * (1 - size))                     # smaller teeth stop shorter
    ln = abs(base.z - tipz)
    rb = min(0.0125, 0.060 * w) * (0.72 + 0.28 * size)
    dv = V((0, 0, -sg))
    back, inward = V((0, 1, 0)), V((-side, 0, 0))

    def ctr(u):
        return base + dv * (ln * u) + back * (0.16 * ln * u * u) + inward * (0.08 * ln * u * u)
    US = [0.0, 0.25, 0.45, 0.62, 0.76, 0.87, 0.95]
    rs = []
    for u in US:
        tng = (ctr(min(u + 0.02, 1.0)) - ctr(max(u - 0.02, 0.0))).normalized()
        a_ = tng.orthogonal().normalized(); b_ = tng.cross(a_)
        # root and lower crown stay full, the upper crown tapers to a blunt tip
        r = rb * (1 - max(0.0, (u - 0.35) / 0.65) ** 1.4) ** 0.7
        cc = ctr(u)
        rs.append([inside_skin(cc + a_ * (r * math.cos(2 * math.pi * q / 10)) + b_ * (r * math.sin(2 * math.pi * q / 10)), 0.002)
                   for q in range(10)])
    ob = mesh_from_rings("Tooth", rs, TEETH + (0.0 if upper else 0.5), cap_start=inside_skin(base - dv * 0.006, 0.002),
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

