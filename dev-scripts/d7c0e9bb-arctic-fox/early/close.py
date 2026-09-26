import bpy
from mathutils import Vector
sc=bpy.context.scene; rig=bpy.data.objects["FoxRig"]
sc.render.engine='CYCLES'; sc.cycles.samples=24; sc.cycles.use_denoising=True
cam=bpy.data.objects["FoxPreviewCam"]; cam.data.type='PERSP'; cam.data.lens=50; sc.camera=cam
sc.render.resolution_x=800; sc.render.resolution_y=560
rig.hide_render=True
for an,fr,cl,tg,nm in [("ArcticFox_Trot",12,(0.9,0.25,0.3),(0,0.1,0.18),"c_trot12"),("ArcticFox_Walk",0,(0.9,0.25,0.3),(0,0.1,0.18),"c_walk0"),("ArcticFox_Gallop",3,(0.9,-0.4,0.35),(0,-0.15,0.22),"c_gal3")]:
    rig.animation_data.action=bpy.data.actions[an]; sc.frame_set(fr)
    cam.location=cl; cam.rotation_euler=(Vector(tg)-Vector(cl)).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=r"C:/Users/leosp/AppData/Local/Temp/foxwork/%s.png"%nm; bpy.ops.render.render(write_still=True)
print("ok")
