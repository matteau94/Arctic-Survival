import bpy
from mathutils import Vector
sc=bpy.context.scene; ref=bpy.data.objects["RedFox_Reference"]; fox=bpy.data.objects["ArcticFox"]; rig=bpy.data.objects["FoxRig"]
rc=bpy.data.collections["Reference"]
sc.render.engine='CYCLES'; sc.cycles.samples=32; sc.cycles.use_denoising=True
cam=bpy.data.objects["FoxPreviewCam"]; cam.data.type='PERSP'; sc.camera=cam
sc.render.resolution_x=800; sc.render.resolution_y=560
rig.hide_render=True
def shot(name, obj_show, cl, tg):
    for o,v in ((ref,obj_show=='ref'),(fox,obj_show=='fox')): o.hide_render=not v
    rc.hide_render = obj_show!='ref'
    cam.location=cl; cam.rotation_euler=(Vector(tg)-Vector(cl)).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=r"C:/Users/leosp/AppData/Local/Temp/foxwork/%s.png"%name; bpy.ops.render.render(write_still=True)
shot("paw_ref","ref",(0.25,-0.55,0.10),(0.04,-0.2,0.02))
shot("paw_fox","fox",(0.25,-0.55,0.10),(0.04,-0.17,0.02))
ref.hide_render=True; rc.hide_render=True; fox.hide_render=False
print("ok")
