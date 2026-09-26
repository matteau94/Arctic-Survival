SP = r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\7bb4c7a2-2c8e-4793-b5ee-2fc544b80253\scratchpad"
p = r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_build.py"
t = open(p, encoding="utf8").read()


def rep(a, b, cnt=1):
    global t
    assert t.count(a) == cnt, ("NOT FOUND/UNIQUE", t.count(a), a[:100])
    t = t.replace(a, b)


# ================================================================ resolution
rep("RES = 2048", "RES = 4096")
rep("scene.render.bake.margin = 24", "scene.render.bake.margin = 16")
rep("""    return np.array(img.pixels[:], dtype=np.float32).reshape(RES, RES, 4)""",
    """    buf = np.empty(RES * RES * 4, np.float32); img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    return buf.reshape(RES, RES, 4)[..., :3].copy()""")
rep("""px_ao = np.array(ao_img.pixels[:], dtype=np.float32).reshape(RES, RES, 4)[..., 0]""",
    """_buf = np.empty(RES * RES * 4, np.float32); ao_img.pixels.foreach_get(_buf)
px_ao = _buf.reshape(RES, RES, 4)[..., 0].copy(); del _buf""")
rep("""px_noise2 = bake_emit(noise2_socket, new_image("_noise2", True))""",
    """px_noise2 = bake_emit(noise2_socket, new_image("_noise2", True))
px_noise3 = bake_emit(noise3_socket, new_image("_noise3", True))""")
rep('''px_pos = bake_emit(pos_socket, new_image("_pos", True))''', '''def noise3_socket():
    """High-frequency detail for 4K maps. R: fine mottle (~1 cm), G: voronoi speckle cells,
    B: streaks stretched along the body (saddle striations / skin grain)."""
    tc = nodes.new("ShaderNodeTexCoord")
    c = nodes.new("ShaderNodeCombineColor")
    nz = nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 90; nz.inputs["Detail"].default_value = 3
    links.new(tc.outputs["Object"], nz.inputs["Vector"]); links.new(nz.outputs["Fac"], c.inputs[0])
    vo = nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 150
    links.new(tc.outputs["Object"], vo.inputs["Vector"]); links.new(vo.outputs["Distance"], c.inputs[1])
    vm = nodes.new("ShaderNodeVectorMath"); vm.operation = 'MULTIPLY'; vm.inputs[1].default_value = (7.0, 0.6, 7.0)
    links.new(tc.outputs["Object"], vm.inputs[0])
    ns = nodes.new("ShaderNodeTexNoise"); ns.inputs["Scale"].default_value = 9; ns.inputs["Detail"].default_value = 4
    links.new(vm.outputs[0], ns.inputs["Vector"]); links.new(ns.outputs["Fac"], c.inputs[2])
    return c.outputs[0]


px_pos = bake_emit(pos_socket, new_image("_pos", True))''')
rep('''for nm_ in ("_pos", "_nrm", "_part", "_noise", "_noise2", "_ao", "_normal", "_height"):''',
    '''for nm_ in ("_pos", "_nrm", "_part", "_noise", "_noise2", "_noise3", "_ao", "_normal", "_height"):''')

# ================================================================ rounder nose (no pole streaks)
rep('''def prof(s):
    return [hermite(k, s) for k in KEYS]''', '''S_NOSE = 0.022


def prof(s):
    v = [hermite(k, s) for k in KEYS]
    if s < S_NOSE:                        # elliptical nose cap: smooth all the way into the pole
        f = math.sqrt(max(0.0, 1 - (1 - s / S_NOSE) ** 2))
        vn = [hermite(k, S_NOSE) for k in KEYS]
        v = [vn[0] * f, vn[1] * f, vn[2] * f, v[3]]
    return v''')
rep('''DENS = [(0.0, 0.006), (0.03, 0.010), (0.14, 0.011), (0.155, 0.0048), (0.186, 0.0048), (0.21, 0.014),
        (0.28, 0.040), (0.64, 0.040), (0.72, 0.030), (0.945, 0.026)]
ss = [0.003]''', '''DENS = [(0.0, 0.0016), (0.006, 0.0035), (0.022, 0.008), (0.035, 0.011), (0.14, 0.011), (0.155, 0.0048),
        (0.186, 0.0048), (0.21, 0.015), (0.28, 0.044), (0.64, 0.044), (0.72, 0.032), (0.945, 0.028)]
ss = [0.0008]''')
rep('''body = mesh_from_rings("Body", rings, BODY, cap_start=V((0, Y0 - 0.004, PROFILE[0][4])),''',
    '''body = mesh_from_rings("Body", rings, BODY, cap_start=V((0, Y0, PROFILE[0][4])),''')

