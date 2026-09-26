import bpy, bmesh
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\Fish.glb")
o = bpy.data.objects["fish.1"]
bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
seen=set(); isl=[]
for v in bm.verts:
    if v.index in seen: continue
    st=[v]; comp=[]; seen.add(v.index)
    while st:
        x=st.pop(); comp.append(x)
        for e in x.link_edges:
            w=e.other_vert(x)
            if w.index not in seen: seen.add(w.index); st.append(w)
    isl.append(comp)
for c in sorted(isl,key=len,reverse=True):
    ys=[v.co.y for v in c]; zs=[v.co.z for v in c]; xs=[v.co.x for v in c]
    print(len(c), "x",round(min(xs),3),round(max(xs),3),"y",round(min(ys),3),round(max(ys),3),"z",round(min(zs),3),round(max(zs),3))
# non-manifold/boundary edges near head
bd=[e for e in bm.edges if e.is_boundary]
print("boundary edges", len(bd))
hb=[e for e in bd if e.verts[0].co.y<-1.6]
print("boundary near head", len(hb))
for e in hb[:40]: print([tuple(round(c,3) for c in v.co) for v in e.verts])
