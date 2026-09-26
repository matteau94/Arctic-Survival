import bpy, os
mo=bpy.data.objects.get("FoxMeta")
if mo: bpy.data.objects.remove(mo, do_unlink=True)
for mb in list(bpy.data.metaballs):
    if mb.users==0: bpy.data.metaballs.remove(mb)
fox=bpy.data.objects["Fox"]; fox.name="ArcticFox"
fox.data.name="ArcticFox"
for o in fox.children: o.hide_select=False
print("file:", bpy.data.filepath or "(unsaved)")
p=r"C:/Users/leosp/Documents/ArcticFox.blend"
print("exists:", os.path.exists(p))
print([(o.name,o.type) for o in bpy.data.objects], "tris", sum(len(p.vertices)-2 for p in fox.data.polygons), fox.dimensions[:])
