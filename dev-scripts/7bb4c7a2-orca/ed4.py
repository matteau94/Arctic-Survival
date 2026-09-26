p = r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_build.py"
t = open(p, encoding="utf8").read()


def rep(a, b):
    global t
    assert t.count(a) == 1, ("NOT FOUND/UNIQUE", a[:90])
    t = t.replace(a, b)


# ---- vertex budget
rep("""DENS = [(0.0, 0.006), (0.03, 0.009), (0.13, 0.010), (0.150, 0.0040), (0.192, 0.0040), (0.215, 0.012),
        (0.28, 0.030), (0.66, 0.030), (0.72, 0.020), (0.945, 0.016)]""",
    """DENS = [(0.0, 0.006), (0.03, 0.010), (0.14, 0.011), (0.155, 0.0048), (0.186, 0.0048), (0.21, 0.014),
        (0.28, 0.036), (0.64, 0.036), (0.72, 0.026), (0.945, 0.022)]""")
rep("""        for j in range(24):
            ph = 2 * math.pi * j / 24""", """        for j in range(20):
            ph = 2 * math.pi * j / 20""")
rep("""    for i in range(22):
        u = i / 21
        w = hermite(WK, u)""", """    for i in range(18):
        u = i / 17
        w = hermite(WK, u)""")
rep("""print("[build] mesh verts", len(me.vertices), "faces", len(me.polygons))""",
    """print("[build] mesh verts", len(me.vertices), "faces", len(me.polygons), "body rings", NR)""")

# ---- lids: bigger, sit proud of the skin
rep("""    a_, b_, rl = EYE_R * 1.30, EYE_R * 0.92, 0.011""", """    a_, b_, rl = EYE_R * 1.28, EYE_R * 0.90, 0.014""")
rep("""        lr.append([c + radial * (rl * math.cos(2 * math.pi * q / 10)) + nrm * (rl * 0.70 * thick * math.sin(2 * math.pi * q / 10) - 0.004)
                   for q in range(10)])""",
    """        lr.append([c + radial * (rl * math.cos(2 * math.pi * q / 8)) + nrm * (rl * 0.85 * thick * math.sin(2 * math.pi * q / 8) - 0.002)
                   for q in range(8)])""")
rep("""    for i in range(32):
        th = 2 * math.pi * i / 32
        c = hit + t1""", """    for i in range(28):
        th = 2 * math.pi * i / 28
        c = hit + t1""")

# ---- eye patch: an oval, only mildly narrower at the front
rep("""half_h = 0.112 * np.sqrt(np.clip(1 - tq * tq, 0, 1)) * np.clip((tq + 1) / 2, 0, 1) ** 0.6 * 1.32""",
    """half_h = 0.108 * np.sqrt(np.clip(1 - tq * tq, 0, 1)) * np.clip((tq + 1) / 2, 0, 1) ** 0.28 * 1.15""")

# ---- saddle: clearly grey, faint striations
rep("""SADDLE = col(0.34, 0.35, 0.38)""", """SADDLE = col(0.36, 0.37, 0.40)""")
rep("""vert = 1 - smoothstep(0.55, 1.05, ang + 1.5 * jit)""", """vert = 1 - smoothstep(0.62, 1.12, ang + 1.5 * jit)""")
rep("""dark = mix(dark, SADDLE * (0.78 + 0.22 * stri + 0.15 * (n_med - 0.5))[..., None], 0.88 * saddle * (0.7 + 0.3 * stri))""",
    """dark = mix(dark, SADDLE * (0.86 + 0.12 * stri + 0.18 * (n_med - 0.5))[..., None], 0.92 * saddle * (0.86 + 0.14 * stri))""")

# ---- scars: fewer, longer, finer, softer
rep("""for k in range(30):""", """for k in range(22):""")
rep("""    ln = rng.uniform(0.12, 0.45)
    nl = int(rng.integers(2, 4))
    sp = rng.uniform(0.022, 0.04)
    wd = rng.uniform(0.0022, 0.0040)""", """    ln = rng.uniform(0.22, 0.60)
    nl = int(rng.integers(2, 5))
    sp = rng.uniform(0.025, 0.045)
    wd = rng.uniform(0.0016, 0.0030)""")
rep("""    scar_m[box] = np.maximum(scar_m[box], m * rng.uniform(0.5, 1.0))""",
    """    scar_m[box] = np.maximum(scar_m[box], m * rng.uniform(0.35, 0.8))""")

# ---- wrinkles: irregular, noise-broken, subtler
rep("""    H += win * (0.6 * np.sin(th * 22 + 6 * n_med) + 0.4 * np.sin(r * 2 * np.pi / 0.011 + 3 * n_fine))""",
    """    brk = smoothstep(0.35, 0.65, n_fine)
    H += 0.45 * win * brk * np.sin(r * 2 * np.pi / 0.012 + 8 * n_warp + 3 * np.sin(th * 3))""")
rep("""    win = smoothstep(0.035, 0.05, r) * (1 - smoothstep(0.09, 0.14, r)) * (np.sign(x) == sd)""",
    """    win = smoothstep(0.036, 0.046, r) * (1 - smoothstep(0.065, 0.10, r)) * (np.sign(x) == sd)""")
rep("""H += bw * smoothstep(0.012, 0.03, bv) * (1 - smoothstep(0.07, 0.13, bv)) * np.sin(bv * 2 * np.pi / 0.013 + 2 * n_med)""",
    """H += 0.5 * bw * smoothstep(0.03, 0.045, bv) * (1 - smoothstep(0.07, 0.12, bv)) * smoothstep(0.3, 0.6, n_fine) \\
    * np.sin(bv * 2 * np.pi / 0.016 + 7 * n_warp)""")
rep("""    H += win * np.sin(th * 26 + 5 * n_med)""", """    H += 0.55 * win * smoothstep(0.3, 0.6, n_fine) * np.sin(th * 20 + 9 * n_warp)""")
rep("""    H += 0.8 * win * np.sin(r * 2 * np.pi / 0.03 + 4 * n_med)""",
    """    H += 0.5 * win * smoothstep(0.35, 0.65, n_fine) * np.sin(r * 2 * np.pi / 0.035 + 9 * n_warp)""")
rep("""H += 0.25 * np.sin((y * 1.0 + 0.3 * z) * 2 * np.pi / 0.02 + 10 * n_warp) * smoothstep(0.4, 0.7, n_broad) * is_body""",
    """H += 0.30 * (1 - smoothstep(0.0, 0.02, np.abs(n_streak - 0.5))) * is_body        # sparse long stretch creases""")
rep("""H += 0.8 * scar_m""", """H += 0.6 * scar_m""")
rep("""skin.inputs["To Min"].default_value = 0.35; skin.inputs["To Max"].default_value = 0.03""",
    """skin.inputs["To Min"].default_value = 0.16; skin.inputs["To Max"].default_value = 0.02""")
rep("""bump = nodes.new("ShaderNodeBump"); bump.inputs["Distance"].default_value = 0.0012""",
    """bump = nodes.new("ShaderNodeBump"); bump.inputs["Distance"].default_value = 0.0010""")
# ---- mouth: pinker near the lips, palate / tongue shading
rep("""c_mouth = mix(col(0.62, 0.32, 0.34), col(0.22, 0.08, 0.10), mouth_d) * (0.85 + 0.25 * n_med[..., None])""",
    """c_mouth = mix(col(0.70, 0.38, 0.40), col(0.26, 0.09, 0.11), mouth_d ** 0.8) * (0.85 + 0.25 * n_med[..., None])""")
open(p, "w", encoding="utf8").write(t)
print("edited ed4")
