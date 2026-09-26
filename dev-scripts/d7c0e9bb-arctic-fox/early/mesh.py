import bpy, bmesh, math
from mathutils import Vector, Matrix
col = bpy.data.collections["ArcticFox"]
for n in ("Fox","FoxEar.L","FoxEar.R"):
    o=bpy.data.objects.get(n)
    if o: bpy.data.objects.remove(o, do_unlink=True)
meta = bpy.data.objects["FoxMeta"]
dg = bpy.context.evaluated_depsgraph_get()
me = bpy.data.meshes.new_from_object(meta.evaluated_get(dg))
body = bpy.data.objects.new("Fox", me); col.objects.link(body)
meta.hide_viewport = True; meta.hide_render = True
# ears: tapered, flattened, slightly cupped cone
ears=[]
for sx,nm in ((1,"FoxEar.L"),(-1,"FoxEar.R")):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.042, radius2=0.012, depth=0.07)
    for v in bm.verts:
        h = (v.co.z+0.035)/0.07          # 0 base .. 1 tip
        v.co.y *= 0.5
        # round the tip: bulge mid section
        k = 1.0 + 0.35*math.sin(math.pi*h)
        v.co.x *= k
        if v.co.y < 0: v.co.y *= 0.5          # cup: front face flatter
    em = bpy.data.meshes.new(nm); bm.to_mesh(em); bm.free()
    eo = bpy.data.objects.new(nm, em); col.objects.link(eo)
    eo.location = (sx*0.047, -0.318, 0.495)
    eo.rotation_euler = (math.radians(-12), math.radians(sx*22), math.radians(sx*-12))
    ears.append(eo)
bpy.ops.object.select_all(action='DESELECT')
for o in [body]+ears: o.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
body.data.remesh_voxel_size = 0.0032
body.data.remesh_voxel_adaptivity = 0
bpy.ops.object.voxel_remesh()
# smooth pass
m = body.modifiers.new("Smooth", 'CORRECTIVE_SMOOTH'); m.iterations=14; m.use_only_smooth=True if hasattr(m,'use_only_smooth') else None
m.smooth_type='LENGTH_WEIGHTED'; m.rest_source='ORCO'
bpy.ops.object.modifier_apply(modifier=m.name)
bpy.ops.object.shade_smooth()
print(len(body.data.vertices), len(body.data.polygons))
# decimate for game use
d = body.modifiers.new("Decimate",'DECIMATE'); d.ratio = 0.12
bpy.ops.object.modifier_apply(modifier=d.name)
print("tris", sum(len(p.vertices)-2 for p in body.data.polygons))
# eyes + nose
for n in ("FoxEye.L","FoxEye.R","FoxNose"):
    o=bpy.data.objects.get(n)
    if o: bpy.data.objects.remove(o, do_unlink=True)
def surf(p):
    ok, loc, nor, idx = body.closest_point_on_mesh(Vector(p))
    return loc, nor
def sphere(name, center, r, scale=(1,1,1)):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=r)
    m = bpy.data.meshes.new(name); bm.to_mesh(m); bm.free()
    for p in m.polygons: p.use_smooth=True
    o = bpy.data.objects.new(name, m); col.objects.link(o); o.location=center; o.scale=scale
    o.parent = body
    return o
for sx,nm in ((1,"FoxEye.L"),(-1,"FoxEye.R")):
    loc,nor = surf((sx*0.045,-0.38,0.44))
    sphere(nm, loc - nor*0.004, 0.0105)
loc,nor = surf((0,-0.475,0.407))
sphere("FoxNose", loc - nor*0.004, 0.012, (1.25,0.9,0.85))
