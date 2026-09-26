import bpy
from mathutils import Vector, Matrix
fox=bpy.data.objects["fox.1"]; root=bpy.data.objects["RootNode.0"]
mw=fox.matrix_world.copy(); fox.parent=None; fox.matrix_world=mw
bpy.data.objects.remove(root, do_unlink=True)
bpy.ops.object.select_all(action='DESELECT'); fox.select_set(True); bpy.context.view_layer.objects.active=fox
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
co=[v.co for v in fox.data.vertices]
mn=Vector((min(c.x for c in co),min(c.y for c in co),min(c.z for c in co))); mx=Vector((max(c.x for c in co),max(c.y for c in co),max(c.z for c in co)))
print("bbox",mn[:],mx[:])
# report where the mass is along Y (head vs tail) by vertical extent
import collections
bins=collections.defaultdict(list)
for c in co: bins[int((c.y-mn.y)/(mx.y-mn.y)*10)].append(c.z)
print({k:(round(min(v),4),round(max(v),4),len(v)) for k,v in sorted(bins.items())})
m=fox.data.materials[0]
print([(n.type,n.name,getattr(n,'image',None) and n.image.name, [l.to_socket.name for o in n.outputs for l in o.links]) for n in m.node_tree.nodes])
