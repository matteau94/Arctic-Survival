# draw cross sections around the lip seam as an image. usage: -- out.png
import bpy, bmesh, numpy as np, sys
out = sys.argv[sys.argv.index("--")+1]
ob = bpy.data.objects["PolarBear"]; me = ob.data
ji = ob.vertex_groups["jaw"].index
def lz(y):
    u = min(1.15, max(0.0, y + 7.8)); return 6.95 - 0.23*u + 0.04*u*u
def segs(co, no):
    bm = bmesh.new(); bm.from_mesh(me)
    dl = bm.verts.layers.deform.active
    jw = [v[dl].get(ji, 0.0) for v in bm.verts]
    r = bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=co, plane_no=no)
    cut = set(v for v in r["geom_cut"] if isinstance(v, bmesh.types.BMVert))
    S=[]
    for e in r["geom_cut"]:
        if isinstance(e, bmesh.types.BMEdge):
            a,b=e.verts
            # jaw weight approx: from neighbouring original verts
            def w(v):
                ws=[jw[o.index] for ee in v.link_edges for o in ee.verts if o not in cut and o.index < len(jw)]
                return np.mean(ws) if ws else 0
            S.append((a.co[:], b.co[:], (w(a)+w(b))/2))
    bm.free(); return S
PW=360; panels=[]
def panel(S, ax_h, ax_v, c_h, c_v, span, flip=False, ref=None):
    img = np.ones((PW,PW,3),dtype=np.float32)
    sc = PW/span
    def P(p):
        h=(p[ax_h]-c_h)*(-1 if flip else 1); v=p[ax_v]-c_v
        return PW/2+h*sc, PW/2-v*sc
    # grid lines every 0.1
    for k in range(-10,11):
        g=int(PW/2+k*0.1*sc)
        if 0<=g<PW: img[g,:,:]*=0.92; img[:,g,:]*=0.92
    if ref is not None:
        r=int(PW/2-(ref-c_v)*sc)
        if 0<=r<PW: img[r,:,:]=[0.6,0.8,1]
    for a,b,w in S:
        (x0,y0),(x1,y1)=P(a),P(b)
        n=int(max(abs(x1-x0),abs(y1-y0)))+2
        col=np.array([1-w,0,w])*0.9
        for t in np.linspace(0,1,n):
            x=int(x0+(x1-x0)*t); y=int(y0+(y1-y0)*t)
            if 0<=x<PW and 0<=y<PW: img[max(0,y-1):y+1,max(0,x-1):x+1]=col
    img[0,:]=0; img[:,0]=0
    return img
ys=[-7.7,-7.55,-7.4,-7.25,-7.1,-6.95,-6.8]
for y0 in ys:
    S=segs((0,y0,0),(0,1,0)); S=[s for s in S if s[0][0]>-0.05]
    panels.append(panel(S,0,2,0.35,lz(y0),1.0,ref=lz(y0)))
for x0 in [0.0,0.15]:
    S=segs((x0+1e-4,0,0),(1,0,0))
    panels.append(panel(S,1,2,-7.6,6.95,1.2,flip=True,ref=6.95))
rows=[np.concatenate(panels[i:i+3] + [np.ones((PW,PW,3),np.float32)]*(3-len(panels[i:i+3])),axis=1) for i in range(0,len(panels),3)]
sheet=np.concatenate(rows,axis=0)[::-1]
H,W,_=sheet.shape
rgba=np.ones((H,W,4),np.float32); rgba[:,:,:3]=sheet
im=bpy.data.images.new("s",W,H); im.pixels=rgba.ravel(); im.filepath_raw=out; im.file_format='PNG'; im.save()
