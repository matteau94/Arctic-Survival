SP = r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\7bb4c7a2-2c8e-4793-b5ee-2fc544b80253\scratchpad"
p = r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_build.py"
t = open(p, encoding="utf8").read()


def rep(a, b, cnt=1):
    global t
    assert t.count(a) == cnt, ("NOT FOUND/UNIQUE", t.count(a), a[:90])
    t = t.replace(a, b)


# ---------------------------------------------------------------- mouth lining + teeth
i = t.index("# ======================================================================= 2. mouth interior + teeth")
j = t.index("# ======================================================================= 3. eyes")
t = t[:i] + open(SP + r"\mouth_block.py", encoding="utf8").read() + t[j:]

# ---------------------------------------------------------------- junctions, micro mask, fin-root normals
rep("""# ======================================================================= join
objs = [body, plug, dorsal, flukes] + eyes + pectorals + teeth""",
"""# ======================================================================= join
# fin-root junction points: fin vertices lying on the body surface (used to hide the seams)
JUNC = []
for fo, rad_ in ((dorsal, 0.012), (flukes, 0.010), (pectorals[0], 0.012), (pectorals[1], 0.012)):
    for v in fo.data.vertices:
        hit_ = bvh_body.find_nearest(v.co)
        if hit_[0] is not None and hit_[3] < rad_:
            JUNC.append(tuple(v.co))
JUNC = np.array(JUNC)
print("[build] fin-root junction points", len(JUNC))

objs = [body, plug, dorsal, flukes] + eyes + pectorals + teeth""")
rep("""print("[build] mesh verts", len(me.vertices), "faces", len(me.polygons), "body rings", NR)""",
"""print("[build] mesh verts", len(me.vertices), "faces", len(me.polygons), "body rings", NR)

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
    print("[build] custom normals failed:", ex)""")

# ---------------------------------------------------------------- micro bump driven by the mask
rep("""att = nodes.new("ShaderNodeAttribute"); att.attribute_name = "part"
skin = nodes.new("ShaderNodeMapRange")          # skin parts 0..3 get the micro bump, eyes / mouth / teeth barely
skin.inputs["From Min"].default_value = 3.5; skin.inputs["From Max"].default_value = 3.6
skin.inputs["To Min"].default_value = 0.24; skin.inputs["To Max"].default_value = 0.02
links.new(att.outputs["Fac"], skin.inputs["Value"])
mm = nodes.new("ShaderNodeMath"); mm.operation = 'MULTIPLY'
links.new(micro.outputs[0], mm.inputs[0]); links.new(skin.outputs[0], mm.inputs[1])""",
"""att = nodes.new("ShaderNodeAttribute"); att.attribute_name = "micro"      # ~0 on head / eyes / mouth
skin = nodes.new("ShaderNodeMath"); skin.operation = 'MULTIPLY'; skin.inputs[1].default_value = 0.16
links.new(att.outputs["Fac"], skin.inputs[0])
mm = nodes.new("ShaderNodeMath"); mm.operation = 'MULTIPLY'
links.new(micro.outputs[0], mm.inputs[0]); links.new(skin.outputs[0], mm.inputs[1])""")
rep("""vo = nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 260""",
    """vo = nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 340""")

# ---------------------------------------------------------------- weights for the lining
rep("""    elif pid == MOUTH:
        lz = lip_point(max(0.0, min(0.125, sv))).z
        wj = (1 - sstep(lz - 0.05, lz + 0.03, p.z)) * (1 - sstep(S_CORNER - 0.01, S_CORNER + 0.03, sv))
        ws = {"head": 1 - wj, "jaw": wj}""",
"""    elif pid in (MOUTH, MOUTH + 0.5):
        wj = float(jawf[i])
        ws = {"head": 1 - wj, "jaw": wj}""")

# ---------------------------------------------------------------- eye patch: long, low, tilted, pointed front
rep("""a = math.radians(12)
EPC = (Y0 + L * 0.184, 0.180)""", """a = math.radians(15)
EPC = (Y0 + L * 0.178, 0.170)""")
rep("""tq = ey / 0.34
half_h = 0.100 * np.sqrt(np.clip(1 - tq * tq, 0, 1)) * (0.78 + 0.22 * np.clip((tq + 1) / 2, 0, 1)) * 1.12""",
"""tq = ey / 0.315                                    # ~0.63 m long, ~0.17 m tall (3.7 : 1)
half_h = (0.085 / 0.84) * np.sqrt(np.clip(1 - tq * tq, 0, 1)) * np.clip((tq + 1) / 2, 0, 1) ** 0.30""")

# ---------------------------------------------------------------- pattern: throat narrows between flippers, graceful flank lobe
rep("""THR = [(0.00, PHI_M + 0.05), (0.095, PHI_M + 0.05), (0.13, 1.95), (0.18, 2.30), (0.24, 2.62), (0.30, 2.62),
       (0.38, 2.42), (0.47, 2.22), (0.54, 1.95), (0.59, 1.55), (0.635, 1.22), (0.665, 1.20),
       (0.695, 1.55), (0.725, 2.20), (0.76, 2.75), (0.79, 3.40), (1.0, 3.40)]""",
"""THR = [(0.00, PHI_M + 0.05), (0.095, PHI_M + 0.05), (0.125, 1.90), (0.16, 2.15), (0.205, 2.55), (0.25, 2.76),
       (0.30, 2.74), (0.36, 2.52), (0.44, 2.30), (0.51, 2.12), (0.555, 1.90), (0.585, 1.58), (0.608, 1.30),
       (0.630, 1.14), (0.652, 1.10), (0.675, 1.20), (0.70, 1.46), (0.73, 1.90), (0.76, 2.42), (0.785, 2.90),
       (0.805, 3.40), (1.0, 3.40)]""")

