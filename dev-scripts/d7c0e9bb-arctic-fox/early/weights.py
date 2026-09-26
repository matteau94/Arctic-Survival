import bpy, numpy as np
fox=bpy.data.objects["ArcticFox"]; rig=bpy.data.objects["FoxRig"]; me=fox.data; N=len(me.vertices)
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
D=segdist(co)
allow=np.zeros((N,B),bool)
def A(mask,bnames):
    cols=[idx[n] for n in bnames]; allow[np.ix_(np.where(mask)[0],cols)]=True
x=co[:,0]; side=np.where(x>0.012,'L',np.where(x<-0.012,'R','C'))
roleisl={}
for i in range(K):
    s=sizes[i]; c=cent[i]
    if s==1493: roleisl[i]='body'
    elif s==1358: roleisl[i]='head'
    elif s==319: roleisl[i]='ear'
    elif s==782: roleisl[i]='tail'
    elif s in (1012,): roleisl[i]='hindleg'
    elif s in (736,): roleisl[i]='frontleg'
    elif c[2]<0.06: roleisl[i]='paw'
    elif c[1]<-0.28 and c[2]>0.28: roleisl[i]='headpart'
    else: roleisl[i]='misc'
role=np.array([roleisl[i] for i in isl])
spine=['hips','spine1','spine2','chest','neck1','neck2']
for s in ('L','R'):
    m=(role=='body')&(side==s); A(m,spine+['head',f'scapula.{s}',f'upperarm.{s}',f'thigh.{s}'])
    m=(role=='frontleg')&(side==s); A(m,['chest','spine2',f'scapula.{s}',f'upperarm.{s}',f'forearm.{s}',f'hand.{s}',f'toes_front.{s}'])
    m=(role=='hindleg')&(side==s); A(m,['hips','spine1',f'thigh.{s}',f'shin.{s}',f'hock.{s}',f'toes_hind.{s}'])
    m=(role=='ear')&(side==s); A(m,['head',f'ear.{s}'])
A((role=='body')&(side=='C'),spine+['head'])
for r in ('frontleg','hindleg','ear'):   # centre-line stragglers of side parts
    m=(role==r)&(side=='C'); allow[m]=allow[m] | False
A(role=='head',['head','neck2','neck1'])
A(role=='tail',['hips']+[f'tail{k}' for k in range(1,7)])
W=np.where(allow,1.0/np.maximum(D,0.004)**5,0.0)
# side parts with centre-line verts (rare): fall back to nearest of their family
none=W.sum(1)==0
# rigid pieces: whole island -> single nearest bone (paws: that leg's paw bones; head parts: head)
for i in range(K):
    r=roleisl[i]
    if r not in ('paw','headpart','misc') and not none[isl==i].any(): continue
    m=isl==i; c=cent[i]
    if r=='headpart': j=idx['head']
    else:
        d=segdist(c[None])[0]
        if r=='paw':
            s='L' if c[0]>0 else 'R'; cand=[f'hand.{s}',f'toes_front.{s}',f'hock.{s}',f'toes_hind.{s}']
            j=min((idx[n] for n in cand), key=lambda q:d[q])
        else: j=int(d.argmin())
    W[m]=0; W[m,j]=1
W/=W.sum(1,keepdims=True)
# smooth along edges (within islands) a few times, rigid pieces stay rigid
ev=np.empty(len(me.edges)*2,int); me.edges.foreach_get("vertices",ev); ev=ev.reshape(-1,2)
rigid=np.isin(role,['paw','headpart','misc'])
deg=np.bincount(ev.ravel(),minlength=N).astype(float)
for _ in range(6):
    S=np.zeros_like(W); np.add.at(S,ev[:,0],W[ev[:,1]]); np.add.at(S,ev[:,1],W[ev[:,0]])
    avg=np.where(deg[:,None]>0,S/np.maximum(deg,1)[:,None],W)
    Wn=0.5*W+0.5*avg; Wn[~allow & ~rigid[:,None]]=0; Wn[rigid]=W[rigid]
    W=Wn/np.maximum(Wn.sum(1,keepdims=True),1e-9)
# keep 4 strongest
o=np.argsort(-W,1); W2=np.zeros_like(W); r_=np.arange(N)[:,None]; W2[r_,o[:,:4]]=W[r_,o[:,:4]]
W=W2/W2.sum(1,keepdims=True)
fox.vertex_groups.clear()
for j,n in enumerate(names):
    vg=fox.vertex_groups.new(name=n); nz=np.where(W[:,j]>0.001)[0]
    for w in np.unique(np.round(W[nz,j],3)):
        sel=nz[np.round(W[nz,j],3)==w]; vg.add(sel.tolist(), float(w), 'REPLACE')
for m in list(fox.modifiers):
    if m.type=='ARMATURE': fox.modifiers.remove(m)
am=fox.modifiers.new("Armature",'ARMATURE'); am.object=rig
fox.parent=rig
print("roles",{r:int((role==r).sum()) for r in set(role)}, "unweighted", int((W.sum(1)==0).sum()))
