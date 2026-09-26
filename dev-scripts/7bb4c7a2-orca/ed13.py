p = r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_build.py"
t = open(p, encoding="utf8").read()
def rep(a, b, cnt=1):
    global t
    assert t.count(a) == cnt, ("NOT FOUND/UNIQUE", t.count(a), a[:100])
    t = t.replace(a, b)
rep("""H += 0.34 * np.sin(2 * np.pi * arc / 0.012 + 7 * n_warp + 3 * n_str) * smoothstep(0.30, 0.60, n_str) \\""",
    """H += 0.13 * np.sin(2 * np.pi * arc / 0.009 + 7 * n_warp + 3 * n_str) * smoothstep(0.42, 0.72, n_str) \\""")
rep("""H += 0.22 * (n_hf - 0.5) * skinm * smoothstep(0.14, 0.3, s)""", """H += 0.10 * (n_hf - 0.5) * skinm * smoothstep(0.14, 0.3, s)""")
rep("""H += 0.5 * bw * smoothstep(0.03, 0.045, bv)""", """H += 0.28 * bw * smoothstep(0.03, 0.045, bv)""")
rep("""    H += 0.45 * win * brk * np.sin(""", """    H += 0.28 * win * brk * np.sin(""")
rep("""SADDLE = col(0.42, 0.43, 0.46)""", """SADDLE = col(0.50, 0.51, 0.54)""")
rep("""GUM_U, GUM_L = 0.028, -0.028""", """GUM_U, GUM_L = 0.022, -0.022""")
rep("""    base = V((side * rr * w, lp.y, lz + sg * 0.046))
    tipz = lz + sg * (0.002 + 0.010 * (1 - size))                     # smaller teeth stop shorter""",
    """    base = V((side * rr * w, lp.y, lz + sg * 0.044))
    tipz = lz + sg * (0.001 + 0.008 * (1 - size))                     # smaller teeth stop shorter""")
rep("""    rb = min(0.0125, 0.060 * w) * (0.72 + 0.28 * size)""", """    rb = min(0.0105, 0.052 * w) * (0.75 + 0.25 * size)""")
rep("""tt_up = np.clip(((lz_s + 0.046) - z) / 0.046, 0, 1)
tt_lo = np.clip((z - (lz_s - 0.046)) / 0.046, 0, 1)""", """tt_up = np.clip(((lz_s + 0.044) - z) / 0.044, 0, 1)
tt_lo = np.clip((z - (lz_s - 0.044)) / 0.044, 0, 1)""")
rep("""depth = smoothstep(0.045, S_BACK, s)""", """depth = smoothstep(0.085, S_BACK + 0.004, s)""")
rep("""rough = np.where(is_pal | is_flr, 0.24 + 0.06 * gum + 0.04 * n_fine, rough)""",
    """rough = np.where(is_pal | is_flr, 0.24 + 0.06 * gum + 0.04 * n_fine + 0.14 * depth, rough)""")
rep("""    d -= 0.008 * g(sv, 0.018, 0.008) * g(ang, 0.0, 1.1) * smoothstep(0.006, 0.013, sv)""",
    """    d -= 0.004 * g(sv, 0.020, 0.009) * g(ang, 0.0, 1.1) * smoothstep(0.006, 0.013, sv)""")
rep("""    reach = 0.035 if abs(pa_[vi] - FLUKE) < 0.5 else 0.08""", """    reach = 0.03 if abs(pa_[vi] - FLUKE) < 0.5 else 0.055""")
open(p, "w", encoding="utf8").write(t)
print("edited ed13")
