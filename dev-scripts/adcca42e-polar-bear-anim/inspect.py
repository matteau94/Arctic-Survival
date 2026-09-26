import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Polar Bear.glb")
for o in bpy.data.objects:
    print("OBJ", o.name, o.type, tuple(round(v,3) for v in o.dimensions), o.parent.name if o.parent else None, [m.type for m in o.modifiers])
    if o.type=='MESH':
        me=o.data; print("  verts",len(me.vertices),"faces",len(me.polygons),"vgroups",len(o.vertex_groups), "mats",[m.name for m in me.materials if m])
        import mathutils
        ws=[o.matrix_world@v.co for v in me.vertices]
        for i,a in enumerate("xyz"): print("  ",a,round(min(w[i] for w in ws),3),round(max(w[i] for w in ws),3))
    if o.type=='ARMATURE': print("  bones",[b.name for b in o.data.bones])
print("actions",[a.name for a in bpy.data.actions])
