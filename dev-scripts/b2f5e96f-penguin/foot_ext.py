import bpy
m=bpy.data.objects["Penguin"]; gi={g.index:g.name for g in m.vertex_groups}
for v in m.data.vertices:
    if len(v.groups) and v.co.z>0.2:
        b=max(v.groups,key=lambda g:g.weight)
        if gi[b.group].startswith(("foot","shin","thigh")): print("V",v.index,tuple(round(x,3) for x in v.co), gi[b.group], len(v.link_edges) if hasattr(v,'link_edges') else '')
print("materials",[s.material.name if s.material else None for s in m.material_slots])
