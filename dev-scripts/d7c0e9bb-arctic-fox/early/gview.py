import bpy, math
from mathutils import Vector
sc=bpy.context.scene
sc.render.engine='CYCLES'; sc.cycles.samples=32; sc.cycles.use_denoising=True
cam=bpy.data.objects.get("FoxPreviewCam")
if not cam:
    cam=bpy.data.objects.new("FoxPreviewCam", bpy.data.cameras.new("FoxPreviewCam")); sc.collection.objects.link(cam)
sc.camera=cam; cam.data.lens=50
sc.render.resolution_x=800; sc.render.resolution_y=560; sc.render.resolution_percentage=100
V=globals().get('V',[('g_side',(1.7,0,0.3),(0,0,0.25)),('g_q34',(1.1,-1.2,0.55),(0,0,0.25)),('g_front',(0,-1.6,0.35),(0,0,0.28)),('g_head',(0.35,-0.8,0.45),(0,-0.3,0.4))])
for name,cl,tg in V:
    cam.location=cl; cam.rotation_euler=(Vector(tg)-Vector(cl)).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=r"C:/Users/leosp/AppData/Local/Temp/foxwork/%s.png"%name
    bpy.ops.render.render(write_still=True)
print("ok")
