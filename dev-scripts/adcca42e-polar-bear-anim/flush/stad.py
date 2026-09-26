# profiles perpendicular to the muzzle outline (stadium: ellipse front, straight sides)
import bpy, bmesh, numpy as np, math, sys
C=-7.3; A=0.40; B=0.56
me = bpy.data.objects["PolarBear"].data
def lz(y):
    u = min(1.15, max(0.0, y + 7.8)); return 6.95 - 0.23*u + 0.04*u*u
def station(s):
    # s in deg for front ellipse (0..90), >90: side, y = C + (s-90)/100
    if s <= 90:
        f=math.radians(s); p=np.array([A*math.sin(f), C-B*math.cos(f)])
        n=np.array([math.sin(f)/A, -math.cos(f)/B]); n/=np.linalg.norm(n)
    else:
        p=np.array([A, C+(s-90)/100]); n=np.array([1.0,0])
    return p,n
bm0 = bmesh.new(); bm0.from_mesh(me)
dzs=[0.3,0.2,0.15,0.1,0.06,0.03,0.0,-0.03,-0.06,-0.1,-0.15,-0.2,-0.3,-0.4]
print("  s   y0     " + " ".join("%6.2f"%d for d in dzs))
for s in [0,15,30,45,60,75,90,110,130,150,170]:
    p,n=station(s); t=np.array([-n[1],n[0]])
    bm=bm0.copy()
    r=bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=(p[0],p[1],0), plane_no=(t[0],t[1],0))
    S=[]
    for e in r["geom_cut"]:
        if isinstance(e,bmesh.types.BMEdge):
            a=np.array(e.verts[0].co[:]); b=np.array(e.verts[1].co[:])
            for q in np.linspace(0,1,12): S.append(a+(b-a)*q)
    bm.free()
    S=np.array(S); rr=(S[:,:2]-p)@n; S=S[rr>-0.5]; rr=rr[rr>-0.5]
    # keep only this side (x>=0 region near p)
    along=np.abs((S[:,:2]-p)@t); S=S[along<0.02]; rr=rr[along<0.02]
    dz=S[:,2]-np.array([lz(y) for y in S[:,1]])
    row=[]
    for q in dzs:
        m=np.abs(dz-q)<0.012
        row.append(rr[m].max() if m.any() else np.nan)
    mu=(dz>-0.08)&(dz<0.12); U=rr[mu].max()
    lo=np.nanmax([row[9],row[10]])
    print("%4d %6.2f  "%(s,p[1])+" ".join("%6.3f"%v for v in row)+"  OVH %6.3f"%(U-lo))
