import bpy, bmesh
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\Fish.glb")
o = bpy.data.objects["fish.1"]
bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
# largest island
seen={}; 
def comp(v):
    st=[v]; c=[v]; s={v.index}
    while st:
        x=st.pop()
        for e in x.link_edges:
            w=e.other_vert(x)
            if w.index not in s: s.add(w.index); st.append(w); c.append(w)
    return s
body=None
for v in bm.verts:
    if v.co.y>3: body=comp(v); break
print("body",len(body))
import collections
for y0 in [-2.3,-2.25,-2.2,-2.1,-2.0,-1.95,-1.9,-1.85,-1.8,-1.75,-1.7,-1.6]:
    for xs in [(0,0.04),(0.1,0.2)]:
        zs=sorted(round(v.co.z,3) for v in bm.verts if v.index in body and abs(v.co.y-y0)<0.02 and xs[0]<=abs(v.co.x)<xs[1])
        print(y0, xs, zs)
