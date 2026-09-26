p = r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_build.py"
t = open(p, encoding="utf8").read()
def rep(a, b):
    global t
    assert t.count(a) == 1, a[:80]
    t = t.replace(a, b)
rep("""~40k verts, one object 'Orca', one material 'Orca_Skin', armature 'OrcaRig'.""",
    """~41k verts, one object 'Orca', one material 'Orca_Skin', armature 'OrcaRig', 4096^2 maps.""")
rep("""     mouth     a soft interior 'plug' inside the head (seen through the open jaw) + conical teeth
               sitting between plug and skin (hidden when the jaw is closed)""",
"""     mouth     a folded lining sheet (inner lips, gums, ridged palate, tongue, dark throat fold)
               whose edges are ray-clamped inside the skin, plus 12 upper / 11 lower interlocking
               conical teeth per side (curved back / inward, smaller front and back) growing from the
               gums toward the lip line but never crossing it, so they stay hidden while the jaw is
               closed or only a few degrees open""")
rep("""   Every part carries a 'part' point attribute used when texturing and weighting.""",
"""   Every part carries a 'part' point attribute used when texturing and weighting; a 'micro' point
   attribute masks the pore bump (near zero on the smooth head).  Fin-root vertices get custom
   normals bent toward the body normal (and AO / colour are blended there) to hide the seams.
   UVs: only the x > 0 half is unwrapped (seams: head / mid / tail body pieces, both faces of every
   fin, fluke, eye, tooth), packed, and mirrored onto the x < 0 half (~1070 px/m at 4K).""")
open(p, "w", encoding="utf8").write(t)
print("ok")
