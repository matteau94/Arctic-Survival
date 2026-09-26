p = r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_build.py"
t = open(p, encoding="utf8").read()


def rep(a, b):
    global t
    assert t.count(a) == 1, ("NOT FOUND/UNIQUE", a[:90])
    t = t.replace(a, b)


# colours are written to an 8-bit sRGB image, so these are display (sRGB) values
rep("""BLACK = col(0.020, 0.022, 0.028)     # charcoal with a cool blue-grey cast""",
    """BLACK = col(0.080, 0.087, 0.102)     # charcoal with a cool blue-grey cast (sRGB values)""")
rep("""spine = 0.72 + 0.28 * smoothstep(0.1, 1.3, ang)
mott = smoothstep(0.52, 0.75, n_broad) * smoothstep(0.7, 1.6, ang) * (0.6 + 0.4 * n_fine)
dark = BLACK * (spine * (0.85 + 0.35 * n_med))[..., None]
dark = dark + col(0.030, 0.034, 0.042) * mott[..., None]
dark_fin = BLACK * (0.9 + 0.3 * n_med + 0.15 * n_fine)[..., None]""",
"""spine = 0.62 + 0.38 * smoothstep(0.1, 1.4, ang)
mott = smoothstep(0.50, 0.78, n_broad) * smoothstep(0.6, 1.6, ang) * (0.5 + 0.5 * n_fine)
speck = smoothstep(0.10, 0.02, n_vor) * 0.5
dark = BLACK * (spine * (0.80 + 0.40 * n_med) * (0.92 + 0.16 * n_fine))[..., None]
dark = dark + col(0.055, 0.060, 0.072) * mott[..., None] + col(0.03, 0.03, 0.035) * speck[..., None]
dark_fin = BLACK * (0.80 + 0.35 * n_med + 0.2 * n_fine)[..., None]""")
rep("""SADDLE = col(0.36, 0.37, 0.40)""", """SADDLE = col(0.42, 0.43, 0.46)""")
rep("""vert = 1 - smoothstep(0.62, 1.12, ang + 1.5 * jit)""", """vert = 1 - smoothstep(0.80, 1.40, ang + 1.5 * jit)""")
rep("""dark = mix(dark, SADDLE * (0.86 + 0.12 * stri + 0.18 * (n_med - 0.5))[..., None], 0.92 * saddle * (0.86 + 0.14 * stri))""",
    """dark = mix(dark, SADDLE * (0.88 + 0.10 * stri + 0.18 * (n_med - 0.5))[..., None], 0.95 * saddle * (0.88 + 0.12 * stri))""")
# eye patch: clean oval, only a hint narrower at the front
rep("""half_h = 0.108 * np.sqrt(np.clip(1 - tq * tq, 0, 1)) * np.clip((tq + 1) / 2, 0, 1) ** 0.28 * 1.15""",
    """half_h = 0.100 * np.sqrt(np.clip(1 - tq * tq, 0, 1)) * (0.78 + 0.22 * np.clip((tq + 1) / 2, 0, 1)) * 1.12""")
rep("""EPC = (Y0 + L * 0.181, 0.175)""", """EPC = (Y0 + L * 0.184, 0.180)""")
# blowhole: dark matte slit, not a glint
rep("""H -= 1.5 * bslit""", """H -= 0.5 * bslit""")
rep("""rough = rough + 0.04 * white + 0.10 * scar_m""", """rough = rough + 0.04 * white + 0.10 * scar_m + 0.45 * bslit""")
# micro-detail a touch stronger
rep("""skin.inputs["To Min"].default_value = 0.16; skin.inputs["To Max"].default_value = 0.02""",
    """skin.inputs["To Min"].default_value = 0.24; skin.inputs["To Max"].default_value = 0.02""")
# lids: almond, lower and softer
rep("""    a_, b_, rl = EYE_R * 1.28, EYE_R * 0.90, 0.014""", """    a_, b_, rl = EYE_R * 1.38, EYE_R * 0.82, 0.012""")
rep("""nrm * (rl * 0.85 * thick * math.sin(2 * math.pi * q / 8) - 0.002)""",
    """nrm * (rl * 0.60 * thick * math.sin(2 * math.pi * q / 8) - 0.003)""")
open(p, "w", encoding="utf8").write(t)
print("edited ed5")
