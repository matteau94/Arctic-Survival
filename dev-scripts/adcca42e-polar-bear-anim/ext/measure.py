import bpy, numpy as np
me = bpy.data.objects["PolarBear"]; m = me.data
mat = m.materials[0]; nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
img = None
for n in nt.nodes:
    if n.type=='TEX_IMAGE': img=n.image; print("img", n.image.name, n.image.size[:])
W,H = img.size; px = np.array(img.pixels[:],dtype=np.float32).reshape(H,W,img.channels)
uv = m.uv_layers.active.data
vuv = {}
for l in m.loops: vuv.setdefault(l.vertex_index, uv[l.index].uv[:])
col = m.color_attributes["LipLine"].data
rows=[]
for v in m.vertices:
    x,y,z = v.co
    if abs(x)<0.7 and -8.3<y<-7.0 and 6.6<z<7.7:
        u,vv = vuv[v.index]; c = px[int(vv*H)%H, int(u*W)%W,:3].mean()
        rows.append((round(x,3),round(y,3),round(z,3),round(float(c),2),round(col[v.index].color[0],2)))
rows=sorted(set(rows),key=lambda r:(abs(r[0]),-r[2]))
for r in rows:
    if r[0]>=-0.01: print("V",*r)
