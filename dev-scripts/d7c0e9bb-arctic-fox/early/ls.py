import bpy
print(bpy.data.filepath, bpy.data.is_dirty)
for o in bpy.data.objects:
    print(o.name, o.type, o.parent.name if o.parent else None, [c.name for c in o.users_collection], tuple(round(x,3) for x in o.dimensions), tuple(round(x,3) for x in o.location), (len(o.data.vertices) if o.type=='MESH' else ''), (len(o.data.bones) if o.type=='ARMATURE' else ''))
print("actions",[a.name for a in bpy.data.actions])
