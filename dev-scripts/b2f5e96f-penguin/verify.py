import bpy, os, math, sys
from mathutils import Vector
import numpy as np
OUT=r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\b2f5e96f-c9dd-4470-a7b5-3345ee089a18\scratchpad"
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NF = int(args[0]) if args else 4           # frames per row
only = args[1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\Penguin_Animated.glb")
sc=bpy.context.scene
arm=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]
mesh=[o for o in bpy.data.objects if o.type=='MESH'][0]
print("objects",[o.name for o in bpy.data.objects], "verts",len(mesh.data.vertices))
for a in bpy.data.actions: print("action",a.name,tuple(a.frame_range))
cam=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'
w=bpy.data.worlds.new("w"); sc.world=w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[0].default_value=(0.6,0.65,0.7,1)
sun=bpy.data.objects.new("sun",bpy.data.lights.new("sun",'SUN')); sun.data.energy=3; sun.rotation_euler=(0.8,0.2,0.6); sc.collection.objects.link(sun)
bpy.ops.mesh.primitive_plane_add(size=4)
RES=300
sc.render.engine='BLENDER_EEVEE'; sc.render.resolution_x=RES; sc.render.resolution_y=RES
sc.eevee.taa_render_samples=4
VIEWS={"side":((3,0,0.45),None,1.3),"front34":((1.6,-2.6,1.3),(0,0,0.4),1.3),
       "head":((1.2,-1.2,1.05),(0,-0.12,0.85),0.45),
       "top":((0.6,-1.2,2.6),(-0.25,0,0.1),1.5)}
for act in bpy.data.actions:
    if only and act.name not in only: continue
    arm.animation_data.action=act
    f0,f1=act.frame_range
    views=["side","front34"] + (["head"] if act.name in ("Penguin_Call","Penguin_Idle") else []) + (["top"] if act.name=="Penguin_Death" else [])
    tiles=[]
    for view in views:
        loc,tgt,orth=VIEWS[view]; cam.data.ortho_scale=orth
        cam.location=Vector(loc)
        if tgt is None: cam.rotation_euler=(math.pi/2,0,math.pi/2)
        else: cam.rotation_euler=(Vector(tgt)-cam.location).to_track_quat('-Z','Y').to_euler()
        row=[]
        for k in range(NF):
            f=round(f0+(f1-f0)*k/NF) if act.use_cyclic else round(f0+(f1-f0)*k/(NF-1))
            if view=="head" and act.name=="Penguin_Peck": # follow the head
                pass
            sc.frame_set(int(f))
            p=os.path.join(OUT,"_tile.png"); sc.render.filepath=p
            bpy.ops.render.render(write_still=True)
            img=bpy.data.images.load(p); a=np.array(img.pixels[:]).reshape(RES,RES,4); bpy.data.images.remove(img)
            row.append(a)
        tiles.append(np.concatenate(row,1))
    sheet=np.concatenate(tiles[::-1],0)
    im=bpy.data.images.new("sheet",sheet.shape[1],sheet.shape[0]); im.pixels.foreach_set(sheet.astype(np.float32).ravel())
    im.filepath_raw=os.path.join(OUT,f"sheet_{act.name}.png"); im.file_format='PNG'; im.save(); bpy.data.images.remove(im)
    print("sheet",act.name)
