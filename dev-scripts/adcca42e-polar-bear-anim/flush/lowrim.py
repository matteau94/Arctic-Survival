import bpy, numpy as np, math
ob=bpy.data.objects["PolarBear"]; me=ob.data; ji=ob.vertex_groups["jaw"].index
C,A,B=-7.3,0.40,0.56
def lz(y):
    u = min(1.15, max(0.0, y + 7.8)); return 6.95 - 0.23*u + 0.04*u*u
co=np.array([v.co[:] for v in me.vertices]); jw=np.array([next((g.weight for g in v.groups if g.group==ji),0.0) for v in me.vertices])
_,u=np.unique(np.round(co*2000).astype(np.int64),axis=0,return_index=True)
for k in u:
    x,y,z=co[k]
    if x<0 or y>C: continue
    uu=x/A; vv=-(y-C)/B; phi=math.degrees(math.atan2(uu,vv)); rho=math.hypot(uu,vv)
    gx=x/A**2; gy=(y-C)/B**2; d=(rho-1)*rho/math.hypot(gx,gy)
    dz=z-lz(y)
    if 35<phi<85 and -0.35<dz<0.05 and d>-0.25:
        print("s %5.1f dz %6.3f d %6.3f jw %.2f  xyz %.3f %.3f %.3f"%(phi,dz,d,jw[k],x,y,z))
