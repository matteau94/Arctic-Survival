import bpy, os, math, sys
from mathutils import Vector
OUT=os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else ""
OUT=r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\b2f5e96f-c9dd-4470-a7b5-3345ee089a18\scratchpad"
tag=sys.argv[sys.argv.index("--")+1]
sc=bpy.context.scene
cam=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera=cam
w=bpy.data.worlds.new("w"); sc.world=w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[0].default_value=(0.6,0.65,0.7,1)
sun=bpy.data.objects.new("sun",bpy.data.lights.new("sun",'SUN')); sun.data.energy=3; sun.rotation_euler=(0.8,0.2,2.6); sc.collection.objects.link(sun)
sc.render.engine='BLENDER_EEVEE'; sc.render.resolution_x=sc.render.resolution_y=600
shots={"backseam":((0.0,0.75,0.75),(0,0.1,0.6)),"feet":((0.25,-0.5,0.12),(0,-0.05,0.05)),"shoulder":((0.45,0.25,0.75),(0.1,0.0,0.62)),"crown":((0.15,-0.25,1.2),(0,-0.05,0.9))}
for n,(loc,tgt) in shots.items():
    cam.location=Vector(loc); cam.rotation_euler=(Vector(tgt)-cam.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=os.path.join(OUT,f"{tag}_{n}.png"); bpy.ops.render.render(write_still=True)
