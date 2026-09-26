import numpy as np
d=np.load('dump2.npz'); Q=d['Q'];J=d['J'];lp=d['lp'];ls=d['ls'];lt=d['lt'];lz=d['lz']
U=len(Q)
def normals(Q):
    N=np.zeros_like(Q)
    for s,t in zip(ls,lt):
        vs=lp[s:s+t]
        if len(set(vs))<3: continue
        c=Q[vs]; fn=np.zeros(3)
        for k in range(t): fn+=np.cross(c[k],c[(k+1)%t])
        N[vs]+=fn*0.5
    return N/np.maximum(np.linalg.norm(N,axis=1,keepdims=True),1e-12)
N=normals(Q)
D=Q[:,2]-lz
C=np.array([0,-6.9])
rad=Q[:,:2]-C; r=np.linalg.norm(rad,axis=1); th=np.arctan2(rad[:,0],-rad[:,1])
band=(Q[:,1]>-7.95)&(Q[:,1]<-6.55)&(np.abs(Q[:,0])<1.2)&(np.abs(D)<0.3)
outdot=(N[:,0]*rad[:,0]+N[:,1]*rad[:,1])/np.maximum(r,1e-9)
bins=np.linspace(-1.6,1.6,33)
for a,b in zip(bins,bins[1:]):
    s=np.nonzero(band&(th>=a)&(th<b))[0]
    if len(s)==0: continue
    rm=r[s].max()
    o=s[(r[s]>rm-0.1)]
    print('th %.2f rmax %.3f  n=%d outer:'%((a+b)/2,rm,len(s)), ' '.join('%+.3f(%.2f,J%.0f,o%.1f)'%(D[i],rm-r[i],J[i],outdot[i]) for i in o[np.argsort(-D[o])]))
