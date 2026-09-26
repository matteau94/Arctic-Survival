import bpy
ob=bpy.data.objects['Human']; arm=bpy.data.objects['HumanRig']
for sd in ('L','R'):
    for bn in ('foot.'+sd,'toe.'+sd):
        gi=ob.vertex_groups[bn].index
        vv=[v for v in ob.data.vertices if any(g.group==gi and g.weight>.99 for g in v.groups) and v.co.z<.035]
        print('BOOT',bn,'head',tuple(arm.data.bones[bn].head_local),'tail',tuple(arm.data.bones[bn].tail_local))
        for axis in (1,2):
            for fun in (min,max):
                v=fun(vv,key=lambda v:v.co[axis]); print(axis,fun.__name__,v.index,tuple(v.co))
for k in (47189,44775,44850):
    v=ob.data.vertices[k];print('VERT',k,tuple(v.co))
