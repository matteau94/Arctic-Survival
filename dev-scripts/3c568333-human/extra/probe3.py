import bpy, numpy as np
arm=bpy.data.objects["HumanRig"]; me=bpy.data.objects["Human"]
print(me.parent, me.matrix_world, [ (m.type, m.object) for m in me.modifiers])
print(arm.animation_data.action)
for p in arm.pose.bones: p.matrix_basis.identity()
bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get(); ev=me.evaluated_get(dg); m=ev.to_mesh()
co=np.array([v.co[:] for v in m.vertices]); print("rest eval", co.min(0), co.max(0))
co2=np.array([v.co[:] for v in me.data.vertices]); print("orig", co2.min(0), co2.max(0), np.abs(co-co2).max())
