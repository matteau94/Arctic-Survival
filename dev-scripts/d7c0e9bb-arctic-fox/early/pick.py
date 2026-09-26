import bpy, math
from mathutils import Vector
sc=bpy.context.scene; cam=bpy.data.objects["FoxPreviewCam"]; body=bpy.data.objects["ArcticFox"]
def aim(cl,tg):
    cam.location=cl; cam.rotation_euler=(Vector(tg)-Vector(cl)).to_track_quat('-Z','Y').to_euler(); bpy.context.view_layer.update()
def ray(px,py,W=800,H=560):
    fr=[cam.matrix_world@v for v in cam.data.view_frame(scene=sc)]  # tr, br, bl, tl
    tr,br,bl,tl=fr; u=px/W; v=py/H
    top=tl.lerp(tr,u); bot=bl.lerp(br,u); p=top.lerp(bot,v)
    d=(p-cam.location).normalized()
    hit,loc,n,idx=body.ray_cast(cam.location,d)
    if not hit: return None
    me=body.data; poly=me.polygons[idx]; uvl=me.uv_layers.active.data
    uvs=[tuple(round(c,4) for c in uvl[li].uv) for li in poly.loop_indices]
    return tuple(round(c,3) for c in loc), idx, round(poly.area*1e6,3), uvs
aim((0.3,-0.9,0.38),(0,-0.39,0.40))
for p in [(495,493),(500,490),(530,487)]: print(p, ray(*p))
aim((1.05,-1.1,0.55),(0,0.05,0.25))
print((220,300), ray(220,300))
