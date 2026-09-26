import bpy, numpy as np
me=bpy.data.objects["PolarBear"]; m=me.data
mat=m.materials[0]; nt=mat.node_tree
bsdf=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
img=None
for n in nt.nodes:
    if n.type=='TEX_IMAGE' and n.image: print("img", n.name, n.image.name, n.image.size[:]); img=img or n.image
W,H=img.size; px=np.array(img.pixels[:],dtype=np.float32).reshape(H,W,4)
uv=m.uv_layers.active.data
co=np.array([v.co[:] for v in m.vertices])
dark={}
for l in m.loops:
    u,v=uv[l.index].uv
    c=px[int(min(H-1,max(0,v*H))), int(min(W-1,max(0,u*W)))]
    dark.setdefault(l.vertex_index,[]).append(c[:3].mean())
rows=[]
for vi,vals in dark.items():
    x,y,z=co[vi]
    if 0.3<x<1.1 and -7.2<y<-6.1 and 6.4<z<7.2: rows.append((round(x,2),z,y,np.mean(vals)))
rows.sort()
for r in rows: print("x=%.2f z=%.3f y=%.3f lum=%.2f"%r)
