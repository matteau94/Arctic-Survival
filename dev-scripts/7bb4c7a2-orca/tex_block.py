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


BLACK = col(0.020, 0.022, 0.028)     # charcoal with a cool blue-grey cast
WHITE = col(0.86, 0.87, 0.86)
DIATOM = col(0.90, 0.84, 0.66)
SADDLE = col(0.34, 0.35, 0.38)
SCAR = col(0.30, 0.31, 0.33)

jit = (n_med - 0.5) * 0.05 + (n_fine - 0.5) * 0.015
# ---- white underside: lower jaw from the lip line, throat narrowing between the flippers,
#      belly, and the flank lobes sweeping up and back behind the dorsal fin
THR = [(0.00, PHI_M), (0.095, PHI_M), (0.13, 1.95), (0.18, 2.30), (0.24, 2.62), (0.30, 2.62),
       (0.38, 2.42), (0.47, 2.22), (0.54, 1.95), (0.59, 1.55), (0.635, 1.22), (0.665, 1.20),
       (0.695, 1.55), (0.725, 2.20), (0.76, 2.75), (0.79, 3.40), (1.0, 3.40)]
thr = hermite_np(THR, np.clip(s, 0, 1))
edge_w = 0.008 + 0.004 * (s > 0.12)
white = smoothstep(thr - edge_w, thr + edge_w, ang + jit * (s > 0.12))

# ---- eye patch: an elongated teardrop above and behind the eye, tapering forward
a = math.radians(12)
EPC = (Y0 + L * 0.181, 0.175)
dy, dz = y - EPC[0], z - EPC[1]
ey = dy * math.cos(a) + dz * math.sin(a)
ez = -dy * math.sin(a) + dz * math.cos(a)
tq = ey / 0.34
half_h = 0.112 * np.sqrt(np.clip(1 - tq * tq, 0, 1)) * np.clip((tq + 1) / 2, 0, 1) ** 0.6 * 1.32
eyep = smoothstep(0.005, -0.005, np.abs(ez) - half_h + jit * 0.15) * (np.abs(tq) < 1)
eyep = eyep * smoothstep(0.2, 0.45, np.abs(N[..., 0])) * (x * np.sign(x) > 0.05)
white = np.maximum(white, eyep)

# ---- dark skin: darker along the spine, lighter mottling low on the flanks
spine = 0.72 + 0.28 * smoothstep(0.1, 1.3, ang)
mott = smoothstep(0.52, 0.75, n_broad) * smoothstep(0.7, 1.6, ang) * (0.6 + 0.4 * n_fine)
dark = BLACK * (spine * (0.85 + 0.35 * n_med))[..., None]
dark = dark + col(0.030, 0.034, 0.042) * mott[..., None]
dark_fin = BLACK * (0.9 + 0.3 * n_med + 0.15 * n_fine)[..., None]

# ---- grey saddle: hugs the fin's trailing base, feathered edges, striations sweeping back-down
ds = s - 0.520 + 0.018 * ang
feather = smoothstep(-0.004, 0.022, ds + 0.5 * jit) * (1 - smoothstep(0.055, 0.125, ds + 1.2 * jit - 0.035 * ang))
vert = 1 - smoothstep(0.55, 1.05, ang + 1.5 * jit)
stri_c = (y - 0.55 * np.abs(x) * 0 - 0.9 * (0.66 - z)) * 55 + 9 * n_warp
stri = 0.5 + 0.5 * np.sin(stri_c)
saddle = feather * vert
dark = mix(dark, SADDLE * (0.78 + 0.22 * stri + 0.15 * (n_med - 0.5))[..., None], 0.88 * saddle * (0.7 + 0.3 * stri))

