import bpy, numpy as np, bmesh
fox=bpy.data.objects["ArcticFox"]; me=fox.data
co=np.empty(len(me.vertices)*3,np.float32); me.vertices.foreach_get("co",co); co=co.reshape(-1,3)
bm=bmesh.new(); bm.from_mesh(me)
seen=set(); parts=[]
for v in bm.verts:
    if v.index in seen: continue
    st=[v]; comp=[]; seen.add(v.index)
    while st:
        a=st.pop(); comp.append(a.index)
        for e_ in a.link_edges:
            b=e_.other_vert(a)
            if b.index not in seen: seen.add(b.index); st.append(b)
    c=co[comp]; parts.append((len(comp), c.mean(0).round(3).tolist(), c.min(0).round(3).tolist(), c.max(0).round(3).tolist()))
parts.sort(reverse=True)
print(len(parts))
for p in parts: print(p)
