p = r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_build.py"
t = open(p, encoding="utf8").read()


def rep(a, b, cnt=1):
    global t
    assert t.count(a) == cnt, ("NOT FOUND/UNIQUE", t.count(a), a[:90])
    t = t.replace(a, b)


# ---- lining: interior profile + edges built from the analytic skin, pulled 8 % inside it
rep('''def lining_point(s, a, upper):
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
    return V((a * xf * w, lp.y, lz + dz * fold))''',
'''def lining_point(s, a, upper):
    lp = lip_point(s)
    w, lz = abs(lp.x), lp.z
    fold = 1 - sstep(S_BACK - 0.04, S_BACK, s)
    front = sstep(0.004, 0.030, s)
    aa = min(abs(a), 0.94) / 0.94                                     # interior: 0 midline .. 1 gum
    if upper:
        dz = 0.006 + 0.048 * (1 - aa * aa) * front                      # vaulted palate
        dz -= 0.011 * math.exp(-((aa - 0.975) / 0.05) ** 2)             # gum ridge under the tooth row
    else:
        tongue = sstep(0.030, 0.065, s) * front
        dz = -0.012 - 0.014 * (1 - aa * aa) * front                     # floor of the mouth
        dz += 0.032 * math.exp(-(aa / 0.55) ** 2) * tongue              # rounded tongue mound
        dz -= 0.005 * math.exp(-(aa / 0.075) ** 2) * tongue             # median groove
        dz += 0.011 * math.exp(-((aa - 0.975) / 0.05) ** 2)             # gum ridge under the tooth row
    inner = V((math.copysign(aa * 0.94 * 0.975 * w, a), lp.y, lz + dz * fold))
    if abs(a) <= 0.94:
        return inner
    # the last strip runs from the gum up (or down) into the jaw, ending 8 % inside the skin
    c = V((0, lp.y, lz))
    e = ring_point(s, PHI_M - (0.30 if upper else -0.30) * fold)
    e.x = math.copysign(abs(e.x), a)
    e = c + 0.92 * (e - c)
    tq = (abs(a) - 0.94) / 0.06
    return inner.lerp(e, tq)''')
rep("""TOOTH_R = 0.915                      # tooth row, as a fraction of the lip half-width""",
    """TOOTH_R = 0.905                      # tooth row, as a fraction of the lip half-width""")
rep("""    rb = min(0.0125, 0.066 * rad) * (0.72 + 0.28 * size)""", """    rb = min(0.0125, 0.058 * rad) * (0.72 + 0.28 * size)""")
rep("""        tooth(0.020 + 0.074 * i / (NT_UP - 1), side, True,""", """        tooth(0.024 + 0.070 * i / (NT_UP - 1), side, True,""")
rep("""        tooth(0.020 + 0.074 * (i + 0.5) / (NT_UP - 1), side, False,""", """        tooth(0.024 + 0.070 * (i + 0.5) / (NT_UP - 1), side, False,""")
# gum colour position follows the new profile (gum ridge at ~0.915 w)
rep("""gum = g(a_m, 0.93, 0.05)""", """gum = g(a_m, 0.905, 0.05)""")
rep("""c_mouth = mix(c_mouth, col(0.16, 0.12, 0.13), smoothstep(0.965, 1.0, a_m))           # pigmented inner lip""",
    """c_mouth = mix(c_mouth, col(0.16, 0.12, 0.13), smoothstep(0.94, 0.99, a_m))           # pigmented inner lip""")

# ---- eye patch: slimmer
rep("""half_h = (0.085 / 0.84) * np.sqrt""", """half_h = (0.072 / 0.84) * np.sqrt""")
rep("""tq = ey / 0.315                                    # ~0.63 m long, ~0.17 m tall (3.7 : 1)""",
    """tq = ey / 0.325                                    # ~0.65 m long, ~0.145 m tall (4.5 : 1 flat, ~3.5 : 1 on the curved head)""")

# ---- no noise-contour lines on the head (they read as blotches in the wet highlight)
rep("""H += 0.30 * (1 - smoothstep(0.0, 0.02, np.abs(n_streak - 0.5))) * is_body        # sparse long stretch creases""",
    """H += 0.22 * (1 - smoothstep(0.0, 0.02, np.abs(n_streak - 0.5))) * is_body * smoothstep(0.22, 0.32, s)  # sparse long stretch creases""")
rep("""scar_m = np.maximum(scar_m, 0.35 * (1 - smoothstep(0.0, 0.010, np.abs(n_streak - 0.5))) * smoothstep(0.6, 0.72, n_broad) * bodyside)""",
    """scar_m = np.maximum(scar_m, 0.35 * (1 - smoothstep(0.0, 0.010, np.abs(n_streak - 0.5))) * smoothstep(0.6, 0.72, n_broad) * bodyside * (s > 0.24))""")

# ---- vertex budget (~40k)
rep("""        (0.28, 0.036), (0.64, 0.036), (0.72, 0.026), (0.945, 0.022)]""",
    """        (0.28, 0.040), (0.64, 0.040), (0.72, 0.030), (0.945, 0.026)]""")
open(p, "w", encoding="utf8").write(t)
print("edited ed11")
