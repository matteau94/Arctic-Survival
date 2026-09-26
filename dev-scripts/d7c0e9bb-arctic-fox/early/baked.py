import bpy
D=r"C:/Users/leosp/Documents/ArcticFox_Textures/"
m=bpy.data.materials.get("ArcticFox_Baked") or bpy.data.materials.new("ArcticFox_Baked")
m.use_nodes=True; nt=m.node_tree; N=nt.nodes; L=nt.links; N.clear()
out=N.new('ShaderNodeOutputMaterial'); out.location=(700,0)
b=N.new('ShaderNodeBsdfPrincipled'); b.location=(400,0)
def tex(fn, noncolor, loc):
    i=bpy.data.images.load(D+fn, check_existing=True); i.reload()
    if noncolor: i.colorspace_settings.name='Non-Color'
    t=N.new('ShaderNodeTexImage'); t.image=i; t.location=loc; return t
bc=tex("ArcticFox_BaseColor.png",False,(-500,300)); ao=tex("ArcticFox_AO.png",True,(-500,0))
rg=tex("ArcticFox_Roughness.png",True,(-500,-300)); nm=tex("ArcticFox_Normal.png",True,(-500,-600))
mix=N.new('ShaderNodeMix'); mix.data_type='RGBA'; mix.blend_type='MULTIPLY'; mix.location=(-100,200)
mix.inputs['Factor'].default_value=0.55
L.new(bc.outputs['Color'],mix.inputs[6]); L.new(ao.outputs['Color'],mix.inputs[7])
L.new(mix.outputs[2],b.inputs['Base Color']); L.new(rg.outputs['Color'],b.inputs['Roughness'])
nmap=N.new('ShaderNodeNormalMap'); nmap.location=(100,-500)
L.new(nm.outputs['Color'],nmap.inputs['Color']); L.new(nmap.outputs['Normal'],b.inputs['Normal'])
b.inputs['Sheen Weight'].default_value=0.15
L.new(b.outputs['BSDF'],out.inputs['Surface'])
for n in ("ArcticFox","FoxJaw"):
    me=bpy.data.objects[n].data
    for i in range(len(me.materials)): me.materials[i]=m
    me.color_attributes.active_color_index=0
print("ok")
