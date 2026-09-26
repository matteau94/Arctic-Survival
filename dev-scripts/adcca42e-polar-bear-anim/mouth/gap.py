import bpy, math
from mathutils import Quaternion
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\Polar Bear Walking.blend")
arm = bpy.data.objects["PolarBearRig"]; arm.animation_data.action = None
me = bpy.data.objects["PolarBear"]
for p in arm.pose.bones: p.matrix_basis.identity()
j = arm.pose.bones["jaw"]; j.rotation_mode = 'QUATERNION'
r = j.bone.matrix_local.to_quaternion(); j.rotation_quaternion = r.inverted() @ Quaternion((1, 0, 0), math.radians(-27)) @ r
bpy.context.view_layer.update()
ev = me.evaluated_get(bpy.context.evaluated_depsgraph_get()); m = ev.to_mesh()
P = [v.co.copy() for v in m.vertices]; ev.to_mesh_clear()
# outer surface only: for each (x band, y slice) the lateral-most skin; gaps along z in 5.9..7.4
for xa, xb in ((0.0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.0)):
    print(f"-- |x| {xa}-{xb}")
    for y10 in range(-80, -58, 2):
        y = y10 / 10
        zs = sorted(p.z for p in P if abs(p.y - y) < 0.1 and xa <= abs(p.x) < xb and 5.9 < p.z < 7.4)
        gaps = [(round(a, 2), round(b, 2)) for a, b in zip(zs, zs[1:]) if b - a > 0.08]
        if zs: print(f"y{y:5.1f} n{len(zs):3d} z {zs[0]:.2f}-{zs[-1]:.2f} gaps {gaps}")
