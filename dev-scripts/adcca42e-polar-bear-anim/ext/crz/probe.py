import numpy as np
d=np.load('dump2.npz'); Q=d['Q'];J=d['J'];lp=d['lp'];ls=d['ls'];lt=d['lt'];lz=d['lz']
import pickle; nbr=pickle.load(open('../nbr.pkl','rb'))
N=np.zeros_like(Q)
for s,t in zip(ls,lt):
    vs=lp[s:s+t]; c=Q[vs]; fn=np.zeros(3)
    for k in range(t): fn+=np.cross(c[k],c[(k+1)%t])
    N[vs]+=fn
N/=np.maximum(np.linalg.norm(N,axis=1,keepdims=True),1e-12)
D=Q[:,2]-lz
def outdir(p):
    v=np.array([p[0],p[1]+7.0]); return v/max(np.linalg.norm(v),1e-9)
cnt=0
for i in range(len(Q)):
    x,y,z=Q[i]
    if not(-7.9<y<-6.62 and abs(x)<1.1 and abs(D[i])<0.012): continue
    up=J[i]<0.5; s=1 if up else -1
    walls=[j for j in nbr[i] if (J[j]<0.5)==up and s*D[j]>0.02 and np.dot(N[j][:2],outdir(Q[j]))>0.5]
    if walls and x>=0:
        cnt+=1
        print('%s c=(%.3f,%.3f) n=(%.2f,%.2f,%.2f) walls:'%('U' if up else 'L',x,y,*N[i]),' '.join('d%.3f dx%+.3f'%(s*D[j],np.dot(Q[j][:2]-Q[i][:2],outdir(Q[i]))) for j in walls))
print(cnt)
