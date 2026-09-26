import bpy, os, math, sys
from mathutils import Vector
D=r"C:\Users\leosp\Documents\Blender\Artic-Survival"
OUT=r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\b2f5e96f-c9dd-4470-a7b5-3345ee089a18\scratchpad"
tag=sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_factory_settings(use_empty=True)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
bpy.ops.import_scene.gltf(filepath=os.path.join(D,"ArcticFox_Animated.glb"))
fox=[o for o in bpy.data.objects if o.type in('MESH','ARMATURE') and o.name!='Icosphere']
for o in fox:
    if o.parent is None: o.location.x=-0.75
bpy.ops.import_scene.gltf(filepath=os.path.join(D,"Penguin_Animated.glb"))
for o in list(bpy.data.objects):
    if o.name.startswith("Icosphere"): bpy.data.objects.remove(o)
for o in bpy.data.objects:
    if o.type=='ARMATURE' and o.animation_data: o.animation_data.action=None
    if o.type=='ARMATURE':
        for p in o.pose.bones: p.matrix_basis.identity()
peng=[o for o in bpy.data.objects if o.name.startswith("Penguin")]
for o in peng:
    if o.parent is None: o.location.x=0.45
sc=bpy.context.scene
cam=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera=cam
w=bpy.data.worlds.new("w"); sc.world=w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[0].default_value=(0.55,0.62,0.7,1)
sun=bpy.data.objects.new("sun",bpy.data.lights.new("sun",'SUN')); sun.data.energy=3.5; sun.rotation_euler=(0.8,0.2,-0.6); sc.collection.objects.link(sun)
bpy.ops.mesh.primitive_plane_add(size=10)
sc.render.engine='BLENDER_EEVEE'; sc.eevee.taa_render_samples=16
shots={"wide":((0,-3.2,0.9),(-0.1,0,0.42),1400,700),
       "foxhead":((-0.75+0.35,-0.9,0.5),(-0.75,-0.35,0.33),700,700),
       "penghead":((0.45+0.25,-0.55,0.95),(0.45,-0.05,0.82),700,700),
       "foxbody":((-0.75+0.9,-0.6,0.45),(-0.75,0,0.25),700,700),
       "pengbody":((0.45+0.7,-0.8,0.6),(0.45,0,0.45),700,700)}
for n,(loc,tgt,rx,ry) in shots.items():
    cam.location=Vector(loc); cam.rotation_euler=(Vector(tgt)-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.lens=50 if n=="wide" else 60
    sc.render.resolution_x=rx; sc.render.resolution_y=ry
    sc.render.filepath=os.path.join(OUT,f"cmp{tag}_{n}.png"); bpy.ops.render.render(write_still=True)
