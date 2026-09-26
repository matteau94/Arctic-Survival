import bpy, sys, math
from mathutils import Vector as V
argv = sys.argv[sys.argv.index("--")+1:]
src, out = argv
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
sc = bpy.context.scene
meshes = [o for o in sc.objects if o.type=='MESH']
for o in meshes: print("MESH", o.name, len(o.data.vertices), [m.name for m in o.data.materials], o.dimensions[:])
for o in sc.objects:
    if o.type=='ARMATURE': print("ARM", o.name, len(o.data.bones), [b.name for b in o.data.bones][:60])
print("ACTIONS", [(a.name, a.frame_range[:]) for a in bpy.data.actions])
print("IMAGES", [(i.name, i.size[:]) for i in bpy.data.images])
mn = V((1e9,)*3); mx = V((-1e9,)*3)
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ V(c); mn = V(map(min, mn, w)); mx = V(map(max, mx, w))
ctr = (mn+mx)/2; size = max(mx-mn)
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam)
cam.data.type='ORTHO'; cam.data.ortho_scale = size*1.2
d = V((1, -1, 0.5)).normalized()
cam.location = ctr + d*size*3
cam.rotation_euler = (-d).to_track_quat('-Z','Y').to_euler(); sc.camera = cam
sun = bpy.data.objects.new("s", bpy.data.lights.new("s","SUN")); sc.collection.objects.link(sun); sun.rotation_euler=(0.7,0.2,-0.9); sun.data.energy=3.5
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[0].default_value=(0.55,0.62,0.68,1)
sc.render.engine='BLENDER_EEVEE'; sc.render.resolution_x=sc.render.resolution_y=600
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
