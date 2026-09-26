import bpy, runpy, sys, math
import numpy as np
sys.path.insert(0, r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\7bb4c7a2-2c8e-4793-b5ee-2fc544b80253\scratchpad")
g = runpy.run_path(r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_anim_swim.py")
ck = {}
src = open(r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\7bb4c7a2-2c8e-4793-b5ee-2fc544b80253\scratchpad\check.py").read()
src = src.split("if \"--nocheck\"")[0]
exec(src, ck)
arm = g["arm"]; arm.animation_data.action = None
State, apply, rad = g["State"], g["apply"], g["rad"]
for p in arm.pose.bones: p.matrix_basis.identity()
bpy.context.view_layer.update()
rco, rtri = ck["eval_co"]()
rin = ck["inside_set"](rco, rtri)
e = rtri[:, [0, 1]]; lr = np.linalg.norm(rco[e[:, 0]] - rco[e[:, 1]], axis=1); ok = lr > 1e-4
pec = np.abs(ck["part"] - 2) < 0.01
from mathutils import Vector as V
from mathutils.bvhtree import BVHTree
b = arm.data.bones["pectoral_01.L"]
sh = np.array(b.head_local); ax = np.array((b.tail_local - b.head_local).normalized())
along = (rco - sh) @ ax
pl = np.where(pec & (rco[:, 0] > 0))[0]
outer = pl[along[pl] > 0.25]
tipi = pl[np.argsort(along[pl])[-40:]]
print("rest tip", np.round(rco[tipi].mean(0), 2))
for ad in (0,):
    for sw in (-40, -30, -20, -10, 10, 20, 30, 40):
        for fl in (0, 8):
            S = State(); S.pec_flare, S.pec_swing = rad(fl), rad(sw)
            apply(S); bpy.context.view_layer.update()
            co, tri = ck["eval_co"]()
            body = ck["part"] < 0.5
            tb = tri[body[tri].all(1)]
            bvh = BVHTree.FromPolygons([V(c) for c in co], tb.tolist())
            sd = []
            for i in outer:
                loc, n, _, d = bvh.find_nearest(V(co[i]))
                sd.append(d if (V(co[i]) - loc).dot(n) >= 0 else -d)
            sd = np.array(sd)
            print(f"G2 swing {sw} flare {fl}: outer-part min signed dist {sd.min():.3f}  n<-0.01 {int((sd < -0.01).sum())}  tip {np.round(co[tipi].mean(0), 2)}")
