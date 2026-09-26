import bpy, sys, math
from mathutils import Vector as V
argv = sys.argv[sys.argv.index("--")+1:]
src, prefix = argv[0], argv[1]
focus = [float(x) for x in argv[2].split(",")] if len(argv)>2 else None
scale = float(argv[3]) if len(argv)>3 else 7.0
if src.endswith(".glb"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
else:
    bpy.ops.wm.open_mainfile(filepath=src)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x = 900; sc.render.resolution_y = 600
w = bpy.data.worlds.new("w") if not sc.world else sc.world
sc.world = w; w.use_nodes=True
w.node_tree.nodes["Background"].inputs[0].default_value=(0.6,0.6,0.65,1); w.node_tree.nodes["Background"].inputs[1].default_value=1.0
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun","SUN")); sc.collection.objects.link(sun); sun.rotation_euler=(0.6,0.3,0.5); sun.data.energy=3
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'; cam.data.ortho_scale=scale
c = V(focus) if focus else V((0,0.64*0.01*100,0.83))*0.01
# object is scaled by 0.01 via RootNode -> world units: y -0.023..0.036, z 0..0.0166
c = V(focus) if focus else V((0,0.0064,0.0083))
cam.data.ortho_scale = scale*0.01
cam.data.clip_start=0.0001; cam.data.clip_end=10
views = {"side":(V((1,0,0)),), "top":(V((0,0,1)),), "front":(V((0,1,0)),), "back":(V((0,-1,0)),), "otherside":(V((-1,0,0)),), "under":(V((0,0,-1)),)}
for name,(d,) in views.items():
    cam.location = c + d*1.0
    cam.rotation_euler = (-d).to_track_quat('-Z','Y' if name not in ("top","under") else 'Y').to_euler()
    if name in ("top","under"): cam.rotation_euler = (-d).to_track_quat('-Z','X').to_euler()
    sc.render.filepath = f"{prefix}_{name}.png"
    bpy.ops.render.render(write_still=True)
