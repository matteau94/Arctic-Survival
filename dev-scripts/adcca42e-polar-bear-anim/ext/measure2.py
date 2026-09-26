import bpy, numpy as np
me = bpy.data.objects["PolarBear"]; m = me.data
print("mats", [ma.name for ma in m.materials])
nt = m.materials[0].node_tree
for n in nt.nodes:
    print("N", n.type, n.name, getattr(n,'image',None) and n.image.name, [ (i.name, [l.from_node.name for l in i.links]) for i in n.inputs if i.links])
bsdf = next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
mul = nt.nodes["LipLineMul"]; tex = mul.inputs["A"].links[0].from_node
img = tex.image; print("base", img.name)
W,H = img.size; px = np.array(img.pixels[:],dtype=np.float32).reshape(H,W,img.channels)
uvl = m.uv_layers.active; print("uv", uvl.name, [u.name for u in m.uv_layers])
vuv = {}
for l in m.loops: vuv.setdefault(l.vertex_index, []).append(uvl.data[l.index].uv[:])
col = m.color_attributes["LipLine"].data
rows=[]
for v in m.vertices:
    x,y,z = v.co
    if 0<=x<0.5 and y<-7.6 and 6.8<z<7.35:
        u,vv = vuv[v.index][0]; c = px[int(vv*H)%H, int(u*W)%W,:3].mean()
        rows.append((round(x,3),round(y,3),round(z,3),round(float(c),2),round(col[v.index].color[0],2), v.index))
for r in sorted(set(rows),key=lambda r:(round(r[0],1),-r[2])): print("V",*r)
