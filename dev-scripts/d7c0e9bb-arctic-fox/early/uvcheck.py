import bpy, numpy as np
if bpy.context.object and bpy.context.object.mode!="OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
R=512
def cover(o):
    me=o.data; me.calc_loop_triangles(); uv=me.uv_layers.active.data
    cnt=np.zeros((R,R),np.int32)
    for t in me.loop_triangles:
        P=np.array([uv[l].uv[:] for l in t.loops])*R
        x0,y0=np.floor(P.min(0)).astype(int); x1,y1=np.ceil(P.max(0)).astype(int)
        xs,ys=np.meshgrid(np.arange(max(x0,0),min(x1,R))+0.5, np.arange(max(y0,0),min(y1,R))+0.5)
        if xs.size==0: continue
        a,b,c=P
        def e(p,q): return (q[0]-p[0])*(ys-p[1])-(q[1]-p[1])*(xs-p[0])
        w0,w1,w2=e(b,c),e(c,a),e(a,b)
        ins=((w0>=0)&(w1>=0)&(w2>=0))|((w0<=0)&(w1<=0)&(w2<=0))
        cnt[ys[ins].astype(int), xs[ins].astype(int)]+=1
    return cnt
cb=cover(bpy.data.objects["ArcticFox"]); cj=cover(bpy.data.objects["FoxJaw"])
print("body-jaw overlap px", int(((cb>0)&(cj>0)).sum()), "body self >1 px", int((cb>1).sum()), "jaw self", int((cj>1).sum()))
