import bpy, os, math, sys
from mathutils import Vector
OUT=r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\b2f5e96f-c9dd-4470-a7b5-3345ee089a18\scratchpad"
argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
tag=argv[0] if argv else "p"
frame=int(argv[1]) if len(argv)>1 else 0
sc=bpy.context.scene
sc.frame_set(frame)
c=Vector((0,0,0.5)); r=0.55
if len(argv)>2: c=Vector(eval(argv[2]))
cam=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera=cam
w=bpy.data.worlds.new("w"); sc.world=w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[0].default_value=(0.6,0.65,0.7,1)
sun=bpy.data.objects.new("sun",bpy.data.lights.new("sun",'SUN')); sun.data.energy=3; sun.rotation_euler=(0.8,0.2,0.6); sc.collection.objects.link(sun)
sc.render.engine='BLENDER_EEVEE'
sc.render.resolution_x=700; sc.render.resolution_y=700
views=[("front34",-60,0.15),("side",0,0.05),("back34",140,0.3),("face",-80,0.1)]
if len(argv)>3: views=[v for v in views if v[0] in argv[3].split(",")]
for nm,az,el in views:
    a=math.radians(az); d=r*3.4 if nm!="face" else 0.55
    cc=c if nm!="face" else Vector((0,-0.08,0.85))
    cam.location=cc+Vector((math.cos(a)*math.cos(el)*d, math.sin(a)*math.cos(el)*d, math.sin(el)*d))
    cam.rotation_euler=(cc-cam.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=os.path.join(OUT,f"{tag}_{nm}.png")
    bpy.ops.render.render(write_still=True)
