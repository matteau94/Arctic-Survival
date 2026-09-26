import bpy
arm=bpy.data.objects["PenguinRig"]
for b in arm.data.bones:
    print(f"{b.name:18s} parent={b.parent.name if b.parent else None!s:14s} head={tuple(round(x,3) for x in b.head_local)} tail={tuple(round(x,3) for x in b.tail_local)} roll_mat_y={tuple(round(x,2) for x in b.matrix_local.col[1][:3])}")
m=bpy.data.objects["Penguin"]
print("verts",len(m.data.vertices), "groups",[g.name for g in m.vertex_groups])
zs=[v.co.z for v in m.data.vertices]; print("zrange",min(zs),max(zs))
print("mods",[(x.type) for x in m.modifiers], "parent", m.parent)