# ================================================================ mouth + teeth
i = t.index("# ======================================================================= 2. mouth interior + teeth")
j = t.index("# ======================================================================= 3. eyes")
t = t[:i] + open(SP + r"\mouth_block2.py", encoding="utf8").read() + t[j:]

# ================================================================ eye a touch bigger, blowhole deeper
rep("EYE_R = 0.030", "EYE_R = 0.034")
rep("    ctr = hit - nrm * EYE_R * 0.62", "    ctr = hit - nrm * EYE_R * 0.58")
rep("""    d -= 0.020 * g(v, 0.0, 0.0085) * lat * topm""", """    d -= 0.034 * g(v, 0.0, 0.0105) * lat * topm""")
rep("""bslit = g(bv, 0.0, 0.0065) * (1 - smoothstep(0.07, 0.105, np.abs(x))) * (ang < 0.6)""",
    """bslit = g(bv, 0.0, 0.0095) * (1 - smoothstep(0.07, 0.105, np.abs(x))) * (ang < 0.6)""")

# ================================================================ UVs: seams + mirrored halves, then custom normals
i = t.index("# fin-root seams: bend the fin normals toward the body normal")
j = t.index("bpy.ops.object.mode_set(mode='EDIT')\nbpy.ops.mesh.select_all(action='SELECT')\nbpy.ops.uv.smart_project(")
k = t.index('me.uv_layers[0].name = "UVMap"\n', j) + len('me.uv_layers[0].name = "UVMap"\n')
normals_block = t[i:j]
uv_block = '''# ----------------------------------------------------------------------- UVs: mirrored halves
# The pattern is left/right symmetric, so only the x > 0 half is unwrapped: seams cut the body into
# head / mid-body / tail pieces at ring loops, and split every fin, fluke, eye and tooth into its two
# faces; islands are unwrapped (angle based), scale-averaged and packed tightly, then each x < 0 face
# takes the UVs of its mirror image.  That doubles the texel density of the 4K maps.
from mathutils.kdtree import KDTree
bm = bmesh.new(); bm.from_mesh(me)
bm.faces.ensure_lookup_table()
play = bm.verts.layers.float.get("part")
pec_thick = pec_frames[1][3]
eye_axis = EYE_FRAMES[1][1]


def fgroup(f):
    pid = round(sum(v[play] for v in f.verts) / len(f.verts) * 2) / 2
    c = f.calc_center_median()
    if pid == BODY:
        return ("B", int(np.digitize(c.y, [-1.75, 0.45])))
    if pid == PECTORAL:
        return ("P", f.normal.dot(pec_thick) > 0)
    if pid == FLUKE:
        return ("F", f.normal.z > 0)
    if pid == EYE:
        return ("E", f.normal.dot(eye_axis) > 0.2)
    if pid >= TEETH:
        return ("T", f.normal.y > 0)
    return (str(pid), 0)


fg = {f.index: fgroup(f) for f in bm.faces}
nseam = 0
for e in bm.edges:
    lf_ = e.link_faces
    if len(lf_) == 2 and fg[lf_[0].index] != fg[lf_[1].index]:
        e.seam = True; nseam += 1
for f in bm.faces:
    f.select = f.calc_center_median().x > 0
bm.to_mesh(me); bm.free()
print("[build] uv seams", nseam)

bpy.ops.object.mode_set(mode='EDIT')
scene.tool_settings.use_uv_select_sync = True
bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
bpy.ops.uv.average_islands_scale()
try:
    bpy.ops.uv.pack_islands(rotate=True, margin=0.0012, shape_method='CONCAVE')
except TypeError:
    bpy.ops.uv.pack_islands(rotate=True, margin=0.0012)
bpy.ops.object.mode_set(mode='OBJECT')
me.uv_layers[0].name = "UVMap"

bm = bmesh.new(); bm.from_mesh(me)
uvl = bm.loops.layers.uv.active
posf = [f for f in bm.faces if f.calc_center_median().x > 0]
kd = KDTree(len(posf))
for i_, f in enumerate(posf):
    kd.insert(f.calc_center_median(), i_)
kd.balance()
for f in bm.faces:
    c = f.calc_center_median()
    if c.x > 0:
        continue
    gf = posf[kd.find(V((-c.x, c.y, c.z)))[1]]
    for l_ in f.loops:
        pm = V((-l_.vert.co.x, l_.vert.co.y, l_.vert.co.z))
        best = min(gf.loops, key=lambda gl: (gl.vert.co - pm).length_squared)
        l_[uvl].uv = best[uvl].uv.copy()
bm.to_mesh(me); bm.free()
print("[build] uv: unwrapped the x > 0 half, mirrored onto x < 0")

'''
t = t[:i] + uv_block + normals_block + t[k:]

