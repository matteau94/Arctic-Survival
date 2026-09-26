# profile cross-sections of the baked mesh around the lip seam (bmesh bisect)
import bpy, bmesh, numpy as np, sys
from mathutils import Vector
me = bpy.data.objects["PolarBear"].data
def lz(y):
    u = min(1.15, max(0.0, y + 7.8)); return 6.95 - 0.23*u + 0.04*u*u
def section(co, no):
    bm = bmesh.new(); bm.from_mesh(me)
    r = bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=co, plane_no=no)
    pts = np.array([v.co[:] for v in r["geom_cut"] if isinstance(v, bmesh.types.BMVert)])
    bm.free(); return pts
print("SIDE: y slice; outermost x of surface at z offsets from line (dz), x>0")
dzs = [0.25,0.15,0.10,0.06,0.03,0.0,-0.03,-0.06,-0.10,-0.15,-0.25]
print("   y   " + " ".join("%6.2f"%d for d in dzs))
for y0 in [-7.6,-7.5,-7.4,-7.3,-7.2,-7.1,-7.0,-6.9,-6.8]:
    P = section((0,y0,0),(0,1,0)); P = P[(P[:,0]>0.05)&(np.abs(P[:,2]-lz(y0))<0.5)]
    row=[]
    for d in dzs:
        z=lz(y0)+d; s=P[np.abs(P[:,2]-z)<0.025]
        row.append(s[:,0].max() if len(s) else np.nan)
    print("%6.2f "%y0 + " ".join("%6.3f"%v for v in row))
print("FRONT: x slice; frontmost -y at dz")
for x0 in [0.0,0.1,0.2,0.3,0.4]:
    P = section((x0+1e-4,0,0),(1,0,0)); P = P[(P[:,1]<-7.3)&(np.abs(P[:,2]-6.9)<0.6)]
    row=[]
    for d in dzs:
        s=P[np.abs(P[:,2]-(6.93+d))<0.025]  # approx
        row.append(-s[:,1].max() if False else (s[:,1].min() if len(s) else np.nan))
    print("%5.2f "%x0 + " ".join("%6.3f"%v for v in row))
