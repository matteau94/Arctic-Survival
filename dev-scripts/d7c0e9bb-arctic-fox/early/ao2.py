import bpy, math, numpy as np
sc=bpy.context.scene; OUT=r"C:/Users/leosp/Documents/ArcticFox_Textures/"; RES=2048
body=bpy.data.objects["ArcticFox"]; jaw=bpy.data.objects["FoxJaw"]
sc.render.engine='CYCLES'; sc.cycles.samples=128; sc.cycles.use_denoising=False
stage=bpy.data.collections.get("FoxPreviewStage")
for o in stage.objects: o.hide_render=True
m=bpy.data.materials["ArcticFox_Baked"]; N=m.node_tree.nodes
tmp=bpy.data.images.get("AO_tmp") or bpy.data.images.new("AO_tmp",RES,RES,alpha=False)
tmp.colorspace_settings.name='Non-Color'
t=N.new('ShaderNodeTexImage'); t.image=tmp; N.active=t
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); jaw.select_set(True); bpy.context.view_layer.objects.active=body
res=[]
for ang in (0,30):
    jaw.rotation_euler.x=math.radians(ang); bpy.context.view_layer.update()
    bpy.ops.object.bake(type='AO', margin=16, use_clear=True)
    a=np.empty(RES*RES*4,dtype=np.float32); tmp.pixels.foreach_get(a); res.append(a)
jaw.rotation_euler.x=0
ao=bpy.data.images.load(OUT+"ArcticFox_AO.png", check_existing=True)
ao.pixels.foreach_set(np.maximum(res[0],res[1])); ao.filepath_raw=OUT+"ArcticFox_AO.png"; ao.file_format='PNG'; ao.save(); ao.reload()
N.remove(t); bpy.data.images.remove(tmp)
for o in stage.objects: o.hide_render=False
print("ok")