# ---------------------------------------------------------------- colour: neutral charcoal, matte patches
rep("""BLACK = col(0.080, 0.087, 0.102)""", """BLACK = col(0.084, 0.087, 0.094)""")
rep("""spine = 0.62 + 0.38 * smoothstep(0.1, 1.4, ang)""", """spine = 0.55 + 0.45 * smoothstep(0.05, 1.45, ang)""")
rep("""rough = rough + 0.04 * white + 0.10 * scar_m + 0.45 * bslit""",
    """rough = rough + 0.04 * white + 0.10 * scar_m + 0.45 * bslit
rough = rough + 0.14 * smoothstep(0.55, 0.80, n_broad) * smoothstep(0.4, 0.7, n_fine) * (is_body | (part == DORSAL))  # drier matte patches""")

# ---------------------------------------------------------------- mouth / teeth colours, no baked AO inside the mouth
rep("""mouth_d = np.clip((y - Y0) / (L * 0.12), 0, 1)
c_mouth = mix(col(0.70, 0.38, 0.40), col(0.26, 0.09, 0.11), mouth_d ** 0.8) * (0.85 + 0.25 * n_med[..., None])
c_mouth = mix(c_mouth, col(0.45, 0.20, 0.24), 0.3 * (0.5 + 0.5 * np.sin(y * 90)) * smoothstep(0.02, 0.0, np.abs(x) - 0.12))
c_teeth = mix(col(0.90, 0.87, 0.78), col(0.72, 0.66, 0.52), smoothstep(0.3, 0.8, n_fine))""",
"""# ---- mouth: palate with transverse ridges, lighter gums, pink tongue, near-black throat
s_c = np.clip(s, 0, 0.2)
w_s = np.interp(s_c, LIP_S, LIP_W); lz_s = np.interp(s_c, LIP_S, LIP_Z)
a_m = np.abs(x) / np.maximum(w_s, 1e-3)
is_pal = np.abs(part - MOUTH) < 0.01
is_flr = np.abs(part - (MOUTH + 0.5)) < 0.01
depth = smoothstep(0.045, S_BACK, s)
pal_r = (0.5 + 0.5 * np.sin(2 * np.pi * (y - Y0) / 0.024)) * (1 - smoothstep(0.55, 0.8, a_m)) * (1 - depth)
gum = g(a_m, 0.93, 0.05)
tongue_m = (1 - smoothstep(0.45, 0.75, a_m))
c_mouth = mix(col(0.60, 0.33, 0.36), col(0.72, 0.42, 0.45), 0.35 * pal_r)              # palate
c_mouth = np.where(is_flr[..., None], mix(col(0.56, 0.24, 0.28), col(0.66, 0.30, 0.33), tongue_m * n_med)[...] , c_mouth)
c_mouth = mix(c_mouth, col(0.80, 0.56, 0.56), 0.75 * gum)                            # gums, lighter pink
c_mouth = mix(c_mouth, col(0.16, 0.12, 0.13), smoothstep(0.965, 1.0, a_m))           # pigmented inner lip
c_mouth = mix(c_mouth, col(0.035, 0.012, 0.016), depth ** 1.3)                        # dark throat
c_mouth = c_mouth * (0.9 + 0.15 * n_fine[..., None])
# ---- teeth: ivory, yellower at the gum line, worn paler tips, per-tooth variation
tt_up = np.clip(((lz_s + 0.014) - z) / 0.055, 0, 1)
tt_lo = np.clip((z - (lz_s - 0.014)) / 0.055, 0, 1)
tt = np.where(part > TEETH + 0.25, tt_lo, tt_up)
c_teeth = mix(col(0.70, 0.60, 0.42), col(0.90, 0.86, 0.74), smoothstep(0.15, 0.55, tt))
c_teeth = mix(c_teeth, col(0.84, 0.83, 0.78), smoothstep(0.75, 1.0, tt))
c_teeth = c_teeth * (0.90 + 0.14 * n_med[..., None]) * (0.95 + 0.08 * n_fine[..., None])""")
rep("""base = c_body.copy()
for pid, cc in ((DORSAL, dark_fin), (PECTORAL, dark_fin), (FLUKE, c_fluke), (EYE, c_eye), (MOUTH, c_mouth),
                (TEETH, c_teeth), (TEETH + 0.5, c_teeth)):
    m = part == pid
    base[m] = (cc if cc.ndim == 1 else cc[m])
ao = np.clip(px_ao, 0, 1)
base = base * (0.55 + 0.45 * ao)[..., None]""",
"""# ---- fin-root junctions: body colour and a lifted AO blend across the seam
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
base = base * (0.55 + 0.45 * ao)[..., None]""")
rep("""rough = np.where(part == MOUTH, 0.30, rough)""",
    """rough = np.where(is_pal | is_flr, 0.24 + 0.06 * gum + 0.04 * n_fine, rough)""")
# ---- mouth height: palate ridges, tongue papillae
rep("""H[(part == EYE) | (part == TEETH) | (part == TEETH + 0.5)] = 0.0""",
    """H += (is_pal * 0.9 * (pal_r - 0.5) + is_flr * 0.6 * tongue_m * (smoothstep(0.12, 0.0, n_vor) - 0.3)) * (1 - depth)
H[(part == EYE) | (part == TEETH) | (part == TEETH + 0.5)] = 0.0""")
open(p, "w", encoding="utf8").write(t)
print("edited ed10")
