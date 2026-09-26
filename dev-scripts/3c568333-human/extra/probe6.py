import bpy, numpy as np, collections
me=bpy.data.objects["Human"]
c=collections.Counter(len(v.groups) for v in me.data.vertices); print(c)
ws=[sum(g.weight for g in v.groups) for v in me.data.vertices]; print(min(ws),max(ws))
print(len(me.data.vertices), len(me.vertex_groups))
md=me.modifiers[0]; print(md.use_vertex_groups, md.use_bone_envelopes, md.use_deform_preserve_volume)
# vertices far from their group bone
arm=bpy.data.objects["HumanRig"]
bad=0
for v in me.data.vertices[:]:
    gname=me.vertex_groups[v.groups[0].group].name
    b=arm.data.bones[gname]
    h=b.head_local; t=b.tail_local
    d=min((v.co-h).length,(v.co-t).length, ((v.co-(h+t)/2).length))
    if d>0.3: bad+=1; 
print("bad",bad)
