import bpy, numpy as np, bmesh
from mathutils import kdtree
fox=bpy.data.objects["ArcticFox"]; me=fox.data
if me.get("rim_tucked"): raise SystemExit("already tucked")
isl=np.load(r"C:/Users/leosp/AppData/Local/Temp/foxwork/isl.npy"); sizes=np.bincount(isl)
b=bmesh.new(); b.from_mesh(me); b.verts.ensure_lookup_table()
legisl=np.isin(sizes[isl],[1012,736])
bnd=[v.index for v in b.verts if legisl[v.index] and any(e.is_boundary for e in v.link_edges)]
kb=kdtree.KDTree(len(bnd))
for j,v in enumerate(bnd): kb.insert(b.verts[v].co,j)
kb.balance()
n=0
for v in b.verts:
    if not legisl[v.index] or v.co.z<0.12: continue
    _,_,d=kb.find(v.co)
    t=max(0.0,1-d/0.025); t=t*t*(3-2*t)
    if t>0: v.co-=v.normal*0.0045*t; n+=1
b.to_mesh(me); me.update(); me["rim_tucked"]=1
print("moved",n)
