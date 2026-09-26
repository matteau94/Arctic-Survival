import bpy, numpy as np, bmesh
fox=bpy.data.objects["ArcticFox"]; me=fox.data
bm=bmesh.new(); bm.from_mesh(me)
seen=set(); small=[]
for v in bm.verts:
    if v.index in seen: continue
    st=[v]; comp=[]; seen.add(v.index)
    while st:
        a=st.pop(); comp.append(a)
        for e_ in a.link_edges:
            b=e_.other_vert(a)
            if b.index not in seen: seen.add(b.index); st.append(b)
    if len(comp)<=8: small.append(comp)
print(len(small), set(len(c) for c in small))
c0=small[0]; fs=set(f for v in c0 for f in v.link_faces)
print("faces in sample", len(fs), [len(f.verts) for f in fs], [tuple(round(x,4) for x in v.co) for v in c0])
cs=np.array([np.mean([v.co[:] for v in c],0) for c in small])
ext=np.array([np.ptp([v.co[:] for v in c],0).max() for c in small])
print("size cm mean", (ext.mean()*100).round(2), "max", (ext.max()*100).round(2))
print("y hist", np.histogram(cs[:,1],bins=9,range=(-0.45,0.45))[0])
print("z hist", np.histogram(cs[:,2],bins=6,range=(0,0.54))[0])
m=me.materials[0]; b=m.node_tree.nodes["Principled BSDF"]
print("alpha linked", b.inputs['Alpha'].is_linked, getattr(m,'surface_render_method',''))
for n in m.node_tree.nodes:
    if n.type=='TEX_IMAGE': print(n.name, n.image.name, n.image.colorspace_settings.name, [l.to_socket.name+"@"+l.to_node.name for o in n.outputs for l in o.links], n.image.packed_file is not None)
