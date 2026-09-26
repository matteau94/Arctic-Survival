import bpy, math
from mathutils import Quaternion
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\Documents\Polar Bear Running.blend")
arm = bpy.data.objects["PolarBearRig"]; me = bpy.data.objects["PolarBear"]
print("action", arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None)
arm.animation_data.action = None
pb = arm.pose.bones
for p in pb: p.matrix_basis.identity()
jaw_i = me.vertex_groups["jaw"].index
# a lower-jaw vertex near the front of the lower lip
cands = [v for v in me.data.vertices if -7.6 < v.co.y < -7.4 and abs(v.co.x) < 0.2 and v.co.z < 6.45 and any(g.group == jaw_i and g.weight > 0.9 for g in v.groups)]
v0 = max(cands, key=lambda v: v.co.z)
print("vertex", v0.index, tuple(round(c, 3) for c in v0.co))
j = pb["jaw"]; j.rotation_mode = 'QUATERNION'
for a in (0, -30):
    r = j.bone.matrix_local.to_quaternion(); j.rotation_quaternion = r.inverted() @ Quaternion((1, 0, 0), math.radians(a)) @ r
    bpy.context.view_layer.update()
    ev = me.evaluated_get(bpy.context.evaluated_depsgraph_get()); m = ev.to_mesh()
    print("jaw", a, "->", tuple(round(c, 3) for c in m.vertices[v0.index].co), "frame", bpy.context.scene.frame_current)
    ev.to_mesh_clear()
