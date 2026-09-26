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
print("side seam (ray from +x): y, seam z (jaw->skull), gap z-range where ray goes deep")
for y10 in range(-78, -67, 1):
    y = y10 / 10; prof = []
    for z100 in range(600, 740, 1):
        z = z100 / 100
        loc, nrm, idx, dist = bvh.ray_cast(V((3, y, z)), V((-1, 0, 0)))
        if loc is None: continue
        prof.append((z, loc.x, jw_at(idx)))
    if not prof: continue
    # outer skin: first transition from jaw-weighted (low z) to skull-weighted (high z)
    seam = next((z for z, x, w in prof if w < 0.5 and z > prof[0][0]), None)
    lower_top = max((z for z, x, w in prof if w >= 0.5), default=None)
    upper_bot = min((z for z, x, w in prof if w < 0.5), default=None)
    xs = {round(z, 2): x for z, x, w in prof}
    print(f"y{y:5.1f} lower-lip top z {lower_top}  upper-lip bottom z {upper_bot}  x@upper {xs.get(round(upper_bot,2)) if upper_bot else '-'} x@lower {xs.get(round(lower_top,2)) if lower_top else '-'}")
ev.to_mesh_clear()
