import bpy
from mathutils import Vector, Matrix
sc=bpy.context.scene; rig=bpy.data.objects["FoxRig"]; ad=rig.animation_data; keep=ad.action; ad.action=None
for pb in rig.pose.bones: pb.matrix_basis=Matrix()
cam=bpy.data.objects["FoxPreviewCam"]; cl=(0.9,0.25,0.3); tg=(0,0.1,0.18)
cam.location=cl; cam.rotation_euler=(Vector(tg)-Vector(cl)).to_track_quat('-Z','Y').to_euler()
sc.render.filepath=r"C:/Users/leosp/AppData/Local/Temp/foxwork/c_rest.png"; bpy.ops.render.render(write_still=True)
# also: which island is under the arc? cast ray from camera at arc pixel (~300,190 of 800x560)
fox=bpy.data.objects["ArcticFox"]
import numpy as np
isl=np.load(r"C:/Users/leosp/AppData/Local/Temp/foxwork/isl.npy"); sizes=np.bincount(isl)
dg=bpy.context.evaluated_depsgraph_get()
res=[]
fr=[cam.matrix_world@v for v in cam.data.view_frame(scene=sc)]
tr,br,bl,tl=fr
for px,py in [(300,185),(300,200),(260,240),(400,190)]:
    u=px/800; v=py/560; p=tl.lerp(tr,u).lerp(bl.lerp(br,u),v)
    hit,loc,n,idx,ob,_=sc.ray_cast(dg,cam.location,(p-cam.location).normalized())
    if hit and ob.name=="ArcticFox":
        pv=fox.data.polygons[idx].vertices[0]; res.append((px,py,int(sizes[isl[pv]]),tuple(round(c,3) for c in loc)))
    else: res.append((px,py,ob.name if hit else None))
ad.action=keep
print(res)
