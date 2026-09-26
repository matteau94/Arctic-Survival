import bpy, numpy as np, bmesh
fox=bpy.data.objects["ArcticFox"]; me=fox.data; N=len(me.vertices)
co=np.empty(N*3); me.vertices.foreach_get("co",co); co=co.reshape(-1,3)
bm=bmesh.new(); bm.from_mesh(me)
isl=np.full(N,-1); k=0; sizes=[]
for v in bm.verts:
    if isl[v.index]>=0: continue
    st=[v]; isl[v.index]=k; n=0
    while st:
        a=st.pop(); n+=1
        for e in a.link_edges:
            b=e.other_vert(a)
            if isl[b.index]<0: isl[b.index]=k; st.append(b)
    sizes.append(n); k+=1
sizes=np.array(sizes)
np.save(r"C:/Users/leosp/AppData/Local/Temp/foxwork/isl.npy", isl)
for s in (1012,736,782,1493,1358):
    for i in np.where(sizes==s)[0]:
        P=co[isl==i]; print("island",s,i,"centroid",P.mean(0).round(3),"min",P.min(0).round(3),"max",P.max(0).round(3))
        if s in (1012,736):
            for z0 in np.arange(0.0,0.34,0.02):
                q=P[(P[:,2]>=z0)&(P[:,2]<z0+0.02)]
                if len(q)>3: print("   z%.2f"%z0, "y[%.3f %.3f] c%.3f  x c%.3f n%d"%(q[:,1].min(),q[:,1].max(),q[:,1].mean(),q[:,0].mean(),len(q)))
