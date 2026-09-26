import bpy
from mathutils import Matrix, Vector
fox=bpy.data.objects["fox.1"]; fox.name="ArcticFox"; fox.data.name="ArcticFox"
co=[v.co for v in fox.data.vertices]
mn=Vector((min(c.x for c in co),min(c.y for c in co),min(c.z for c in co))); mx=Vector((max(c.x for c in co),max(c.y for c in co),max(c.z for c in co)))
s=0.9/(mx.y-mn.y)
c=Vector(((mn.x+mx.x)/2,(mn.y+mx.y)/2,mn.z))
fox.data.transform(Matrix.Scale(s,4)@Matrix.Translation(-c))
fox.data.update()
print(s, fox.dimensions[:])
