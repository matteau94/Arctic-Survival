import bpy, sys, math
from mathutils import Vector as V
argv = sys.argv[sys.argv.index("--")+1:]
src, out, mname = argv
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
sc = bpy.context.scene
for o in list(sc.objects):
    if o.name.startswith("Icosphere"): bpy.data.objects.remove(o)
m = bpy.data.objects[mname]
me = m.data
print("VERTS", len(me.vertices), "POLYS", len(me.polygons), "UVs", len(me.uv_layers), "VGROUPS", len(m.vertex_groups))
mat = me.materials[0]
for n in mat.node_tree.nodes: print("NODE", n.bl_idname, getattr(n,'image',None) and n.image.name)
dg = bpy.context.evaluated_depsgraph_get(); ev = m.evaluated_get(dg); em = ev.to_mesh()
pts = [ev.matrix_world @ v.co for v in em.vertices]
mn = V([min(p[i] for p in pts) for i in range(3)]); mx = V([max(p[i] for p in pts) for i in range(3)])
print("BOUNDS", mn[:], mx[:])
ctr=(mn+mx)/2; size=max(mx-mn)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[0].default_value=(0.55,0.62,0.68,1); w.node_tree.nodes["Background"].inputs[1].default_value=0.8
sun = bpy.data.objects.new("s", bpy.data.lights.new("s","SUN")); sc.collection.objects.link(sun); sun.rotation_euler=(0.8,0.2,-0.6); sun.data.energy=3.5
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'
sc.render.engine='BLENDER_EEVEE'; sc.render.resolution_x=1000; sc.render.resolution_y=700
for tag, d, sc_ in (("side", V((1,0,0)), 1.1), ("q", V((0.9,-1,0.45)), 1.1), ("head", V((0.8,-1,0.3)), 0.35)):
    d=d.normalized(); cam.data.ortho_scale=size*sc_
    tgt = ctr if tag!="head" else V((ctr.x, mn.y+0.12*(mx.y-mn.y), ctr.z+0.2*(mx.z-mn.z)))
    cam.location = tgt + d*size*4; cam.rotation_euler=(-d).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath = out+"_"+tag+".png"; bpy.ops.render.render(write_still=True)
