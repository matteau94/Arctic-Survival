import bpy, math
from mathutils import Quaternion, Vector as V
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\Documents\Polar Bear Running.blend")
arm = bpy.data.objects["PolarBearRig"]; arm.animation_data.action = None
me = bpy.data.objects["PolarBear"]; pb = arm.pose.bones
for p in pb: p.matrix_basis.identity()
j = pb["jaw"]; j.rotation_mode = 'QUATERNION'
r = j.bone.matrix_local.to_quaternion(); j.rotation_quaternion = r.inverted() @ Quaternion((1, 0, 0), math.radians(-30)) @ r
bpy.context.view_layer.update()
ev = me.evaluated_get(bpy.context.evaluated_depsgraph_get()); m = ev.to_mesh()
co = [v.co.copy() for v in m.vertices]; polys = [p.vertices[:] for p in m.polygons]
bvh = BVHTree.FromPolygons(co, polys)
jaw_i = me.vertex_groups["jaw"].index
JW = [next((g.weight for g in v.groups if g.group == jaw_i), 0.0) for v in me.data.vertices]
def jw_at(hit_idx):
    vs = polys[hit_idx]; return sum(JW[i] for i in vs) / len(vs)
print("front seam (ray from -y toward +y): x, lower-lip top z, upper-lip bottom z, y of each")
for x10 in range(-6, 7, 1):
    x = x10 / 10; prof = []
    for z100 in range(600, 740, 1):
        z = z100 / 100
        loc, nrm, idx, dist = bvh.ray_cast(V((x, -12, z)), V((0, 1, 0)))
        if loc is None: continue
        prof.append((z, loc.y, jw_at(idx)))
    lo = [(z, yy) for z, yy, w in prof if w >= 0.5]; up = [(z, yy) for z, yy, w in prof if w < 0.5]
    lt = max(lo) if lo else None; ub = min(up) if up else None
    print(f"x{x:5.2f} lower top {lt[0] if lt else '-'} (y {round(lt[1],2) if lt else '-'})  upper bottom {ub[0] if ub else '-'} (y {round(ub[1],2) if ub else '-'})")
ev.to_mesh_clear()
