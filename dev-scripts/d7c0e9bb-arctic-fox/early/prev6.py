SHOTS=[('f_q34',(1.05,-1.1,0.55),(0,0.05,0.25),0),('f_open',(0.3,-0.9,0.38),(0,-0.39,0.40),0.5),('f_paws',(0.3,-0.55,0.08),(0,-0.19,0.02),0)]
import bpy, math
from mathutils import Vector
sc=bpy.context.scene
sc.render.engine='CYCLES'; sc.cycles.samples=48; sc.cycles.use_denoising=True
cam=bpy.data.objects.get("FoxPreviewCam")
if not cam:
    cam=bpy.data.objects.new("FoxPreviewCam", bpy.data.cameras.new("FoxPreviewCam")); sc.collection.objects.link(cam)
sc.camera=cam; cam.data.lens=50
sc.render.resolution_x=800; sc.render.resolution_y=560
jaw=bpy.data.objects["FoxJaw"]
shots=globals().get('SHOTS',[
 ('m_open',(0.28,-0.95,0.40),(0,-0.39,0.40),math.radians(28)),
 ('m_side',(0.55,-0.45,0.42),(0,-0.37,0.40),math.radians(28)),
 ('m_closed',(0.28,-0.95,0.40),(0,-0.39,0.40),0),
 ('paws',(0.45,-0.75,0.12),(0,-0.15,0.03),0),
])
for name,cl,tg,ang in shots:
    jaw.rotation_euler.x=ang
    cam.location=cl; cam.rotation_euler=(Vector(tg)-Vector(cl)).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=r"C:/Users/leosp/AppData/Local/Temp/foxwork/%s.png"%name
    bpy.ops.render.render(write_still=True)
jaw.rotation_euler.x=0
print("ok")
