p = r"C:\Users\leosp\Documents\Blender\Artic-Survival\human_build.py"
s = open(p).read()
R = [
("    V_, F_ = loft(rings, cap0=path[0], cap1=path[-1])\n    F_ = orient_out(V_, F_, axis_fn=lambda p: path[np.argmin(np.linalg.norm(path - p, axis=1))])\n    return V_, F_, seam_column(len(rings), 32, 16)\n\n\nVru, Fru, sru = build_ruff(RIM)\nadd_part(\"ruff\", Vru, Fru, FUR, seams=sru)",
 "    V_, F_ = loft(rings, cap0=path[0], cap1=path[-1])\n    F_ = orient_out(V_, F_, axis_fn=lambda p: path[np.argmin(np.linalg.norm(path - p, axis=1))])\n    lu = np.concatenate([np.repeat(s, len(th)), [0.0, s[-1]]])\n    lv = np.concatenate([np.tile(th / (2 * np.pi), len(s)), [0.0, 0.0]])\n    return V_, F_, seam_column(len(rings), 32, 16), lu, lv\n\n\nVru, Fru, sru, luru, lvru = build_ruff(RIM)\nadd_part(\"ruff\", Vru, Fru, FUR, seams=sru, attrs=dict(lu=luru, lv=lvru))"),
("    return V_, F_, seam_column(NPth, NA, 0)\n\n\ndef symmetrize(V_):",
 "    lu = np.repeat(t * rr, NA)\n    lv = np.tile(np.arange(NA) / NA, NPth)\n    return V_, F_, seam_column(NPth, NA, 0), lu, lv\n\n\ndef symmetrize(V_):"),
("    Vsc, Fsc, ssc = build_scarf_loop(zf, zb, rr, tr, sd)\n    add_part(\"scarf\", Vsc, Fsc, SCARF, seams=ssc)",
 "    Vsc, Fsc, ssc, lusc, lvsc = build_scarf_loop(zf, zb, rr, tr, sd)\n    add_part(\"scarf\", Vsc, Fsc, SCARF, seams=ssc, attrs=dict(lu=lusc, lv=lvsc))"),
]
for a, b in R:
    assert a in s, a[:70]
    s = s.replace(a, b)
open(p, "w").write(s)
print("ok")
