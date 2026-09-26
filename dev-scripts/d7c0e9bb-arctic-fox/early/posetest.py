import bpy, math
rig=bpy.data.objects["FoxRig"]
for pb in rig.pose.bones: pb.rotation_mode='XYZ'; pb.rotation_euler=(0,0,0); pb.location=(0,0,0)
P=rig.pose.bones; r=math.radians
P['upperarm.L'].rotation_euler.x=r(35); P['forearm.L'].rotation_euler.x=r(-60); P['hand.L'].rotation_euler.x=r(70)
P['thigh.R'].rotation_euler.x=r(-30); P['shin.R'].rotation_euler.x=r(30); P['hock.R'].rotation_euler.x=r(-30)
P['neck1'].rotation_euler.x=r(15); P['head'].rotation_euler.x=r(-15)
for k in range(1,7): P[f'tail{k}'].rotation_euler.x=r(-8); P[f'tail{k}'].rotation_euler.z=r(6)
P['ear.L'].rotation_euler.x=r(-25); P['ear.R'].rotation_euler.x=r(-25)
P['spine2'].rotation_euler.z=r(6)
bpy.context.view_layer.update()
V=[('p_side',(1.7,0,0.28),(0,0,0.22)),('p_q34',(1.1,-1.2,0.5),(0,0,0.22)),('p_back',(0.9,1.1,0.5),(0,0.05,0.2))]
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
