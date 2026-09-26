import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\Fish.glb")
for o in bpy.data.objects:
    print("OBJ", o.name, o.type, tuple(round(x,3) for x in o.location), tuple(round(x,3) for x in o.rotation_euler), tuple(round(x,3) for x in o.scale), "parent", o.parent.name if o.parent else None)
    if o.type=='MESH':
        me=o.data
        print("  verts", len(me.vertices), "faces", len(me.polygons), "dims", tuple(round(x,3) for x in o.dimensions))
        print("  vgroups", [g.name for g in o.vertex_groups][:50])
        print("  shapekeys", [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else None)
        print("  mods", [m.type for m in o.modifiers], "mats", [m.name for m in me.materials])
        xs=[v.co for v in me.vertices]
        import mathutils
        mn=[min(c[i] for c in xs) for i in range(3)]; mx=[max(c[i] for c in xs) for i in range(3)]
        print("  bbox local", mn, mx)
    if o.type=='ARMATURE':
        for b in o.data.bones: print("  BONE", b.name, b.parent.name if b.parent else None, tuple(round(x,3) for x in b.head_local), tuple(round(x,3) for x in b.tail_local))
print("ACTIONS", [a.name for a in bpy.data.actions])
print("IMAGES", [(i.name, i.size[:]) for i in bpy.data.images])
