p = r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_build.py"
t = open(p, encoding="utf8").read()
def rep(a, b):
    global t
    assert t.count(a) == 1, ("NOT FOUND/UNIQUE", a[:90])
    t = t.replace(a, b)
# fluke planform: broader root chord, lobes curving back to pointed, slightly recurved tips
rep("""def fluke_le(u):
    return 2.50 + 0.55 * u ** 1.7""", """def fluke_le(u):
    return 2.47 + 0.61 * u ** 1.6""")
rep("""def fluke_te(u):
    return 2.90 + 0.28 * u ** 1.2          # central notch at u = 0""",
    """def fluke_te(u):
    return 2.86 + 0.34 * u - 0.12 * u ** 3 - 0.035 * math.exp(-(u / 0.06) ** 2)   # median notch at u = 0""")
rep("""inside = np.minimum(y - (2.50 + 0.55 * u ** 1.7), (2.90 + 0.28 * u ** 1.2) - y)""",
    """inside = np.minimum(y - (2.47 + 0.61 * u ** 1.6), (2.86 + 0.34 * u - 0.12 * u ** 3 - 0.035 * np.exp(-(u / 0.06) ** 2)) - y)""")
rep("""cap_start=V((-FLUKE_SPAN * 1.03, 3.15, FLUKE_Z - 0.062))""", """cap_start=V((-FLUKE_SPAN * 1.025, 3.09, FLUKE_Z - 0.062))""")
rep("""cap_end=V((FLUKE_SPAN * 1.03, 3.15, FLUKE_Z - 0.062))""", """cap_end=V((FLUKE_SPAN * 1.025, 3.09, FLUKE_Z - 0.062))""")
# dorsal fin: bend spread over the whole height
rep("""        root = sstep(0.08, 0.20, h)
        top = sstep(0.45, 0.65, h)""", """        root = sstep(0.06, 0.22, h)
        top = sstep(0.30, 0.85, h)""")
# saddle striations: faint streaks running along the body, not bands
rep("""stri_c = (y - 0.55 * np.abs(x) * 0 - 0.9 * (0.66 - z)) * 55 + 9 * n_warp
stri = 0.5 + 0.5 * np.sin(stri_c)""", """stri = smoothstep(0.35, 0.75, n_streak) * (0.6 + 0.4 * n_fine)""")
# belly slits: subtle
rep("""c_body = mix(c_body, col(0.12, 0.11, 0.11), 0.85 * np.maximum(slit, umb))""",
    """c_body = mix(c_body, col(0.30, 0.27, 0.27), 0.55 * np.maximum(slit, umb))""")
rep("""slit = g(x, 0.0, 0.006) * smoothstep(0.600, 0.604, s) * (1 - smoothstep(0.652, 0.656, s)) * (ang > 2.8)""",
    """slit = g(x, 0.0, 0.005) * smoothstep(0.600, 0.612, s) * (1 - smoothstep(0.640, 0.652, s)) * (ang > 2.8)""")
rep("""umb = g(np.hypot(x, y - (Y0 + L * 0.50)), 0.0, 0.010) * (ang > 2.8)""",
    """umb = g(np.hypot(x, y - (Y0 + L * 0.50)), 0.0, 0.007) * (ang > 2.8)""")
# lids: a soft almond mound around the eye rather than a tube
rep("""    a_, b_, rl = EYE_R * 1.38, EYE_R * 0.82, 0.012""", """    a_, b_, rl = EYE_R * 1.45, EYE_R * 1.15, 0.016""")
rep("""        c = (hc if hc is not None else c) + nrm * 0.004""", """        c = (hc if hc is not None else c) + nrm * 0.0015""")
rep("""nrm * (rl * 0.62 * thick * math.sin(2 * math.pi * q / 8))""",
    """nrm * (rl * 0.42 * thick * math.sin(2 * math.pi * q / 8))""")
open(p, "w", encoding="utf8").write(t)
print("edited ed7")
