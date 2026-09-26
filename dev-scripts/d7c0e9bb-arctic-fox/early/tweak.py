import bpy
from mathutils import Vector
m=bpy.data.materials["FoxFur"]; N=m.node_tree.nodes
b=N["Principled BSDF"]; b.inputs['Sheen Weight'].default_value=0.15; b.inputs['Roughness'].default_value=0.85
N["Bump"].inputs['Strength'].default_value=0.8; N["Bump"].inputs['Distance'].default_value=0.003
N["Noise Texture"].inputs['Scale'].default_value=260
N["Map Range"].inputs['To Min'].default_value=0.78; N["Map Range"].inputs['To Max'].default_value=1.08
me=bpy.data.objects["Fox"].data; ca=me.color_attributes["FoxCol"]
for d in ca.data:
    c=d.color
    if c[0]>0.5: d.color=(c[0]*0.97, c[1]*0.93, c[2]*0.84, 1)
sc=bpy.context.scene
bpy.data.objects["StageSun"].data.energy=4.5
sc.world.node_tree.nodes["Background"].inputs['Strength'].default_value=0.45
for n in ("FoxEye.L","FoxEye.R"):
    o=bpy.data.objects[n]; o.scale=(0.85,1.15,0.72)
print("ok")
