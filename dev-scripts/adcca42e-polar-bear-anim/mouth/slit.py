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
dg = bpy.context.evaluated_depsgraph_get()
ev = me.evaluated_get(dg); m = ev.to_mesh()
bvh = BVHTree.FromPolygons([v.co.copy() for v in m.vertices], [p.vertices[:] for p in m.polygons])
# side rays (toward -x) and front rays (toward +y) across a grid; report where they go deep
print("side (ray from +x): y -> z-range where the ray penetrates deep (slit)")
for y10 in range(-78, -66, 1):
    y = y10 / 10; deep = []; surf = []
    for z100 in range(620, 720, 2):
        z = z100 / 100
        hit = bvh.ray_cast(V((3, y, z)), V((-1, 0, 0)))
        if hit[0] is None: continue
        surf.append((z, hit[0].x))
    if not surf: continue
    xs = [s[1] for s in surf]; xmax = max(xs)
    deep = [z for z, x in surf if x < xmax - 0.12]
    top = [(z, round(x, 2)) for z, x in surf][::5]
    print(f"y{y:5.1f} skin x max {xmax:.2f}  deep z {min(deep) if deep else '-'}..{max(deep) if deep else '-'}")
ev.to_mesh_clear()
