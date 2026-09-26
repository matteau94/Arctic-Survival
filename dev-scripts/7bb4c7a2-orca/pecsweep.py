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
for fl, sw, ad, bend, swg in [(0,0,0,0,20),(0,0,0,0,-20),(0,0,0,0,35),(0,0,0,0,-35),(5,0,0,0,35),(-5,0,0,0,35),(0,10,0,0,30),(5,0,-5,0,40)]:
    S = State(); S.pec_flare, S.pec_sweep, S.pec_adduct, S.pec_bend, S.pec_swing = rad(fl), rad(sw), rad(ad), rad(bend), rad(swg)
    apply(S); bpy.context.view_layer.update()
    co, tri = ck["eval_co"]()
    ins = ck["inside_set"](co, tri)
    lp = np.linalg.norm(co[e[:, 0]] - co[e[:, 1]], axis=1)
    st = np.abs(lp[ok] / lr[ok] - 1)
    # min distance of pectoral tip region to body
    print(f"PEC flare {fl} sweep {sw} adduct {ad} bend {bend} swing {swg}: new inside {len(ins['pec'] - rin['pec'])}  max strain {st.max():.2f}")
    idx = np.array(sorted(ins['pec'] - rin['pec']), int)
    if len(idx):
        import mathutils
        b = arm.data.bones["pectoral_01.L"]
        sh = np.array(b.head_local); ax = np.array((b.tail_local - b.head_local).normalized())
        u = (rco[idx] - sh) @ ax
        print("    along-axis of inside verts (m):", np.round(np.percentile(u, [0, 50, 90, 100]), 2), " tip pos", np.round(co[pec][np.argmax((rco[pec]-sh)@ax)], 2))
    else:
        print("    tip pos", np.round(co[pec][np.argmax((rco[pec]-np.array(arm.data.bones['pectoral_01.L'].head_local))@np.array((arm.data.bones['pectoral_01.L'].tail_local-arm.data.bones['pectoral_01.L'].head_local).normalized()))], 2))
