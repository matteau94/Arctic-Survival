import bpy, numpy as np
fox=bpy.data.objects["ArcticFox"]; me=fox.data
co=np.empty(len(me.vertices)*3,np.float32); me.vertices.foreach_get("co",co); co=co.reshape(-1,3)
print("bbox",co.min(0).round(3),co.max(0).round(3))
nose=co[co[:,1].argmin()]; print("nose tip",nose.round(3))
# slices along y: z range and x range
for y0 in np.arange(-0.45,0.46,0.05):
    s=co[(co[:,1]>=y0)&(co[:,1]<y0+0.05)]
    if len(s): print(round(y0,2), "z",s[:,2].min().round(3),s[:,2].max().round(3),"x",s[:,0].min().round(3),s[:,0].max().round(3), len(s))
# ear tips: highest points
top=co[co[:,2]>co[:,2].max()-0.06]; print("top region y",top[:,1].min().round(3),top[:,1].max().round(3),"x",top[:,0].min().round(3),top[:,0].max().round(3))
for sx in (1,-1):
    e=co[(co[:,0]*sx>0.01)]; t=e[e[:,2].argmax()]; print("ear tip",sx,t.round(3))
# legs: at z=0.1 clusters
s=co[(co[:,2]>0.08)&(co[:,2]<0.12)]
print("leg slice y range", np.unique((s[:,1]*20).round()/20))
# islands count
import bmesh
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
    c=co[comp]; parts.append((len(comp), c.mean(0).round(3).tolist(), (c.max(0)-c.min(0)).round(3).tolist()))
print("islands", sorted(parts,reverse=True)[:12])
