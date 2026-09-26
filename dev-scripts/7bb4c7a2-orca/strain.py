import bpy, numpy as np
ck = {}
src = open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/7bb4c7a2-2c8e-4793-b5ee-2fc544b80253/scratchpad/check.py").read().split('if "--nocheck"')[0]
exec(src, ck)
arm = ck["arm"]; sc = bpy.context.scene; part = ck["part"]
arm.animation_data.action = None
for p in arm.pose.bones: p.matrix_basis.identity()
sc.frame_set(0); rco, rtri = ck["eval_co"]()
e = np.concatenate([rtri[:, [0, 1]], rtri[:, [1, 2]], rtri[:, [2, 0]]])
lr = np.linalg.norm(rco[e[:, 0]] - rco[e[:, 1]], axis=1); ok = lr > 1e-3
for an in ("Orca_Breach", "Orca_SwimFast", "Orca_TurnL"):
    arm.animation_data.action = bpy.data.actions[an]
    worst = (0, 0, 0)
    for f in range(0, int(bpy.data.actions[an].frame_range[1]) + 1, 4):
        sc.frame_set(f); co, _ = ck["eval_co"]()
        lp = np.linalg.norm(co[e[:, 0]] - co[e[:, 1]], axis=1)
        st = np.where(ok, np.abs(lp / np.maximum(lr, 1e-9) - 1), 0)
        i = int(st.argmax())
        if st[i] > worst[0]: worst = (float(st[i]), f, e[i, 0])
        p95 = np.percentile(st[ok], 99.9)
    v = worst[2]
    print("STRAIN", an, round(worst[0], 2), "frame", worst[1], "part", part[v], "rest pos", np.round(rco[v], 2), "edge len", round(float(lr[np.where((e[:,0]==v))[0][0]]),4))
