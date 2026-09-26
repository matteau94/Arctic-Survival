import bpy
for f in ["Penguin_Animated.glb","ArcticFox_Animated.glb"]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\\"+f)
    print("==",f)
    for o in bpy.data.objects:
        print(" obj",o.name,o.type,o.parent.name if o.parent else None, tuple(round(x,3) for x in o.dimensions), o.animation_data.action.name if o.animation_data and o.animation_data.action else None)
        if o.type=='ARMATURE': print("  bones",len(o.data.bones))
        if o.animation_data: print("  nla",[ (t.name,[s.action.name for s in t.strips]) for t in o.animation_data.nla_tracks])
    for a in bpy.data.actions: print(" act",a.name,tuple(a.frame_range), a.use_fake_user, len(a.layers) if hasattr(a,'layers') else '', getattr(a,'slots',None) and [s.name_display for s in a.slots])
    print(" mats",[m.name for m in bpy.data.materials]," imgs",[(i.name,tuple(i.size)) for i in bpy.data.images])
