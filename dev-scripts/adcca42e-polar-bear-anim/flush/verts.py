import bpy, numpy as np, math, sys
CY=-6.0
ob=bpy.data.objects["PolarBear"]; me=ob.data; ji=ob.vertex_groups["jaw"].index
def lz(y):
    u = min(1.15, max(0.0, y + 7.8)); return 6.95 - 0.23*u + 0.04*u*u
co=np.array([v.co[:] for v in me.vertices])
jw=np.array([next((g.weight for g in v.groups if g.group==ji),0.0) for v in me.vertices])
_,u=np.unique(np.round(co*2000).astype(np.int64),axis=0,return_index=True)
for th in [int(a) for a in sys.argv[sys.argv.index("--")+1:]]:
    t=math.radians(th); d=np.array([math.sin(t),-math.cos(t)]); p=np.array([d[1]*-1,d[0]])
    rel=co[u,:2]-np.array([0,CY]); r=rel@d; perp=rel@np.array([math.cos(t),math.sin(t)])
    dz=co[u,2]-np.array([lz(y) for y in co[u,1]])
    m=(np.abs(perp)<0.05)&(r>0.8)&(dz>-0.6)&(dz<0.3)&(co[u,0]>=-1e-4)
    idx=np.nonzero(m)[0]; rm=np.array([r[idx[np.abs(dz[idx]-dz[i])<0.04]].max() for i in idx]); keep=np.zeros_like(m); keep[idx]=r[idx]>rm-0.3; m=keep
    print("th",th)
    for i in np.argsort(-dz[m]):
        k=u[m][i]; print("  dz %6.3f r %6.3f jw %.2f  xyz %.3f %.3f %.3f"%(dz[m][i],r[m][i],jw[k],*co[k]))
