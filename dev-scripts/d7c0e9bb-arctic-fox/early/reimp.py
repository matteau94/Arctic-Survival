import bpy
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
for c in list(bpy.data.collections): bpy.data.collections.remove(c)
for _ in range(3): bpy.ops.outliner.orphans_purge(do_recursive=True)
bpy.ops.import_scene.gltf(filepath=r"C:/Users/leosp/Documents/Fox.glb")
fox=[o for o in bpy.data.objects if o.type=='MESH'][0]
root=fox.parent
mw=fox.matrix_world.copy(); fox.parent=None; fox.matrix_world=mw
if root: bpy.data.objects.remove(root, do_unlink=True)
bpy.ops.object.select_all(action='DESELECT'); fox.select_set(True); bpy.context.view_layer.objects.active=fox
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
fox.name="fox.1"
print([o.name for o in bpy.data.objects], [i.name for i in bpy.data.images])
