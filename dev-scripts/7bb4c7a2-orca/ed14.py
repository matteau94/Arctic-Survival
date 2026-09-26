p = r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_build.py"
t = open(p, encoding="utf8").read()
def rep(a, b, cnt=1):
    global t
    assert t.count(a) == cnt, ("NOT FOUND/UNIQUE", t.count(a), a[:100])
    t = t.replace(a, b)
rep("""    tipz = lz + sg * (0.001 + 0.008 * (1 - size))                     # smaller teeth stop shorter""",
    """    tipz = lz + sg * (0.004 + 0.008 * (1 - size))                     # tips stay inside the jaw; smaller teeth shorter""")
rep("""c_mouth = mix(c_mouth, col(0.16, 0.12, 0.13), smoothstep(0.93, 0.965, a_m))          # pigmented inner lip""",
    """c_mouth = mix(c_mouth, col(0.10, 0.08, 0.09), smoothstep(0.90, 0.95, a_m))           # pigmented inner lip""")
rep("""    H += 0.28 * win * brk * np.sin(""", """    H += 0.18 * win * brk * np.sin(""")
rep("""dark = BLACK * (spine * (0.80 + 0.40 * n_med) * (0.86 + 0.16 * n_fine + 0.14 * n_hf))[..., None]""",
    """dark = BLACK * (spine * (0.80 + 0.40 * n_med) * (0.76 + 0.22 * n_fine + 0.30 * n_hf))[..., None]""")
rep("""BLACK = col(0.084, 0.087, 0.094)""", """BLACK = col(0.082, 0.087, 0.099)""")
rep("""light = mix(WHITE, DIATOM, 0.45 * smoothstep(0.40, 0.78, n_broad) + 0.20 * smoothstep(0.6, 0.9, n_vor))""",
    """light = mix(WHITE, DIATOM, 0.55 * smoothstep(0.40, 0.78, n_broad) + 0.25 * smoothstep(0.6, 0.9, n_vor))""")
rep("""light = light * (0.92 + 0.08 * n_med + 0.06 * n_hf)[..., None]""", """light = light * (0.88 + 0.08 * n_med + 0.12 * n_hf)[..., None]""")
rep("""dots = smoothstep(0.16, 0.07, n_spk) * border * smoothstep(0.35, 0.6, n_fine)""",
    """dots = smoothstep(0.20, 0.09, n_spk) * border * smoothstep(0.30, 0.6, n_fine)""")
rep("""fleck = smoothstep(0.07, 0.03, n_spk) * smoothstep(0.55, 0.75, n_hf) * (1 - white)""",
    """fleck = smoothstep(0.09, 0.04, n_spk) * smoothstep(0.50, 0.75, n_hf) * (1 - white)""")
rep("""H += 0.13 * np.sin(2 * np.pi * arc / 0.009""", """H += 0.17 * np.sin(2 * np.pi * arc / 0.009""")
rep("""H += 0.10 * (n_hf - 0.5) * skinm * smoothstep(0.14, 0.3, s)""", """H += 0.16 * (n_hf - 0.5) * skinm * smoothstep(0.14, 0.3, s)""")
rep('''bump.inputs["Distance"].default_value = 0.0014''', '''bump.inputs["Distance"].default_value = 0.0016''')
open(p, "w", encoding="utf8").write(t)
print("edited ed14")
