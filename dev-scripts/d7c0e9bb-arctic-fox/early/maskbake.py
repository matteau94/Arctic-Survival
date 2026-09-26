import bpy, numpy as np
sc=bpy.context.scene
ref=bpy.data.objects["RedFox_Reference"]; me=ref.data; N=len(me.vertices)
isl=np.load(r"C:/Users/leosp/AppData/Local/Temp/foxwork/isl.npy"); sizes=np.bincount(isl)
co=np.empty(N*3); me.vertices.foreach_get("co",co); co=co.reshape(-1,3)
nr=np.empty(N*3); me.vertices.foreach_get("normal",nr); nr=nr.reshape(-1,3)
cent=np.array([co[isl==i].mean(0) for i in range(len(sizes))])
small=np.array([sizes[i]<=160 and cent[i][2]<0.06 for i in range(len(sizes))])
legs=np.isin(sizes[isl],[1012,736])
mask=np.where(small[isl],1.0,0.0)
mask=np.maximum(mask, np.where(legs&(co[:,2]<0.014)&(nr[:,2]<-0.3),1.0,0.0))   # paw undersides
if "KeepMask" in me.color_attributes: me.color_attributes.remove(me.color_attributes["KeepMask"])
ca=me.color_attributes.new("KeepMask",'FLOAT_COLOR','POINT')
cols=np.repeat(mask[:,None],4,1); cols[:,3]=1; ca.data.foreach_set("color",cols.ravel())
rc=bpy.data.collections["Reference"]; rc.hide_render=False; ref.hide_render=False; ref.hide_set(False)
orig=me.materials[0]
pm=bpy.data.materials.get("MaskBake") or bpy.data.materials.new("MaskBake"); pm.use_nodes=True
nt=pm.node_tree; nt.nodes.clear()
at=nt.nodes.new('ShaderNodeVertexColor'); at.layer_name="KeepMask"
em=nt.nodes.new('ShaderNodeEmission'); out=nt.nodes.new('ShaderNodeOutputMaterial')
nt.links.new(at.outputs['Color'],em.inputs['Color']); nt.links.new(em.outputs[0],out.inputs['Surface'])
img=bpy.data.images.get("KeepMaskMap")
if img: bpy.data.images.remove(img)
img=bpy.data.images.new("KeepMaskMap",2048,2048,alpha=True,float_buffer=True); img.colorspace_settings.name='Non-Color'
tn=nt.nodes.new('ShaderNodeTexImage'); tn.image=img; nt.nodes.active=tn
me.materials[0]=pm
sc.render.engine='CYCLES'; sc.cycles.samples=1
bpy.ops.object.select_all(action='DESELECT'); ref.select_set(True); bpy.context.view_layer.objects.active=ref
bpy.ops.object.bake(type='EMIT', margin=4, use_clear=True)
me.materials[0]=orig; ref.hide_set(True); ref.hide_render=True; rc.hide_render=True
a=np.empty(2048*2048*4,np.float32); img.pixels.foreach_get(a); a=a.reshape(2048,2048,4)
np.save(r"C:/Users/leosp/AppData/Local/Temp/foxwork/keepmask.npy", a[...,0])
print("mask verts", int(mask.sum()), "texel frac", float((a[...,0]>0.5).mean()))
