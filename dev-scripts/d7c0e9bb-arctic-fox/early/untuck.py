import bpy
m=bpy.data.objects["ArcticFox"].data
if "rim_tucked" in m: del m["rim_tucked"]
print("flag cleared")
