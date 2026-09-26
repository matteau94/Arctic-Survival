# Per-frame paw contact analysis on the actual deformed mesh (cm units).
import bpy, re
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\Documents\Polar Bear Running.blend")
sc = bpy.context.scene
arm = bpy.data.objects["PolarBearRig"]; me = bpy.data.objects["PolarBear"]
src = open(r"C:\Users\leosp\Documents\polar_bear_run.py", encoding="utf-8").read()
SWEEP = float(re.search(r"^SWEEP = ([\d.]+)", src, re.M).group(1))
CYCLE = int(re.search(r"^CYCLE = (\d+)", src, re.M).group(1))
v_frame = SWEEP / CYCLE
names = {g.index: g.name for g in me.vertex_groups}
# sole vertices per paw: rest z < 0.35 cm and mostly weighted to that paw's manus/pes/digits
sole = {k: [] for k in ("FL", "FR", "HL", "HR")}
for v in me.data.vertices:
    if v.co.z > 0.35: continue
    acc = {}
    for g in v.groups:
        n = names[g.group]
        if "." in n:
            b, k = n.split(".")
            if b in ("manus", "pes", "digits"): acc[k] = acc.get(k, 0) + g.weight
    if acc:
        k, wsum = max(acc.items(), key=lambda kv: kv[1])
        if wsum > 0.6: sole[k].append(v.index)
print("sole verts", {k: len(v) for k, v in sole.items()})
prev = {}
rows = []
for f in range(1, CYCLE + 1):
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = me.evaluated_get(dg); m = ev.to_mesh()
    M = ev.matrix_world
    line = f"f{f:02d}"
    for k, ids in sole.items():
        pts = [(M @ m.vertices[i].co) * 100 for i in ids]
        zmin = min(p.z for p in pts)
        # contact points = sole verts within 0.12 cm of the lowest one, if the paw is down
        low = [i for i, p in zip(ids, pts) if p.z < zmin + 0.12]
        slip = ""
        if zmin < 0.15 and k in prev:
            # expected: planted verts move +v_frame in y (treadmill), 0 in z
            dys = [((M @ m.vertices[i].co) * 100).y - prev[k][i].y for i in low if i in prev[k]]
            if dys: slip = f"{sum(dys)/len(dys) - v_frame:+.2f}"
        prev[k] = {i: p for i, p in zip(ids, pts)}
        line += f" | {k} z{zmin:+.2f} {slip:>6}"
    ev.to_mesh_clear()
    rows.append(line)
print(f"expected planted dy/frame = {v_frame:.3f} cm")
print("\n".join(rows))
