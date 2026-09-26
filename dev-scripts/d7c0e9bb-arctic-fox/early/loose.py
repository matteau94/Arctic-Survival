import bpy, bmesh
jaw=bpy.data.objects["FoxJaw"]
bm=bmesh.new(); bm.from_mesh(jaw.data); bm.verts.ensure_lookup_table()
seen=set(); parts=[]
for v in bm.verts:
    if v.index in seen: continue
    stack=[v]; comp=[]
    seen.add(v.index)
    while stack:
        a=stack.pop(); comp.append(a)
        for e in a.link_edges:
            b=e.other_vert(a)
            if b.index not in seen: seen.add(b.index); stack.append(b)
    c=sum((jaw.matrix_world@x.co for x in comp), __import__('mathutils').Vector())/len(comp)
    parts.append((len(comp), tuple(round(k,3) for k in c)))
print(sorted(parts, reverse=True))
