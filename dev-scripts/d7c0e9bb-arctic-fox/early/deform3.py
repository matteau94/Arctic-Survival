import bpy, bmesh, numpy as np, math
fox=bpy.data.objects["ArcticFox"]; me=fox.data
# keep an untouched reference copy (hidden)
ref=bpy.data.objects.get("RedFox_Reference")
if ref is None:
    ref=fox.copy(); ref.data=me.copy(); ref.name="RedFox_Reference"; ref.data.name="RedFox_Reference"
    rc=bpy.data.collections.get("Reference") or bpy.data.collections.new("Reference")
    if rc.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(rc)
    rc.objects.link(ref); rc.hide_render=True; ref.hide_set(True); ref.hide_render=True
    for c in list(ref.users_collection):
        if c!=rc: c.objects.unlink(ref)
    SRC=me
else:
    SRC=ref.data   # always rebuild from the pristine copy
N=len(SRC.vertices)
co=np.empty(N*3); SRC.vertices.foreach_get("co",co); co=co.reshape(-1,3)
nr=np.empty(N*3); SRC.vertices.foreach_get("normal",nr); nr=nr.reshape(-1,3)
# islands
bm=bmesh.new(); bm.from_mesh(SRC); bm.verts.ensure_lookup_table()
isl=np.full(N,-1); sizes=[]; k=0
for v in bm.verts:
    if isl[v.index]>=0: continue
    st=[v]; isl[v.index]=k; n=0
    while st:
        a=st.pop(); n+=1
        for e in a.link_edges:
            b=e.other_vert(a)
            if isl[b.index]<0: isl[b.index]=k; st.append(b)
    sizes.append(n); k+=1
sizes=np.array(sizes)
cent=np.array([co[isl==i].mean(0) for i in range(k)])
def ids(cond): return [i for i in range(k) if cond(sizes[i],cent[i])]
BODY=ids(lambda s,c: s==1493); HEAD=ids(lambda s,c: s==1358)
LEGS=ids(lambda s,c: s in (1012,736)); TAIL=ids(lambda s,c: s==782)
EARS=ids(lambda s,c: s==319); PADS=ids(lambda s,c: s==156)
role=np.zeros(N,int)  # 0 other,1 body,2 head,3 leg,4 tail,5 ear
for r,L in ((1,BODY),(2,HEAD),(3,LEGS),(4,TAIL),(5,EARS)):
    role[np.isin(isl,L)]=r
def sst(e0,e1,x):
    t=np.clip((x-e0)/(e1-e0),0,1); return t*t*(3-2*t)
def g(p,c,r): return np.exp(-np.sum((p-np.array(c))**2,1)/(r*r))
new=co.copy()
# --- 1) inflate (fluffy winter coat) as ONE smooth spatial field so overlapping shells stay flush
x,y,z=co[:,0],co[:,1],co[:,2]
P=np.c_[np.abs(x),y,z]
amt=0.011+0.012*g(co,(0,-0.28,0.36),0.075)+0.008*g(P,(0.052,-0.33,0.38),0.035)
amt+=0.012*sst(0.22,0.36,y)*sst(0.33,0.25,z)          # bushier tail
amt-=0.002*sst(0.15,0.05,z)                             # slightly less on lower legs
eye=g(P,(0.03,-0.381,0.409),0.024)
amt*=(1-eye)*sst(-0.405,-0.365,y)                       # keep eyes, nose, lips as they are
amt*=np.where((z<0.03)&(nr[:,2]<0),sst(0.004,0.03,z),1) # don't push soles through the ground
amt*=np.where(nr[:,2]<-0.5,np.where(z>0.15,0.7,1.0),1.0) # belly a bit less
for i in EARS:                                          # ears: match head at the base, thin above
    m=isl==i; zb=co[m,2].min()
    amt[m]=amt[m]*sst(zb+0.022,zb+0.004,co[m,2])+0.0015*sst(zb+0.004,zb+0.022,co[m,2])
