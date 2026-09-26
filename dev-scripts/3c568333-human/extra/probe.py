import bpy
arm=bpy.data.objects["HumanRig"]
for b in arm.data.bones:
    if b.name.endswith(".R") : continue
    m=b.matrix_local.to_3x3()
    print(f"{b.name:14s} h={tuple(round(x,3) for x in b.head_local)} t={tuple(round(x,3) for x in b.tail_local)} X={tuple(round(x,2) for x in m.col[0])} Z={tuple(round(x,2) for x in m.col[2])} par={b.parent.name if b.parent else None}")
print([o.name for o in bpy.data.objects], bpy.app.version_string)
