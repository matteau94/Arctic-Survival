import bpy, sys, numpy as np
from mathutils import Vector as V
arm=bpy.data.objects["HumanRig"]; name=sys.argv[-1]
bones=arm.data.bones; pts=[]
for sd in ("L","R"):
    ank=bones[f"foot.{sd}"].head_local; ball=bones[f"toe.{sd}"].head_local
    fwd=ball-ank; fwd.z=0; fwd.normalize()
    for b,p,l in ((f"foot.{sd}",V((ank.x,ank.y,0))-fwd*0.05,"heel"+sd),(f"toe.{sd}",V((ball.x,ball.y,0)),"ball"+sd),(f"toe.{sd}",V((ball.x,ball.y,0))+fwd*0.06,"tip"+sd)):
        pts.append((b,bones[b].matrix_local.inverted()@p,l))
def samp(a):
    arm.animation_data.action=bpy.data.actions[a]; P=[]
    for f in range(int(bpy.data.actions[a].frame_range[1])+1):
        bpy.context.scene.frame_set(f); P.append([np.array(arm.pose.bones[b].matrix@loc) for b,loc,_ in pts])
    return np.array(P)
base=samp("Human_Idle")[:,:,2].min(0)
P=samp(name)
for k,(_,_,l) in enumerate(pts):
    pl=P[:,k,2]<base[k]+0.005; d=np.linalg.norm((P[1:,k,:2]-P[:-1,k,:2]),axis=1)
    bad=[(i,round(d[i]*1000,2),round(P[i,k,2]*1000,1)) for i in range(len(d)) if pl[i] and pl[i+1] and d[i]>0.0015]
    if bad: print(l,bad[:12])
