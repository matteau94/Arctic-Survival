"""Full-frame, real-mesh locomotion QA; never saves the scene.
Run after human_anim_locomotion.py in background Blender. Optional LOCO_REPORT env path.
"""
import bpy, json, os
import numpy as np
from mathutils import Vector
arm=bpy.data.objects['HumanRig']; ob=bpy.data.objects['Human']; sc=bpy.context.scene
names={g.index:g.name for g in ob.vertex_groups}
pts=[]
for sd in ('L','R'):
    a=arm.data.bones['foot.'+sd].head_local; b=arm.data.bones['toe.'+sd].head_local
    fw=b-a; fw.z=0; fw.normalize()
    for bn,p,label in [('foot.'+sd,Vector((a.x,a.y,0))-fw*.05,'heel'),('toe.'+sd,Vector((b.x,b.y,0)),'ball'),('toe.'+sd,Vector((b.x,b.y,0))+fw*.06,'tip')]:
        pts.append((bn,arm.data.bones[bn].matrix_local.inverted()@p,label+' '+sd))
def sample(name,mesh=True):
    act=bpy.data.actions[name];arm.animation_data.action=act
    if act.slots:arm.animation_data.action_slot=act.slots[0]
    n=int(act.frame_range[1]); points=[]; worst=None; first=None; closure=0
    previous=None; actual_slip={'mm_per_frame':0}; speed=act.get('speed_mps',0)
    for f in range(n+1):
        sc.frame_set(f)
        points.append([list(arm.matrix_world@arm.pose.bones[bn].matrix@p) for bn,p,_ in pts])
        if not mesh:continue
        eo=ob.evaluated_get(bpy.context.evaluated_depsgraph_get()); em=eo.to_mesh()
        assert len(em.vertices)==len(ob.data.vertices), 'Topology changed: vertex IDs invalid'
        co=np.empty(len(em.vertices)*3);em.vertices.foreach_get('co',co);co=co.reshape(-1,3)
        co=co@np.array(eo.matrix_world)[:3,:3].T+np.array(eo.matrix_world)[:3,3]
        if previous is not None:
            ids=np.flatnonzero((co[:,2]<.005)&(previous[:,2]<.005))
            if len(ids):
                delta=co[ids,:2]-previous[ids,:2]-np.array([0,speed/60])
                slip=np.linalg.norm(delta,axis=1)*1000; j=int(slip.argmax())
                if slip[j]>actual_slip['mm_per_frame']:
                    actual_slip=dict(mm_per_frame=float(slip[j]),frame=f-1,vertex=int(ids[j]))
        previous=co.copy()
        if f==0:first=co.copy()
        if f==n:closure=float(np.max(np.linalg.norm(co-first,axis=1)))
        k=int(co[:,2].argmin()); z=float(co[k,2]*1000)
        if worst is None or z<worst['z_mm']:
            v=ob.data.vertices[k]; wg=sorted([(names[g.group],g.weight) for g in v.groups],key=lambda a:-a[1])
            sd=wg[0][0][-1]; u=(f/n-(.5 if sd=='R' else 0))%1
            worst=dict(frame=f,z_mm=z,vertex=k,rest=list(v.co),weights=wg,phase=u)
        eo.to_mesh_clear()
    return np.array(points),worst,closure,actual_slip
base=sample('Human_Idle',False)[0][:,:,2].min(axis=0)
report={'vertices':len(ob.data.vertices),'clips':{}}
for name,D in [('Human_Walk',.62),('Human_Run',.28),('Human_CrouchWalk',.66)]:
    P,w,c,actual=sample(name);act=bpy.data.actions[name];n=len(P)-1;v=act['speed_mps']; best={'mm_per_frame':0}
    for j,(_,_,label) in enumerate(pts):
        pl=P[:,j,2]<base[j]+.005
        for f in np.flatnonzero(pl[1:]&pl[:-1]):
            d=P[f+1,j]-P[f,j]-np.array([0,v/60,0]);slip=float(np.linalg.norm(d[:2])*1000)
            if slip>best['mm_per_frame']:best=dict(mm_per_frame=slip,frame=int(f),contact=label,heights_mm=(P[f:f+2,j,2]*1000).tolist(),phase=(float(f)/n-(.5 if label.endswith('R') else 0))%1)
    w['contact_phase']='stance' if w['phase']<D else 'swing'
    report['clips'][name]=dict(frames=n,speed=v,worst_mesh=w,proxy_slip=best,mesh_contact_slip=actual,mesh_loop_error_mm=c*1000)
print(json.dumps(report,indent=2))
with open(os.environ.get('LOCO_REPORT','dev-scripts/3c568333-human/loco/diagnostic.json'),'w') as f:json.dump(report,f,indent=2)
