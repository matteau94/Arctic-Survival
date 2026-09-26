import bpy, os, math
from mathutils import Vector
D=r"C:\Users\leosp\Documents\Blender\Artic-Survival"
OUT=r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\b2f5e96f-c9dd-4470-a7b5-3345ee089a18\scratchpad"
def setup_render(name, meshes):
    sc=bpy.context.scene
    sc.frame_set(0)
    dg=bpy.context.evaluated_depsgraph_get()
    pts=[]
    for o in meshes:
        e=o.evaluated_get(dg)
        pts+= [e.matrix_world@v.co for v in e.data.vertices]
    mn=Vector([min(p[i] for p in pts) for i in range(3)]);mx=Vector([max(p[i] for p in pts) for i in range(3)])
    c=(mn+mx)/2; r=(mx-mn).length/2
    print(name,"world bbox",tuple(mn),tuple(mx))
    cam=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera=cam
    cam.data.lens=50
    w=bpy.data.worlds.new("w"); sc.world=w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[0].default_value=(0.6,0.65,0.7,1)
    sun=bpy.data.objects.new("sun",bpy.data.lights.new("sun",'SUN')); sun.data.energy=3; sun.rotation_euler=(0.8,0.2,0.6); sc.collection.objects.link(sun)
    sc.render.engine='BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
    sc.render.resolution_x=800; sc.render.resolution_y=600
    for i,az in enumerate([30,150, 270]):
        a=math.radians(az)
        d=r*3.2
        cam.location=c+Vector((math.cos(a)*d, math.sin(a)*d, r*0.8))
        cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler()
        sc.render.filepath=os.path.join(OUT,f"ref_{name}_{i}.png")
        bpy.ops.render.render(write_still=True)
for f in ["Polar Bear Walking.glb","ArcticFox_Animated.glb","Fish Swim Calm.glb"]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(D,f))
    if "Icosphere" in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects["Icosphere"])
    ms=[o for o in bpy.data.objects if o.type=='MESH']
    setup_render(f.split()[0].split("_")[0], ms)
