import bpy, sys
from mathutils import Vector
arm = bpy.data.objects["PolarBearRig"]; arm.animation_data.action = None
for p in arm.pose.bones: p.matrix_basis.identity()
bpy.context.view_layer.update()
ob = bpy.data.objects["PolarBear"]
dg = bpy.context.evaluated_depsgraph_get()
c = arm.matrix_world @ Vector((0, -7.3, 6.75)); d = Vector((0.8, -0.45, 0.3)).normalized()
loc = c + d * 0.3
q = (c - loc).to_track_quat('-Z', 'Y'); M = q.to_matrix()
right = M.col[0]; up = M.col[1]; fwd = -M.col[2]
S = 0.013
for px, py in [(70, 172), (90, 176), (110, 178), (130, 180), (150, 182), (170, 184), (100, 181), (100, 175)]:
    o = loc + right * ((px - 200) / 400 * S) + up * ((200 - py) / 400 * S)
    hit, p, n, fi, obj, mw = bpy.context.scene.ray_cast(dg, o, fwd)
    if hit and obj.name == "PolarBear":
        pl = obj.matrix_world.inverted() @ p
        ev = obj.evaluated_get(dg); m = ev.data
        f = m.polygons[fi]
        print("PX", px, py, "local %.3f %.3f %.3f" % tuple(pl), "n %.2f %.2f %.2f" % tuple(n), "verts", [tuple(round(c, 3) for c in m.vertices[v].co) for v in f.vertices])
    else:
        print("PX", px, py, "miss", obj and obj.name)
