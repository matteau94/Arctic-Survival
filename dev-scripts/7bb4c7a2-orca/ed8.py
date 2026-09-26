p = r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_build.py"
t = open(p, encoding="utf8").read()
def rep(a, b):
    global t
    assert t.count(a) == 1, ("NOT FOUND/UNIQUE", a[:90])
    t = t.replace(a, b)
i = t.index("    # almond-shaped lid rim (a flattened torus)")
j = t.index("    eyes.append(lid)\n", i)
t = t[:i] + '''    # eyelids: an almond-shaped skirt draped over the skin (each profile point is ray-cast onto the
    # sculpted head) - its outer edge tucks tangentially under the skin, a soft ridge forms the lid
    # margin and its inner edge rolls down into the eyeball
    t1 = V((0, 1, 0)); t1 = (t1 - t1.dot(nrm) * nrm).normalized()
    t2 = nrm.cross(t1).normalized()
    a_, b_ = EYE_R * 1.22, EYE_R * 0.86                         # lid margin (ridge) ellipse
    W, Hh = 0.024, 0.0075
    PROF = [(1.00, -0.0025), (0.70, 0.18), (0.42, 0.55), (0.18, 0.88), (0.0, 1.0), (-0.16, 0.82),
            (-0.30, 0.45), (-0.40, -0.1), (-0.46, -0.8)]
    NT = 32
    lv, lf = [], []
    for i_ in range(NT):
        th = 2 * math.pi * i_ / NT
        ca, sa = math.cos(th), math.sin(th)
        corner = 1 + 0.10 * ca * ca                               # slightly pointed canthi
        e = t1 * (a_ * ca * corner) + t2 * (b_ * sa)
        radial = (t1 * (b_ * ca) + t2 * (a_ * sa)).normalized()
        heavy = 1.0 + 0.45 * max(0.0, sa)                         # heavier upper lid
        for (rq, hq) in PROF:
            q = hit + e + radial * (W * rq)
            hc, _ = surface(q + nrm * 0.08, -nrm)
            base_ = hc if hc is not None else q
            lv.append(base_ + nrm * (Hh * heavy * hq))
    npf = len(PROF)
    for i_ in range(NT):
        i2 = (i_ + 1) % NT
        for k_ in range(npf - 1):
            lf.append((i_ * npf + k_, i2 * npf + k_, i2 * npf + k_ + 1, i_ * npf + k_ + 1))
    lme = bpy.data.meshes.new("Lid"); lme.from_pydata([tuple(v_) for v_ in lv], [], lf)
    bml = bmesh.new(); bml.from_mesh(lme)
    bmesh.ops.recalc_face_normals(bml, faces=bml.faces)
    # outward = along the eye normal
    if sum((f.normal.dot(nrm)) for f in bml.faces) < 0:
        bmesh.ops.reverse_faces(bml, faces=bml.faces)
    bml.to_mesh(lme); bml.free()
    lid = bpy.data.objects.new("Lid", lme); scene.collection.objects.link(lid)
    for nm_, val in (("part", float(BODY)), ("jaw", 0.0)):
        att = lme.attributes.new(nm_, 'FLOAT', 'POINT')
        att.data.foreach_set("value", [val] * len(lme.vertices))
    subdivide(lid, 1)
''' + t[j:]
rep("""feather = smoothstep(-0.004, 0.020, ds + 0.25 * jit)""", """feather = smoothstep(-0.006, 0.040, ds + 0.4 * jit)""")
open(p, "w", encoding="utf8").write(t)
print("edited ed8")