# ================================================================ painting on mirrored UVs
rep("""P = px_pos[..., :3] * SPAN + np.array(LO)""",
    """P = px_pos[..., :3] * SPAN + np.array(LO)
P[..., 0] = np.abs(P[..., 0])                  # mirrored UVs: paint the symmetric (x >= 0) half""")
rep("""N = px_nrm[..., :3] * 2 - 1""", """N = px_nrm[..., :3] * 2 - 1
N[..., 0] = np.abs(N[..., 0])
del px_pos, px_nrm""")
rep("""n_fine, n_vor, n_warp = px_noise2[..., 0], px_noise2[..., 1], px_noise2[..., 2]""",
    """n_fine, n_vor, n_warp = px_noise2[..., 0], px_noise2[..., 1], px_noise2[..., 2]
n_hf, n_spk, n_str = px_noise3[..., 0], px_noise3[..., 1], px_noise3[..., 2]""")
rep("""    sd = 1 if k % 2 else -1""", """    sd = 1""")
rep("""for k in range(22):""", """for k in range(18):""")
rep("""    scar_m[box] = np.maximum(scar_m[box], m * rng.uniform(0.35, 0.8))""",
    """    scar_m[box] = np.maximum(scar_m[box], m * rng.uniform(0.55, 1.0))""")

# ================================================================ richer albedo
rep("""dark = BLACK * (spine * (0.80 + 0.40 * n_med) * (0.92 + 0.16 * n_fine))[..., None]""",
    """dark = BLACK * (spine * (0.80 + 0.40 * n_med) * (0.86 + 0.16 * n_fine + 0.14 * n_hf))[..., None]""")
rep("""light = mix(WHITE, DIATOM, 0.35 * smoothstep(0.42, 0.78, n_broad) + 0.15 * smoothstep(0.6, 0.9, n_vor))
light = light * (0.94 + 0.08 * n_med + 0.03 * n_fine)[..., None]
c_body = mix(dark, light, white)""",
"""light = mix(WHITE, DIATOM, 0.45 * smoothstep(0.40, 0.78, n_broad) + 0.20 * smoothstep(0.6, 0.9, n_vor))
light = mix(light, col(0.78, 0.83, 0.88), 0.30 * smoothstep(0.45, 0.75, n_fine) * (1 - smoothstep(0.4, 0.7, n_broad)))  # cool shift
light = light * (0.92 + 0.08 * n_med + 0.06 * n_hf)[..., None]
c_body = mix(dark, light, white)
# pigment speckle along the black / white borders (dark flecks in the white, pale flecks in the black)
border = g(ang - thr, 0.0, 0.06) * (s > 0.12) * is_body
dots = smoothstep(0.16, 0.07, n_spk) * border * smoothstep(0.35, 0.6, n_fine)
c_body = mix(c_body, np.where(white[..., None] > 0.5, dark, light * 0.8), 0.85 * dots)
# fine pale flecks scattered over the dark skin
fleck = smoothstep(0.07, 0.03, n_spk) * smoothstep(0.55, 0.75, n_hf) * (1 - white)
c_body = mix(c_body, col(0.20, 0.21, 0.23), 0.6 * fleck)""")
rep("""stri = smoothstep(0.35, 0.75, n_streak) * (0.6 + 0.4 * n_fine)""",
    """stri = smoothstep(0.30, 0.70, n_str) * (0.6 + 0.4 * n_hf)""")
# dark ring around the eye, lighter iris for readability
rep("""    irc = mix(col(0.16, 0.09, 0.05), col(0.07, 0.04, 0.025), smoothstep(0.84, 0.95, ca)) * (0.85 + 0.3 * n_fine[..., None])""",
    """    irc = mix(col(0.30, 0.17, 0.08), col(0.10, 0.05, 0.03), smoothstep(0.84, 0.95, ca)) * (0.85 + 0.3 * n_fine[..., None])""")
