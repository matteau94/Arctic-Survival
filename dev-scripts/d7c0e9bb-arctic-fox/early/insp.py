import bpy
if bpy.context.object and bpy.context.object.mode!="OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.wm.save_mainfile()
bpy.ops.wm.save_as_mainfile(filepath=r"C:/Users/leosp/Documents/ArcticFox_FromGLB.blend")
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
for c in list(bpy.data.collections): bpy.data.collections.remove(c)
bpy.ops.outliner.orphans_purge(do_recursive=True)
bpy.ops.import_scene.gltf(filepath=r"C:/Users/leosp/Documents/Fox.glb")
out=[]
for o in bpy.data.objects:
    d=dict(name=o.name,type=o.type,parent=o.parent.name if o.parent else None,loc=tuple(round(x,3) for x in o.location),rot=tuple(round(x,3) for x in o.rotation_euler),scale=tuple(round(x,3) for x in o.scale),dims=tuple(round(x,3) for x in o.dimensions))
    if o.type=='MESH':
        d['verts']=len(o.data.vertices); d['tris']=sum(len(p.vertices)-2 for p in o.data.polygons)
        d['mats']=[m.name for m in o.data.materials if m]; d['vgroups']=len(o.vertex_groups); d['shapekeys']=len(o.data.shape_keys.key_blocks) if o.data.shape_keys else 0
        d['uv']=[u.name for u in o.data.uv_layers]; d['mods']=[m.type for m in o.modifiers]
    if o.type=='ARMATURE':
        d['bones']=len(o.data.bones); d['bone_names']=[b.name for b in o.data.bones]
    out.append(d)
print(out)
print("actions",[(a.name, tuple(a.frame_range)) for a in bpy.data.actions])
print("images",[(i.name,i.size[:]) for i in bpy.data.images])
