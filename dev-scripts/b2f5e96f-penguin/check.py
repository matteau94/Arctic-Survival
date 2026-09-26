"""Numeric sanity check of Penguin_Animated.blend: ground penetration, loop pops, foot slide."""
import bpy, numpy as np, sys
arm = bpy.data.objects["PenguinRig"]; mesh = bpy.data.objects["Penguin"]
only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
me = mesh.data
n = len(me.vertices)
gi = {g.index: g.name for g in mesh.vertex_groups}
dom = []
for v in me.vertices:
    best = max(v.groups, key=lambda g: g.weight, default=None)
    dom.append(gi[best.group] if best else "")
dom = np.array(dom)
footm = np.array([d.startswith(("foot", "shin")) for d in dom])
sc = bpy.context.scene
ad = arm.animation_data
for tr in ad.nla_tracks: tr.mute = True
for act in bpy.data.actions:
    if not act.name.startswith("Penguin_") or (only and act.name not in only):
        continue
    ad.action = act
    f0, f1 = map(int, act.frame_range)
    bodymin, footmin, worst_body_f = 9, 9, -1
    toes = {"L": [], "R": []}
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = mesh.evaluated_get(dg); m = ev.to_mesh()
        co = np.empty(n * 3, np.float32); m.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        ev.to_mesh_clear()
        mw = np.array(mesh.matrix_world)
        z = co @ mw[2, :3] + mw[2, 3]
        b = z[~footm].min(); ft = z[footm].min()
        if b < bodymin: worst_grp = dom[~footm][z[~footm].argmin()]
        if b < bodymin: bodymin, worst_body_f = b, f
        footmin = min(footmin, ft)
        for sd in "LR":
            toes[sd].append((arm.matrix_world @ arm.pose.bones[f"foot.{sd}"].tail).copy())
    # loop pop
    sc.frame_set(f0); m0 = [p.matrix.copy() for p in arm.pose.bones]
    sc.frame_set(f1); m1 = [p.matrix.copy() for p in arm.pose.bones]
    pop = max(max(abs(a[i][j] - c[i][j]) for i in range(4) for j in range(4)) for a, c in zip(m0, m1))
    # toe planted sideways / vertical wobble when z < 13 mm
    slide = 0.0; vy = []
    for sd in "LR":
        T = toes[sd]
        for a, c in zip(T, T[1:]):
            if a.z < 0.0135 and c.z < 0.0135:
                slide = max(slide, abs(c.x - a.x)); vy.append(c.y - a.y)
    vy_s = f"toe dy/frame {min(vy)*1000:.2f}..{max(vy)*1000:.2f} mm" if vy else ""
    print(f"CHECK {act.name:15s} f{f0}-{f1} bodyMinZ {bodymin*1000:6.1f}mm@{worst_body_f}({worst_grp}) footMinZ {footmin*1000:6.1f}mm "
          f"loopPop {pop:.4f} toeSideSlide {slide*1000:.2f}mm {vy_s}")
