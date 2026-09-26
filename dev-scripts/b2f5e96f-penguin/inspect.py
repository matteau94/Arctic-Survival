import bpy, sys, os
from mathutils import Vector
D=r"C:\Users\leosp\Documents\Blender\Artic-Survival"
OUT=r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\b2f5e96f-c9dd-4470-a7b5-3345ee089a18\scratchpad"
for f in ["Polar Bear Walking.glb","ArcticFox_Animated.glb","Fish Swim Calm.glb"]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(D,f))
    print("=====",f)
    for o in bpy.data.objects:
        info=""
        if o.type=='MESH':
            info=f"verts={len(o.data.vertices)} faces={len(o.data.polygons)} mats={[m.name for m in o.data.materials]} uv={len(o.data.uv_layers)}"
            ws=[o.matrix_world@Vector(c) for c in o.bound_box]
            mn=Vector([min(w[i] for w in ws) for i in range(3)]);mx=Vector([max(w[i] for w in ws) for i in range(3)])
            info+=f" bbox={tuple(round(x,3) for x in mn)}..{tuple(round(x,3) for x in mx)}"
        if o.type=='ARMATURE':
            info=f"bones={len(o.data.bones)} {[b.name for b in o.data.bones][:60]}"
        print(o.name,o.type,"parent=",o.parent.name if o.parent else None,"scale=",tuple(round(s,3) for s in o.scale),info)
    for a in bpy.data.actions: print("action",a.name,a.frame_range)
    for m in bpy.data.materials:
        if m.node_tree:
            print("mat",m.name,[ (n.type, getattr(n,'image',None) and (n.image.name, tuple(n.image.size))) for n in m.node_tree.nodes])
