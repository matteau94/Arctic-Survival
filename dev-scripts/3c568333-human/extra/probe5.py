import bpy, numpy as np
arm=bpy.data.objects["HumanRig"]; me=bpy.data.objects["Human"]
act=bpy.data.actions["Human_Gather"]; arm.animation_data.action=act
bpy.context.scene.frame_set(0)
for p in arm.pose.bones:
    m=p.matrix; b=p.bone.matrix_local
    sc=m.to_scale()
    if max(abs(x-1) for x in sc)>1e-3: print("scale",p.name,sc[:])
    if p.name in ("thigh.L","shin.L","spine_02","hood_01"): print(p.name, p.matrix_basis.to_scale()[:], p.bone.inherit_scale, p.scale[:])
dg=bpy.context.evaluated_depsgraph_get(); ev=me.evaluated_get(dg); m=ev.to_mesh()
co=np.array([v.co[:] for v in m.vertices]); print("eval", co.min(0), co.max(0))
