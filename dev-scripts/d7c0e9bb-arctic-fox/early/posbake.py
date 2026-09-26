import bpy, numpy as np
sc=bpy.context.scene
ref=bpy.data.objects["RedFox_Reference"]; fox=bpy.data.objects["ArcticFox"]
rc=bpy.data.collections["Reference"]
lc=bpy.context.view_layer.layer_collection.children[rc.name]; lc.exclude=False; lc.hide_viewport=False
rc.hide_render=False; ref.hide_render=False; ref.hide_set(False); ref.hide_viewport=False
orig=ref.data.materials[0]
pm=bpy.data.materials.get("PosBake") or bpy.data.materials.new("PosBake"); pm.use_nodes=True
nt=pm.node_tree; nt.nodes.clear()
geo=nt.nodes.new('ShaderNodeNewGeometry'); add=nt.nodes.new('ShaderNodeVectorMath'); add.operation='ADD'; add.inputs[1].default_value=(0.5,0.5,0.5)
em=nt.nodes.new('ShaderNodeEmission'); out=nt.nodes.new('ShaderNodeOutputMaterial')
nt.links.new(geo.outputs['Position'],add.inputs[0]); nt.links.new(add.outputs[0],em.inputs['Color']); nt.links.new(em.outputs[0],out.inputs['Surface'])
img=bpy.data.images.get("PosMap")
if img: bpy.data.images.remove(img)
img=bpy.data.images.new("PosMap",2048,2048,alpha=True,float_buffer=True); img.colorspace_settings.name='Non-Color'
img.generated_color=(0,0,0,0)
tn=nt.nodes.new('ShaderNodeTexImage'); tn.image=img; nt.nodes.active=tn
ref.data.materials[0]=pm
sc.render.engine='CYCLES'; sc.cycles.samples=1
bpy.ops.object.select_all(action='DESELECT'); ref.select_set(True); bpy.context.view_layer.objects.active=ref
bpy.ops.object.bake(type='EMIT', margin=3, use_clear=False)
ref.data.materials[0]=orig
ref.hide_set(True); ref.hide_render=True; rc.hide_render=True
a=np.empty(2048*2048*4,np.float32); img.pixels.foreach_get(a); a=a.reshape(2048,2048,4)
cov=a[...,3]>0.5
print("coverage",cov.mean().round(3), "pos range", (a[cov,:3]-0.5).min(0).round(3), (a[cov,:3]-0.5).max(0).round(3))
np.save(r"C:/Users/leosp/AppData/Local/Temp/foxwork/posmap.npy", a)
