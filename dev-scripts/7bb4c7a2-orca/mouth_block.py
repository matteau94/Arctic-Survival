# ======================================================================= 2. mouth interior + teeth
# The mouth lining is one folded sheet: palate (under the upper jaw, facing down) -> throat fold at
# S_BACK -> floor + tongue (over the lower jaw, facing up) back to the chin.  Its side and front edges
# tuck up / down inside the lips, so the open mouth shows a real cavity (palate, gum ridges, tongue,
# dark throat) instead of a slab.  The palate is weighted to 'head', the floor to 'jaw', blending to
# 'head' near the throat fold so it stretches instead of folding through the palate.
TOOTH_R = 0.915                      # tooth row, as a fraction of the lip half-width
S_BACK = 0.135                       # throat fold (just behind the gape)
NA, NU = 33, 22


def lip_w(s):
    return abs(lip_point(s).x)


def lining_point(s, a, upper):
    lp = lip_point(s)
    w, lz = abs(lp.x), lp.z
    fold = 1 - sstep(S_BACK - 0.04, S_BACK, s)
    front = sstep(0.004, 0.030, s)
    aa = abs(a)
    if upper:
        xf = 0.985 + (0.97 - 0.985) * (1 - fold)
        dz = 0.006 + 0.048 * (1 - aa * aa) * front                      # vaulted palate
        dz -= 0.011 * math.exp(-((aa - 0.925) / 0.045) ** 2)            # gum ridge under the tooth row
        dz += 0.034 * sstep(0.955, 1.0, aa)                             # edge tucks up into the upper jaw
    else:
        xf = 0.955 + (0.97 - 0.955) * (1 - fold)
        tongue = sstep(0.030, 0.065, s) * front
        dz = -0.012 - 0.014 * (1 - aa * aa) * front                     # floor of the mouth
        dz += 0.032 * math.exp(-(a / 0.52) ** 2) * tongue               # rounded tongue mound
        dz -= 0.005 * math.exp(-(a / 0.07) ** 2) * tongue               # median groove
        dz += 0.011 * math.exp(-((aa - 0.94) / 0.045) ** 2)             # gum ridge under the tooth row
        dz -= 0.024 * sstep(0.955, 1.0, aa)                             # edge tucks down into the lower jaw
    return V((a * xf * w, lp.y, lz + dz * fold))


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
    rb = min(0.0125, 0.066 * rad) * (0.72 + 0.28 * size)
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
        tooth(0.020 + 0.074 * i / (NT_UP - 1), side, True, math.sin(math.pi * (i + 0.6) / (NT_UP + 0.2)) ** 0.7)
    for i in range(NT_LO):                       # lower row sits in the gaps (interlocking)
        tooth(0.020 + 0.074 * (i + 0.5) / (NT_UP - 1), side, False, math.sin(math.pi * (i + 0.6) / (NT_LO + 0.2)) ** 0.7)

