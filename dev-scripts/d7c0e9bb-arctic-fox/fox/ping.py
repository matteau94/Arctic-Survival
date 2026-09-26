import bpy
print(bpy.data.filepath, [a.name for a in bpy.data.actions], [b.name for b in bpy.data.objects["FoxRig"].data.bones][:5])
