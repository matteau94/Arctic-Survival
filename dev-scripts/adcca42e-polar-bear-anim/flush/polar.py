# radial profiles around the muzzle: planes through vertical axis at (0,CY), angle th from -y toward +x
import bpy, bmesh, numpy as np, math, sys
CY=-6.0
me = bpy.data.objects["PolarBear"].data
def lz(y):
    u = min(1.15, max(0.0, y + 7.8)); return 6.95 - 0.23*u + 0.04*u*u
bm0 = bmesh.new(); bm0.from_mesh(me)
dzs=[0.3,0.2,0.15,0.1,0.06,0.03,0.0,-0.03,-0.06,-0.1,-0.15,-0.2,-0.3,-0.4]
print(" th  seamR  " + " ".join("%6.2f"%d for d in dzs))
res={}
for th in range(0,45,4):
    t=math.radians(th); d=np.array([math.sin(t),-math.cos(t),0]); nrm=(math.cos(t),math.sin(t),0)
    bm=bm0.copy()
    r=bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=(0,CY,0), plane_no=nrm)
    S=[]
    for e in r["geom_cut"]:
        if isinstance(e,bmesh.types.BMEdge):
            a=np.array(e.verts[0].co[:]); b=np.array(e.verts[1].co[:])
            for s in np.linspace(0,1,12): S.append(a+(b-a)*s)
    bm.free()
    S=np.array(S); rr=(S[:,0]*d[0]+(S[:,1]-CY)*d[1]); S=S[rr>0.3]; rr=rr[rr>0.3]
    dz=S[:,2]-np.array([lz(y) for y in S[:,1]])
    row=[]
    for q in dzs:
        m=np.abs(dz-q)<0.012
        row.append(rr[m].max() if m.any() else np.nan)
    m=np.abs(dz)<0.006
    sr=rr[m].max() if m.any() else np.nan
    mu=(dz>-0.08)&(dz<0.1); U=rr[mu].max()
    print("%3d %6.3f  "%(th, sr)+" ".join("%6.3f"%v for v in row)+"   OVH(-.1) %6.3f OVH(-.15) %6.3f"%(U-row[9],U-row[10]))