# ---- rake-mark scars: sparse parallel pairs / triplets of pale thin lines on the flanks
rng = np.random.default_rng(11)
scar_m = np.zeros_like(x)
arc = ang * rad_t
bodyside = is_body & (s > 0.12) & (s < 0.86)
for k in range(30):
    sd = 1 if k % 2 else -1
    yc = Y0 + L * rng.uniform(0.16, 0.82)
    ac = rng.uniform(0.35, 1.9) * float(np.interp((yc - Y0) / L, S_TAB, P_TAB[:, 0])) * 1.1
    th = math.radians(rng.uniform(-60, 60) + (0 if rng.random() < 0.7 else 90))
    ln = rng.uniform(0.12, 0.45)
    nl = int(rng.integers(2, 4))
    sp = rng.uniform(0.022, 0.04)
    wd = rng.uniform(0.0022, 0.0040)
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
    scar_m[box] = np.maximum(scar_m[box], m * rng.uniform(0.5, 1.0))
# plus a few faint long streaks
scar_m = np.maximum(scar_m, 0.35 * (1 - smoothstep(0.0, 0.010, np.abs(n_streak - 0.5))) * smoothstep(0.6, 0.72, n_broad) * bodyside)

light = mix(WHITE, DIATOM, 0.35 * smoothstep(0.42, 0.78, n_broad) + 0.15 * smoothstep(0.6, 0.9, n_vor))
light = light * (0.94 + 0.08 * n_med + 0.03 * n_fine)[..., None]
c_body = mix(dark, light, white)
c_body = mix(c_body, SCAR, 0.55 * scar_m * (1 - white))
c_body = mix(c_body, col(0.55, 0.55, 0.55), 0.35 * scar_m * white)
# genital / umbilical slits: thin dark marks on the white belly
slit = g(x, 0.0, 0.006) * smoothstep(0.600, 0.604, s) * (1 - smoothstep(0.652, 0.656, s)) * (ang > 2.8)
umb = g(np.hypot(x, y - (Y0 + L * 0.50)), 0.0, 0.010) * (ang > 2.8)
c_body = mix(c_body, col(0.12, 0.11, 0.11), 0.85 * np.maximum(slit, umb))
# blowhole slit: dark inside the crescent
bv = blow_v(x, y)
bslit = g(bv, 0.0, 0.0065) * (1 - smoothstep(0.07, 0.105, np.abs(x))) * (ang < 0.6)
c_body = mix(c_body, col(0.004, 0.004, 0.006), 0.8 * bslit)

# ---- flukes: black above, white below with a black margin, black leading edge
u = np.clip(np.abs(x) / FLUKE_SPAN, 0, 1)
inside = np.minimum(y - (2.50 + 0.55 * u ** 1.7), (2.90 + 0.28 * u ** 1.2) - y)
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

mouth_d = np.clip((y - Y0) / (L * 0.12), 0, 1)
c_mouth = mix(col(0.62, 0.32, 0.34), col(0.22, 0.08, 0.10), mouth_d) * (0.85 + 0.25 * n_med[..., None])
c_mouth = mix(c_mouth, col(0.45, 0.20, 0.24), 0.3 * (0.5 + 0.5 * np.sin(y * 90)) * smoothstep(0.02, 0.0, np.abs(x) - 0.12))
c_teeth = mix(col(0.90, 0.87, 0.78), col(0.72, 0.66, 0.52), smoothstep(0.3, 0.8, n_fine))

base = c_body.copy()
for pid, cc in ((DORSAL, dark_fin), (PECTORAL, dark_fin), (FLUKE, c_fluke), (EYE, c_eye), (MOUTH, c_mouth),
                (TEETH, c_teeth), (TEETH + 0.5, c_teeth)):
    m = part == pid
    base[m] = (cc if cc.ndim == 1 else cc[m])
ao = np.clip(px_ao, 0, 1)
base = base * (0.55 + 0.45 * ao)[..., None]
base = np.clip(base, 0, 1)

# ---- roughness: wet glossy skin, dryer along the back, glassy eye
rough = 0.26 + 0.08 * (n_med - 0.5) + 0.05 * (n_fine - 0.5)
rough = rough + 0.10 * (1 - smoothstep(0.2, 1.0, ang)) * (is_body | (part == DORSAL))
rough = rough + 0.04 * white + 0.10 * scar_m
rough = np.where(part == EYE, 0.03, rough)
rough = np.where(part == MOUTH, 0.30, rough)
rough = np.where((part == TEETH) | (part == TEETH + 0.5), 0.32, rough)
rough = rough.astype(np.float32)

