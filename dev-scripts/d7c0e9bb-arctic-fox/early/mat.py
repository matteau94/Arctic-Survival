import bpy, math
from mathutils import Vector
body = bpy.data.objects["Fox"]; me = body.data
# --- vertex color regions
if "FoxCol" in me.color_attributes: me.color_attributes.remove(me.color_attributes["FoxCol"])
ca = me.color_attributes.new("FoxCol", 'FLOAT_COLOR', 'POINT')
me.color_attributes.active_color = ca
def lerp(a,b,t): return tuple(a[i]+(b[i]-a[i])*t for i in range(4))
def sm(e0,e1,x):
    t=max(0,min(1,(x-e0)/(e1-e0))); return t*t*(3-2*t)
BASE=(0.80,0.76,0.68,1); PAD=(0.06,0.055,0.05,1); EAR=(0.50,0.42,0.40,1); LIP=(0.08,0.07,0.06,1)
for v in me.vertices:
    p=v.co; n=v.normal
    c=BASE
    # slightly warmer/darker underside & legs, lighter back (like the bear's shading)
    c=lerp(c,(0.72,0.67,0.58,1), sm(0.25,0.10,p.z)*0.6)
    # paw pads
    c=lerp(c,PAD, sm(0.012,0.004,p.z)*sm(0.0,-0.6,n.z))
    # inner ear (front-facing surface of ears)
    if p.z>0.47: c=lerp(c,EAR, sm(0.475,0.50,p.z)*sm(0.1,0.7,-n.y)*0.85)
    # lip line / mouth corner
    if p.y<-0.37 and abs(p.x)<0.035:
        c=lerp(c,LIP, sm(0.006,0.0,abs(p.z-0.394))*sm(0.3,0.8,max(abs(n.x),-n.y))*0.9)
    ca.data[v.index].color=c
# --- UVs
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); bpy.context.view_layer.objects.active=body
if not me.uv_layers: me.uv_layers.new(name="UVMap")
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
bpy.ops.object.mode_set(mode='OBJECT')
# --- fur material
mat = bpy.data.materials.get("FoxFur") or bpy.data.materials.new("FoxFur")
mat.use_nodes=True; nt=mat.node_tree; nt.nodes.clear(); N=nt.nodes; L=nt.links
out=N.new('ShaderNodeOutputMaterial'); out.location=(900,0)
bsdf=N.new('ShaderNodeBsdfPrincipled'); bsdf.location=(600,0)
tc=N.new('ShaderNodeTexCoord'); tc.location=(-900,0)
vc=N.new('ShaderNodeVertexColor'); vc.layer_name="FoxCol"; vc.location=(-200,300)
# fine strand grain: anisotropic noise (stretched along Z-ish) + fine noise
mp=N.new('ShaderNodeMapping'); mp.location=(-700,-100); mp.inputs['Scale'].default_value=(1,1,0.35)
n1=N.new('ShaderNodeTexNoise'); n1.location=(-500,-100); n1.inputs['Scale'].default_value=420; n1.inputs['Detail'].default_value=3; n1.inputs['Roughness'].default_value=0.6
n2=N.new('ShaderNodeTexNoise'); n2.location=(-500,-350); n2.inputs['Scale'].default_value=45; n2.inputs['Detail'].default_value=4
L.new(tc.outputs['Object'],mp.inputs['Vector']); L.new(mp.outputs['Vector'],n1.inputs['Vector']); L.new(tc.outputs['Object'],n2.inputs['Vector'])
mx=N.new('ShaderNodeMath'); mx.operation='MULTIPLY_ADD'; mx.location=(-250,-200)
L.new(n2.outputs['Fac'],mx.inputs[0]); mx.inputs[1].default_value=0.35; L.new(n1.outputs['Fac'],mx.inputs[2])
# color variation
ramp=N.new('ShaderNodeMapRange'); ramp.location=(-50,-50)
ramp.inputs['From Min'].default_value=0.2; ramp.inputs['From Max'].default_value=1.0
ramp.inputs['To Min'].default_value=0.86; ramp.inputs['To Max'].default_value=1.06
L.new(mx.outputs[0],ramp.inputs['Value'])
mul=N.new('ShaderNodeMix'); mul.data_type='RGBA'; mul.blend_type='MULTIPLY'; mul.location=(200,200)
mul.inputs['Factor'].default_value=1.0
L.new(vc.outputs['Color'],mul.inputs[6]); L.new(ramp.outputs['Result'],mul.inputs[7])
L.new(mul.outputs[2],bsdf.inputs['Base Color'])
bump=N.new('ShaderNodeBump'); bump.location=(300,-250); bump.inputs['Strength'].default_value=0.45; bump.inputs['Distance'].default_value=0.0015
L.new(mx.outputs[0],bump.inputs['Height']); L.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
bsdf.inputs['Roughness'].default_value=0.78
bsdf.inputs['Sheen Weight'].default_value=0.6; bsdf.inputs['Sheen Roughness'].default_value=0.4
bsdf.inputs['Subsurface Weight'].default_value=0.05
L.new(bsdf.outputs['BSDF'],out.inputs['Surface'])
me.materials.clear(); me.materials.append(mat)
# eyes / nose
def gloss(name, col, rough):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes=True
    b=m.node_tree.nodes.get("Principled BSDF"); b.inputs['Base Color'].default_value=col; b.inputs['Roughness'].default_value=rough
    return m
eye=gloss("FoxEye",(0.012,0.01,0.008,1),0.08); nose=gloss("FoxNose",(0.02,0.018,0.016,1),0.35)
for n,m in (("FoxEye.L",eye),("FoxEye.R",eye),("FoxNose",nose)):
    o=bpy.data.objects[n]; o.data.materials.clear(); o.data.materials.append(m)
print("mat ok", len(me.uv_layers))
