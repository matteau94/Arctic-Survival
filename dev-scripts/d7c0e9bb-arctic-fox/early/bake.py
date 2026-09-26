import bpy, math, os
sc=bpy.context.scene
OUT=r"C:/Users/leosp/Documents/ArcticFox_Textures/"
RES=2048
body=bpy.data.objects["ArcticFox"]; jaw=bpy.data.objects["FoxJaw"]
sc.render.engine='CYCLES'; sc.cycles.samples=32; sc.cycles.use_denoising=False
stage=bpy.data.collections.get("FoxPreviewStage")
if stage:
    for o in stage.objects: o.hide_render=True
mats=[bpy.data.materials["FoxFur"], bpy.data.materials["FoxMouth"]]
for m in mats: m.use_fake_user=True
def img(name, noncolor):
    i=bpy.data.images.get(name)
    if i: bpy.data.images.remove(i)
    i=bpy.data.images.new(name, RES, RES, alpha=False, float_buffer=False)
    if noncolor: i.colorspace_settings.name='Non-Color'
    return i
def target(i):
    for m in mats:
        N=m.node_tree.nodes
        n=N.get("BakeTarget") or N.new('ShaderNodeTexImage'); n.name="BakeTarget"; n.location=(1000,400)
        n.image=i; N.active=n
def select():
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True); jaw.select_set(True); bpy.context.view_layer.objects.active=body
def save(i, fn):
    i.filepath_raw=OUT+fn; i.file_format='PNG'; i.save()
bk=sc.render.bake; bk.margin=16; bk.use_clear=True
results={}
select()
i=img("ArcticFox_BaseColor",False); target(i)
bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, margin=16, use_clear=True); save(i,"ArcticFox_BaseColor.png")
i=img("ArcticFox_Normal",True); target(i)
bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', margin=16, use_clear=True); save(i,"ArcticFox_Normal.png")
i=img("ArcticFox_Roughness",True); target(i)
bpy.ops.object.bake(type='ROUGHNESS', margin=16, use_clear=True); save(i,"ArcticFox_Roughness.png")
# AO with the jaw open so the mouth interior isn't baked pitch black
jaw.rotation_euler.x=math.radians(30); bpy.context.view_layer.update()
sc.cycles.samples=128
i=img("ArcticFox_AO",True); target(i)
bpy.ops.object.bake(type='AO', margin=16, use_clear=True); save(i,"ArcticFox_AO.png")
jaw.rotation_euler.x=0
for m in mats:
    n=m.node_tree.nodes.get("BakeTarget")
    if n: m.node_tree.nodes.remove(n)
if stage:
    for o in stage.objects: o.hide_render=False
print(sorted(os.listdir(OUT)))
