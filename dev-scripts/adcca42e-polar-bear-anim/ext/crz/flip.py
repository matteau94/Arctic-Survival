import numpy as np
a=np.load('dump2.npz'); b=np.load('after.npz')
lp=a['lp'];ls=a['ls'];lt=a['lt']
T=[]
for s,t in zip(ls,lt):
    for k in range(1,t-1): T.append((lp[s],lp[s+k],lp[s+k+1]))
T=np.array(T)
def fn(Q): return np.cross(Q[T[:,1]]-Q[T[:,0]],Q[T[:,2]]-Q[T[:,0]])
A=fn(a['Q']);B=fn(b['Q'])
dot=(A*B).sum(1)/np.maximum(np.linalg.norm(A,axis=1)*np.linalg.norm(B,axis=1),1e-15)
disp=np.linalg.norm(b['Q']-a['Q'],axis=1)
print('moved verts',(disp>1e-5).sum(),'max disp',disp.max())
bad=np.nonzero(dot<0.3)[0]
print('faces rotated >72deg:',len(bad))
for f in bad[:20]: print(np.round(b['Q'][T[f]].mean(0),3), round(dot[f],2), round(np.linalg.norm(A[f])/2,5))