rep("""c_body = mix(c_body, col(0.004, 0.004, 0.006), 0.8 * bslit)""",
    """c_body = mix(c_body, col(0.004, 0.004, 0.006), 0.9 * bslit)
eh_ = np.array(EYE_FRAMES[1][2])
c_body = c_body * (1 - 0.45 * g(np.linalg.norm(P - eh_, axis=-1), 0.0, 0.07))[..., None]   # dark eye surround""")
# teeth / gums follow the new geometry
rep("""tt_up = np.clip(((lz_s + 0.014) - z) / 0.055, 0, 1)
tt_lo = np.clip((z - (lz_s - 0.014)) / 0.055, 0, 1)""", """tt_up = np.clip(((lz_s + 0.046) - z) / 0.046, 0, 1)
tt_lo = np.clip((z - (lz_s - 0.046)) / 0.046, 0, 1)""")
rep("""gum = g(a_m, 0.905, 0.05)""", """gum = g(a_m, np.where(is_flr, 0.845, 0.90), 0.05)""")
rep("""c_mouth = mix(c_mouth, col(0.16, 0.12, 0.13), smoothstep(0.94, 0.99, a_m))           # pigmented inner lip""",
    """c_mouth = mix(c_mouth, col(0.16, 0.12, 0.13), smoothstep(0.93, 0.965, a_m))          # pigmented inner lip""")

# ================================================================ roughness 0.15 - 0.5
rep("""rough = 0.26 + 0.08 * (n_med - 0.5) + 0.05 * (n_fine - 0.5)
rough = rough + 0.10 * (1 - smoothstep(0.2, 1.0, ang)) * (is_body | (part == DORSAL))
rough = rough + 0.04 * white + 0.10 * scar_m + 0.45 * bslit
rough = rough + 0.14 * smoothstep(0.55, 0.80, n_broad) * smoothstep(0.4, 0.7, n_fine) * (is_body | (part == DORSAL))  # drier matte patches""",
"""skinm = is_body | (part == DORSAL) | (part == PECTORAL) | (part == FLUKE)
rough = 0.27 + 0.10 * (n_med - 0.5) + 0.08 * (n_hf - 0.5)
rough = rough + 0.16 * (1 - smoothstep(0.15, 1.1, ang)) * is_body + 0.14 * (part == DORSAL)      # drier back / fin
rough = rough - 0.09 * (1 - smoothstep(0.14, 0.30, s)) * is_body                                  # wet glossy head
rough = rough - 0.07 * smoothstep(1.7, 2.5, ang) * is_body                                          # wet lower body
rough = rough + 0.16 * smoothstep(0.52, 0.80, n_broad) * smoothstep(0.35, 0.7, n_fine) * skinm      # dry matte patches
rough = rough + 0.04 * white + 0.28 * scar_m + 0.45 * bslit
rough = np.clip(rough, 0.12, 0.62)""")

# ================================================================ normal detail
rep("""H += 0.5 * np.cos(2 * np.pi * x / 0.085) * smoothstep(0.12, 0.15, s) * (1 - smoothstep(0.22, 0.28, s)) * smoothstep(2.35, 2.75, ang) * is_body""",
    """H += 1.0 * np.cos(2 * np.pi * x / 0.085 + 2 * n_warp) * smoothstep(0.12, 0.15, s) * (1 - smoothstep(0.24, 0.30, s)) * smoothstep(2.3, 2.75, ang) * is_body
# fine skin striation running along the body (broken up, fading onto the head and belly)
arc = ang * rad_t
H += 0.34 * np.sin(2 * np.pi * arc / 0.012 + 7 * n_warp + 3 * n_str) * smoothstep(0.30, 0.60, n_str) \\
    * smoothstep(0.17, 0.30, s) * (1 - 0.5 * white) * is_body
H += 0.22 * (n_hf - 0.5) * skinm * smoothstep(0.14, 0.3, s)""")
rep('''bump = nodes.new("ShaderNodeBump"); bump.inputs["Distance"].default_value = 0.0010''',
    '''bump = nodes.new("ShaderNodeBump"); bump.inputs["Distance"].default_value = 0.0014''')
open(p, "w", encoding="utf8").write(t)
print("edited ed12")
