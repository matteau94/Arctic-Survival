import bpy, bmesh
body=bpy.data.objects["ArcticFox"]; jaw=bpy.data.objects["FoxJaw"]
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); jaw.select_set(True); bpy.context.view_layer.objects.active=body
sc=bpy.context.scene; ts=sc.tool_settings; ts.use_uv_select_sync=False
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.select_all(action='DESELECT')
bpy.ops.uv.select_overlap()
out=[]
for o in (body,jaw):
    bm=bmesh.from_edit_mesh(o.data); uv=bm.loops.layers.uv.active
    faces=[f for f in bm.faces if all(l[uv].select for l in f.loops)]
    out.append((o.name,len(faces),[tuple(round(c,3) for c in (o.matrix_world@f.calc_center_median())) for f in faces[:8]]))
bpy.ops.object.mode_set(mode='OBJECT')
print(out)
