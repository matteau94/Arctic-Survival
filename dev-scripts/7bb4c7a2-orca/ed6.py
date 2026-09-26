p = r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_build.py"
t = open(p, encoding="utf8").read()
def rep(a, b):
    global t
    assert t.count(a) == 1, ("NOT FOUND/UNIQUE", a[:90])
    t = t.replace(a, b)
rep("""    ctr = hit - nrm * EYE_R * 0.45""", """    ctr = hit - nrm * EYE_R * 0.62""")
rep("""        c = hit + t1 * (a_ * math.cos(th)) + t2 * (b_ * math.sin(th) * (1 + 0.12 * math.cos(th)))
""", """        c = hit + t1 * (a_ * math.cos(th)) + t2 * (b_ * math.sin(th) * (1 + 0.12 * math.cos(th)))
        hc, _ = surface(c + nrm * 0.08, -nrm)          # sit the rim on the (sculpted) skin
        c = (hc if hc is not None else c) + nrm * 0.004
""")
rep("""nrm * (rl * 0.60 * thick * math.sin(2 * math.pi * q / 8) - 0.003)""",
    """nrm * (rl * 0.62 * thick * math.sin(2 * math.pi * q / 8))""")
rep("""feather = smoothstep(-0.004, 0.022, ds + 0.5 * jit) * (1 - smoothstep(0.055, 0.125, ds + 1.2 * jit - 0.035 * ang))
vert = 1 - smoothstep(0.80, 1.40, ang + 1.5 * jit)""",
"""feather = smoothstep(-0.004, 0.020, ds + 0.25 * jit) * (1 - smoothstep(0.07, 0.15, ds + 0.5 * jit - 0.03 * ang))
vert = 1 - smoothstep(0.85, 1.45, ang + 0.8 * jit)""")
open(p, "w", encoding="utf8").write(t)
print("edited ed6")
