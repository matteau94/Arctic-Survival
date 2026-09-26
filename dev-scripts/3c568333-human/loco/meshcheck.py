"""Real-mesh QA: deformed boot soles vs ground, and edge stretch / collapse per body region."""
import bpy, sys, math
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
CLIPS = argv or ["Human_Idle", "Human_Walk", "Human_Run", "Human_CrouchIdle", "Human_CrouchWalk"]
arm = bpy.data.objects["HumanRig"]
ob = bpy.data.objects["Human"]
me = ob.data
nv = len(me.vertices)
rest = np.empty(nv * 3)
me.vertices.foreach_get("co", rest)
rest = rest.reshape(-1, 3)
ed = np.empty(len(me.edges) * 2, dtype=np.int64)
me.edges.foreach_get("vertices", ed)
ed = ed.reshape(-1, 2)
L0 = np.linalg.norm(rest[ed[:, 0]] - rest[ed[:, 1]], axis=1)
ok = L0 > 1e-5
# dominant group per vertex -> region
gname = {g.index: g.name for g in ob.vertex_groups}
dom = []
for v in me.vertices:
    best = max(v.groups, key=lambda g: g.weight, default=None)
    dom.append(gname.get(best.group, "") if best else "")
dom = np.array(dom)
feet = np.array([d.split(".")[0] in ("foot", "toe") for d in dom])
print(f"mesh {nv} verts, rest min z {rest[:, 2].min():.4f}, boot verts {feet.sum()}")
for clip in CLIPS:
    act = bpy.data.actions[clip]
    arm.animation_data.action = act
    if act.slots:
        arm.animation_data.action_slot = act.slots[0]
    f1 = int(act.frame_range[1])
    zmin, worst_s, worst_c = 1e9, (0, ""), (9, "")
    for f in range(0, f1, 2):
        bpy.context.scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        em = ob.evaluated_get(dg).to_mesh()
        co = np.empty(len(em.vertices) * 3)
        em.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        ob.evaluated_get(dg).to_mesh_clear()
        co = (np.array(ob.matrix_world) @ np.c_[co, np.ones(len(co))].T).T[:, :3]
        z = co[feet, 2].min()
        zmin = min(zmin, z)
        L = np.linalg.norm(co[ed[:, 0]] - co[ed[:, 1]], axis=1)
        r = np.where(ok, L / np.where(ok, L0, 1), 1.0)
        i, j = int(r.argmax()), int(r.argmin())
        if r[i] > worst_s[0]:
            worst_s = (r[i], f"{dom[ed[i, 0]]}@f{f}")
        if r[j] < worst_c[0]:
            worst_c = (r[j], f"{dom[ed[j, 0]]}@f{f}")
    print(f"{clip}: boot min z {zmin * 1000:.1f} mm; max edge stretch x{worst_s[0]:.2f} ({worst_s[1]}), "
          f"max compression x{worst_c[0]:.2f} ({worst_c[1]})")
