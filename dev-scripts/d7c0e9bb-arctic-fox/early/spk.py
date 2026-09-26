import bpy
b=bpy.data.objects["ArcticFox"]; me=b.data
odd=[(p.index, tuple(round(x,3) for x in p.center), round(p.area*1e6,2)) for p in me.polygons if p.material_index==1 and (p.center.z<0.36 or p.center.y>-0.3)]
print(len(odd), odd[:20])
