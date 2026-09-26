import bpy, sys, collections
from mathutils.geometry import intersect_point_line
me=bpy.data.objects["Human"]; arm=bpy.data.objects["HumanRig"]
m=me.data
par=list(range(len(m.vertices)))
def f(a):
    while par[a]!=a: par[a]=par[par[a]]; a=par[a]
    return a
for e in m.edges:
    a,b=f(e.vertices[0]),f(e.vertices[1]); par[a]=b
isl=collections.defaultdict(list)
for v in m.vertices: isl[f(v.index)].append(v.index)
names=[g.name for g in me.vertex_groups]
fixed=0
for root,vs in isl.items():
    # bone whose segment is closest to the island centroid
    c=sum((m.vertices[i].co for i in vs), m.vertices[vs[0]].co*0)/len(vs)
    best=None
    for n in names:
        b=arm.data.bones[n]; p,t=intersect_point_line(c,b.head_local,b.tail_local); t=max(0,min(1,t))
        d=(c-(b.head_local+(b.tail_local-b.head_local)*t)).length
        if best is None or d<best[0]: best=(d,n)
    for i in vs:
        cur=me.vertex_groups[m.vertices[i].groups[0].group].name
        if cur!=best[1]:
            me.vertex_groups[cur].remove([i]); me.vertex_groups[best[1]].add([i],1.0,'REPLACE'); fixed+=1
print("islands",len(isl),"fixed",fixed)
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-1])