# ---- height map for the normal bake: wrinkles, creases, scars and slits
H = np.zeros_like(x)
# eye: crow's-feet radiating from the corners plus fine concentric creases
for sd, (ec, en, eh) in EYE_FRAMES.items():
    dv = P - np.array(eh)
    r = np.linalg.norm(dv, axis=-1)
    th = np.arctan2(dv[..., 2], dv[..., 1] * sd * 0 + dv[..., 1])
    win = smoothstep(0.035, 0.05, r) * (1 - smoothstep(0.09, 0.14, r)) * (np.sign(x) == sd)
    H += win * (0.6 * np.sin(th * 22 + 6 * n_med) + 0.4 * np.sin(r * 2 * np.pi / 0.011 + 3 * n_fine))
# blowhole: concentric creases fanning behind the crescent
bw = (1 - smoothstep(0.10, 0.16, np.abs(x))) * (ang < 0.8)
H += bw * smoothstep(0.012, 0.03, bv) * (1 - smoothstep(0.07, 0.13, bv)) * np.sin(bv * 2 * np.pi / 0.013 + 2 * n_med)
H -= 1.5 * bslit
# jaw corner: creases radiating back from the gape
for sd in (1, -1):
    kc = lip_point(S_CORNER)
    dyk, dzk = y - kc.y, z - kc.z
    r = np.hypot(dyk, dzk); th = np.arctan2(dzk, dyk)
    win = smoothstep(0.015, 0.03, r) * (1 - smoothstep(0.10, 0.17, r)) * smoothstep(-0.02, 0.02, dyk) * (np.sign(x) == sd) * is_body
    H += win * np.sin(th * 26 + 5 * n_med)
# pectoral armpit: folds around the flipper root
for sd in (1, -1):
    sh = pec_frames[sd][0]
    r = np.linalg.norm(P - np.array(sh), axis=-1)
    win = smoothstep(0.08, 0.14, r) * (1 - smoothstep(0.26, 0.36, r)) * (np.sign(x) == sd) * is_body
    H += 0.8 * win * np.sin(r * 2 * np.pi / 0.03 + 4 * n_med)
# throat folds and belly grooves
H += 0.5 * np.cos(2 * np.pi * x / 0.085) * smoothstep(0.12, 0.15, s) * (1 - smoothstep(0.22, 0.28, s)) * smoothstep(2.35, 2.75, ang) * is_body
H -= 1.2 * np.maximum(slit, umb)
# scars are slightly raised
H += 0.8 * scar_m
# faint skin stretch lines along the body
H += 0.25 * np.sin((y * 1.0 + 0.3 * z) * 2 * np.pi / 0.02 + 10 * n_warp) * smoothstep(0.4, 0.7, n_broad) * is_body
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
vo = nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 260
links.new(tc.outputs["Object"], vo.inputs["Vector"])
micro = nodes.new("ShaderNodeMath"); micro.operation = 'MULTIPLY_ADD'; micro.inputs[1].default_value = 0.6
links.new(wr.outputs["Fac"], micro.inputs[0]); links.new(vo.outputs["Distance"], micro.inputs[2])
att = nodes.new("ShaderNodeAttribute"); att.attribute_name = "part"
skin = nodes.new("ShaderNodeMapRange")          # skin parts 0..3 get the micro bump, eyes / mouth / teeth barely
skin.inputs["From Min"].default_value = 3.5; skin.inputs["From Max"].default_value = 3.6
skin.inputs["To Min"].default_value = 0.35; skin.inputs["To Max"].default_value = 0.03
links.new(att.outputs["Fac"], skin.inputs["Value"])
mm = nodes.new("ShaderNodeMath"); mm.operation = 'MULTIPLY'
links.new(micro.outputs[0], mm.inputs[0]); links.new(skin.outputs[0], mm.inputs[1])
hsum = nodes.new("ShaderNodeMath"); hsum.operation = 'ADD'
links.new(th_.outputs["Color"], hsum.inputs[0]); links.new(mm.outputs[0], hsum.inputs[1])
bump = nodes.new("ShaderNodeBump"); bump.inputs["Distance"].default_value = 0.0012
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

