import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Polar Bear Running.glb")
for a in bpy.data.actions: print("ACTION", a.name, tuple(a.frame_range))
for o in bpy.data.objects:
    if o.type=='MESH': print("MESH dims", tuple(round(v,3) for v in o.dimensions), "groups", len(o.vertex_groups))
    if o.type=='ARMATURE': print("BONES", len(o.data.bones))
