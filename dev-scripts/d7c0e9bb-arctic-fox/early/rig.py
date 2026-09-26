import bpy, numpy as np, math
from mathutils import Vector
exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-AppData-Roaming-Claude-scratch-workspaces-beda0dcd-63a1-4648-a0b8-bb28fcdf9a14-33a69ef5-7371-434a-9644-a2a50600043d-scratch-2026-09-22-0b3d57/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/joints.py").read())
mc=bpy.data.collections.get("JointMarkers")
if mc:
    for o in list(mc.objects): bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.collections.remove(mc)
fox=bpy.data.objects["ArcticFox"]; me=fox.data
co=np.array([v.co[:] for v in me.vertices]); isl=np.load(r"C:/Users/leosp/AppData/Local/Temp/foxwork/isl.npy")
sizes=np.bincount(isl)
old=bpy.data.objects.get("FoxRig")
if old: bpy.data.objects.remove(old,do_unlink=True)
arm=bpy.data.armatures.new("FoxRig"); rig=bpy.data.objects.new("FoxRig",arm)
fox.users_collection[0].objects.link(rig)
arm.display_type='STICK'; rig.show_in_front=True
bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active=rig; rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
eb=arm.edit_bones
def bone(name,h,t,parent=None,connect=False,up=(0,0,1)):
    b=eb.new(name); b.head=Vector(h); b.tail=Vector(t)
    if parent: b.parent=eb[parent]; b.use_connect=connect
    b.align_roll(Vector(up)); return b
bone("root",(0,0,0),(0,0.12,0),up=(0,0,1))
bone("hips",(0,0.10,0.28),(0,0.19,0.29),"root")
bone("spine1",(0,0.10,0.28),(0,0.0,0.285),"hips")
bone("spine2",(0,0.0,0.285),(0,-0.10,0.29),"spine1",True)
bone("chest",(0,-0.10,0.29),(0,-0.19,0.30),"spine2",True)
bone("neck1",(0,-0.19,0.30),(0,-0.255,0.345),"chest",True)
bone("neck2",(0,-0.255,0.345),(0,-0.30,0.375),"neck1",True)
bone("head",(0,-0.30,0.375),(0,-0.42,0.36),"neck2",True)
# ears from ear islands
for i in np.where(sizes==319)[0]:
    P=co[isl==i]; side='L' if P[:,0].mean()>0 else 'R'
    base=P[P[:,2]<P[:,2].min()+0.012].mean(0); tip=P[P[:,2].argmax()]
    bone(f"ear.{side}",base,tip-(tip-base)*0.05,"head",up=(0,-1,0))
# tail centerline from the tail island
P=co[isl==np.where(sizes==782)[0][0]]
ys=np.linspace(0.20,P[:,1].max()-0.015,7); pts=[]
for yv in ys:
    q=P[np.abs(P[:,1]-yv)<0.02]; pts.append((0.0,yv,float(q[:,2].mean()) if len(q) else pts[-1][2]))
pts[0]=(0,0.19,0.29)
prev="hips"
for k in range(6):
    bone(f"tail{k+1}",pts[k],pts[k+1],prev,connect=(k>0)); prev=f"tail{k+1}"
# legs
def P3(x,yz): return (x,yz[0],yz[1])
for s in ('L','R'):
    d=J['H'+s]; x=d['x']
    bone(f"thigh.{s}",P3(x,d['hip']),P3(x,d['knee']),"hips",up=(0,-1,0))
    bone(f"shin.{s}",P3(x,d['knee']),P3(x,d['hock']),f"thigh.{s}",True,up=(0,-1,0))
    bone(f"hock.{s}",P3(x,d['hock']),P3(x,d['ball']),f"shin.{s}",True,up=(0,-1,0))
    bone(f"toes_hind.{s}",P3(x,d['ball']),P3(x,d['toe']),f"hock.{s}",True,up=(0,0,1))
    d=J['F'+s]; x=d['x']
    bone(f"scapula.{s}",P3(x*0.8,d['scap']),P3(x,d['shoulder']),"chest",up=(0,-1,0))
    bone(f"upperarm.{s}",P3(x,d['shoulder']),P3(x,d['elbow']),f"scapula.{s}",True,up=(0,-1,0))
    bone(f"forearm.{s}",P3(x,d['elbow']),P3(x,d['wrist']),f"upperarm.{s}",True,up=(0,-1,0))
    bone(f"hand.{s}",P3(x,d['wrist']),P3(x,d['ball']),f"forearm.{s}",True,up=(0,-1,0))
    bone(f"toes_front.{s}",P3(x,d['ball']),P3(x,d['toe']),f"hand.{s}",True,up=(0,0,1))
bpy.ops.object.mode_set(mode='OBJECT')
for b in arm.bones: b.use_deform = b.name!="root"
print(len(arm.bones), [b.name for b in arm.bones])
print("tail pts", [tuple(round(v,3) for v in p) for p in pts])
