import bpy, math
body=bpy.data.objects["ArcticFox"]; jaw=bpy.data.objects["FoxJaw"]
def lerp(a,b,t): return tuple(a[i]+(b[i]-a[i])*t for i in range(4))
def sm(e0,e1,x):
    t=max(0,min(1,(x-e0)/(e1-e0))); return t*t*(3-2*t)
BASE=(0.776,0.707,0.571,1); UNDER=(0.698,0.623,0.487,1)
PAD=(0.06,0.055,0.05,1); EAR=(0.50,0.42,0.40,1); LIP=(0.08,0.07,0.06,1)
for o in (body,jaw):
    me=o.data
    for a in list(me.color_attributes): me.color_attributes.remove(a)
    ca=me.color_attributes.new("FoxCol",'FLOAT_COLOR','POINT'); me.color_attributes.active_color=ca
    R=o.matrix_world.to_3x3()
    for v in me.vertices:
        p=o.matrix_world@v.co; n=(R@v.normal).normalized()
        c=lerp(BASE,UNDER, sm(0.25,0.10,p.z)*0.6)
        c=lerp(c,PAD, sm(0.012,0.004,p.z)*sm(0.0,-0.6,n.z))
        if p.z>0.47: c=lerp(c,EAR, sm(0.475,0.50,p.z)*sm(0.1,0.7,-n.y)*0.85)
        if p.y<-0.36 and abs(p.x)<0.045:            # dark lips along the mouth seam
            c=lerp(c,LIP, sm(0.007,0.001,abs(p.z-0.393))*0.9)
        ca.data[v.index].color=c
import sys
# shared UV atlas for head + jaw
bpy.ops.object.select_all(action='DESELECT')
for o in (body,jaw):
    o.select_set(True)
    for uv in list(o.data.uv_layers): o.data.uv_layers.remove(uv)
    o.data.uv_layers.new(name="UVMap")
bpy.context.view_layer.objects.active=body
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
bpy.ops.uv.pack_islands(margin=0.003)
bpy.ops.object.mode_set(mode='OBJECT')
# fur shader (same as before) — make sure settings are the tuned ones
m=bpy.data.materials["FoxFur"]; N=m.node_tree.nodes
[n for n in N if n.type=="VERTEX_COLOR"][0].layer_name="FoxCol"
b=N["Principled BSDF"]; b.inputs['Sheen Weight'].default_value=0.15; b.inputs['Roughness'].default_value=0.85
N["Bump"].inputs['Strength'].default_value=0.8; N["Bump"].inputs['Distance'].default_value=0.003
N["Noise Texture"].inputs['Scale'].default_value=260
N["Map Range"].inputs['To Min'].default_value=0.78; N["Map Range"].inputs['To Max'].default_value=1.08
# mouth: wet gum with subtle mottling + bump
mm=bpy.data.materials["FoxMouth"]; nt=mm.node_tree; N=nt.nodes; L=nt.links
bs=N["Principled BSDF"]
if "Noise Texture" not in N:
    nz=N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value=120
    mix=N.new('ShaderNodeMix'); mix.data_type='RGBA'
    mix.inputs[6].default_value=(0.22,0.05,0.06,1); mix.inputs[7].default_value=(0.38,0.12,0.13,1)
    L.new(nz.outputs['Fac'],mix.inputs['Factor']); L.new(mix.outputs[2],bs.inputs['Base Color'])
    bp=N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value=0.3; bp.inputs['Distance'].default_value=0.001
    L.new(nz.outputs['Fac'],bp.inputs['Height']); L.new(bp.outputs['Normal'],bs.inputs['Normal'])
bs.inputs['Roughness'].default_value=0.35
print("ok", len(body.data.polygons), len(jaw.data.polygons))
