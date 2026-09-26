import bpy, numpy as np
from mathutils import kdtree
rig=bpy.data.objects["FoxRig"]
ad=rig.animation_data; keep=ad.action if ad else None
if ad: ad.action=None
for pb in rig.pose.bones: pb.matrix_basis=__import__("mathutils").Matrix()
fox=bpy.data.objects["ArcticFox"]; me=fox.data; N=len(me.vertices)
co=np.empty(N*3); me.vertices.foreach_get("co",co); co=co.reshape(-1,3)
isl=np.load(r"C:/Users/leosp/AppData/Local/Temp/foxwork/isl.npy"); sizes=np.bincount(isl); K=len(sizes)
cent=np.array([co[isl==i].mean(0) for i in range(K)])
bones=[b for b in rig.data.bones if b.use_deform]; names=[b.name for b in bones]; B=len(bones); idx={n:i for i,n in enumerate(names)}
H=np.array([b.head_local[:] for b in bones]); T=np.array([b.tail_local[:] for b in bones])
def segdist(P):
    D=np.empty((len(P),B))
    for j in range(B):
        ab=T[j]-H[j]; t=np.clip(((P-H[j])@ab)/(ab@ab),0,1); D[:,j]=np.linalg.norm(P-(H[j]+t[:,None]*ab),axis=1)
    return D
def sst(e0,e1,v):
    t=np.clip((v-e0)/(e1-e0),0,1); return t*t*(3-2*t)
# one shared spatial field for every shell (body, head, legs, tail) so overlapping pieces move together
D=segdist(co)
ears=[idx['ear.L'],idx['ear.R']]
tailb=[idx[f'tail{k}'] for k in range(2,7)]
W=1.0/(D**2+0.011**2)**2.5
W[:,ears]=0
# tail bones beyond tail1 only affect points actually behind the rump
behind=sst(0.20,0.24,co[:,1])
W[:,tailb]*=behind[:,None]
# legs never take the other side's leg bones
for s,o in (('L','R'),('R','L')):
    other=[idx[n] for n in names if n.endswith('.'+o) and not n.startswith('ear')]
    W[np.ix_(co[:,0]>0.004 if s=='L' else co[:,0]<-0.004, other)]=0
# keep head/neck off the legs and legs off the head
legcols=[idx[n] for n in names if n.split('.')[0] in ('scapula','upperarm','forearm','hand','toes_front','thigh','shin','hock','toes_hind')]
W[np.ix_(co[:,1]<-0.27, legcols)]=0
# tail and rump never follow the legs
tailisl=np.isin(isl,np.where(sizes==782)[0])
W[np.ix_(tailisl | ((co[:,1]>0.215)&(co[:,2]>0.17)), legcols)]=0
W[np.ix_(~tailisl & (co[:,1]<0.2), tailb)]=0
# joints blend into the torso: upper thigh/upper arm and tail root lean on hips/scapula so shells don't lift apart
zz=co[:,2]; yy=co[:,1]
fade=np.array([sst(0.30,0.19,v) for v in zz])
hfade=np.array([sst(0.26,0.13,v) for v in zz])
for n in ('upperarm.L','upperarm.R'): W[:,idx[n]]*=fade
for n in ('thigh.L','thigh.R'): W[:,idx[n]]*=hfade
tfade=np.array([sst(0.195,0.26,v) for v in yy])
for k in range(1,7): W[tailisl,idx[f'tail{k}']]*=tfade[tailisl]
W[tailisl,idx['hips']]+=1e-6
W/=W.sum(1,keepdims=True)
# ears: skirt follows head, flap follows ear bone
for i in np.where(sizes==319)[0]:
    m=np.where(isl==i)[0]; s='L' if cent[i][0]>0 else 'R'; b=rig.data.bones[f'ear.{s}']
    h=np.array(b.head_local[:]); ax=np.array(b.tail_local[:])-h; L=np.linalg.norm(ax); ax/=L
    e=sst(0.014,0.04,(co[m]-h)@ax)
    W[m]*= (1-e)[:,None]; W[m,idx[f'ear.{s}']]+=e
# leg-shell rims hug the body: near their open border, leg shells take the weights of the body skin beneath them
import bmesh as _bm
_b=_bm.new(); _b.from_mesh(me); _b.verts.ensure_lookup_table()
legisl=np.isin(sizes[isl],[1012,736])
bnd=np.array([v.index for v in _b.verts if legisl[v.index] and any(e.is_boundary for e in v.link_edges)])
kb=kdtree.KDTree(len(bnd))
for j,v in enumerate(bnd): kb.insert(co[v],j)
kb.balance()
bodyv=np.where(isl==np.where(sizes==1493)[0][0])[0]
kbody=kdtree.KDTree(len(bodyv))
for j,v in enumerate(bodyv): kbody.insert(co[v],j)
kbody.balance()
for v in np.where(legisl)[0]:
    if co[v,2]<0.14: continue
    _,_,dist=kb.find(co[v]); bl=sst(0.04,0.0,dist)
    if bl<=0: continue
    _,j,_=kbody.find(co[v]); W[v]=(1-bl)*W[v]+bl*W[bodyv[j]]
# small detached pieces (claws, pads, eyes, whiskers, teeth...) copy the weights of the nearest shell vertex
big=np.isin(sizes[isl],[1493,1358,1012,736,782,319])
bv=np.where(big)[0]; kd=kdtree.KDTree(len(bv))
for j,v in enumerate(bv): kd.insert(co[v],j)
kd.balance()
for i in range(K):
    if sizes[i] in (1493,1358,1012,736,782,319): continue
    m=np.where(isl==i)[0]
    _,j,_=kd.find(cent[i]); W[m]=W[bv[j]]      # rigid: whole piece uses one weight set
# keep 4 strongest
o=np.argsort(-W,1); W2=np.zeros_like(W); r_=np.arange(N)[:,None]; W2[r_,o[:,:4]]=W[r_,o[:,:4]]
W=W2/W2.sum(1,keepdims=True)
fox.vertex_groups.clear()
for j,n in enumerate(names):
    vg=fox.vertex_groups.new(name=n); nz=np.where(W[:,j]>0.002)[0]
    q=np.round(W[nz,j],3)
    for w in np.unique(q): vg.add(nz[q==w].tolist(), float(w), 'REPLACE')
print("ok", {n:int((W[:,idx[n]]>0.5).sum()) for n in names})
bpy.data.objects["FoxRig"].animation_data.action=keep