amt*=1-0.7*sst(0.425,0.46,z)*sst(-0.24,-0.28,y)   # thin coat on top of skull around the ears
for i in EARS:   # hold the head still around each ear socket so the ear base keeps covering the opening
    m=isl==i; Pm=co[m]; eb=Pm[Pm[:,2]<Pm[:,2].min()+0.02].mean(0)
    amt*=1-0.97*g(co,eb,0.034)
amt[np.isin(isl,PADS)]=0
disp=nr*amt[:,None]
# ear skirts copy the skull displacement underneath them (their own normals point along the ear)
from mathutils import kdtree
hv=np.where(np.isin(isl,HEAD))[0]; kd=kdtree.KDTree(len(hv))
for j,vi in enumerate(hv): kd.insert(co[vi],j)
kd.balance()
for i in EARS:
    for vi in np.where(isl==i)[0]:
        zb=co[isl==i,2].min() if False else None
    m=np.where(isl==i)[0]; zb=co[m,2].min()
    for vi in m:
        w=float(sst(zb+0.02,zb+0.006,co[vi,2]))
        if w<=0: continue
        _,j,_=kd.find(co[vi]); disp[vi]=disp[vi]*(1-w)+disp[hv[j]]*w
new+=disp
# --- 2) ears: shorter + blunter, scaled about their base
for i in EARS:
    m=isl==i; P=new[m]
    base=P[P[:,2]<P[:,2].min()+0.018].mean(0)
    tip=P[P[:,2].argmax()]; ax=(tip-base); L=np.linalg.norm(ax); ax/=L
    d=P-base; a=d@ax; perp=d-np.outer(a,ax); tt=np.clip(a/L,0,1)
    ga=np.linspace(-0.05,0.15,2001); sl=1-0.42*sst(0.016,0.034,ga)
    ia=np.concatenate([[0],np.cumsum((sl[1:]+sl[:-1])/2*np.diff(ga))]); ia-=np.interp(0,ga,ia)
    a2=np.interp(a,ga,ia); w=sst(0.016,0.04,a)
    new[m]=base+np.outer(a2,ax)+perp*(1.0+0.16*tt*w)[:,None]
# --- 3) shorter muzzle (compress in front of the eyes)
Ym=-0.392
gy=np.linspace(-0.6,0.6,4001); slope=1-0.28*sst(Ym+0.012,Ym-0.012,gy)
integ=np.concatenate([[0],np.cumsum((slope[1:]+slope[:-1])/2*np.diff(gy))])
integ-=np.interp(0,gy,integ)
head_zone=(new[:,2]>0.28)&(new[:,1]<-0.3)
new[head_zone,1]=np.interp(new[head_zone,1],gy,integ)
# --- 4) shorter legs: compress everything below the belly, drop the rest
kL=0.8
gz=np.linspace(-0.1,1.0,4001); sl=kL+(1-kL)*sst(0.16,0.25,gz)
iz=np.concatenate([[0],np.cumsum((sl[1:]+sl[:-1])/2*np.diff(gz))]); iz-=np.interp(0,gz,iz)
drop=0.6-np.interp(0.6,gz,iz)
tl=role==4
new[~tl,2]=np.interp(new[~tl,2],gz,iz)
# tail: rigid drop + lift ~12 degrees about its root
piv=np.array([0,0.19,0.315]); th=math.radians(12)
d=new[tl]-piv; yy=d[:,1]*math.cos(th)-d[:,2]*math.sin(th); zz=d[:,1]*math.sin(th)+d[:,2]*math.cos(th)
new[tl]=piv+np.c_[d[:,0],yy,zz]; new[tl,2]-=drop
new[:,2]-=new[:,2].min()
me.vertices.foreach_set("co",new.ravel()); me.update()
print("drop",round(drop,4),"islands",k,"roles",np.bincount(role),"dims",(new.max(0)-new.min(0)).round(3))
