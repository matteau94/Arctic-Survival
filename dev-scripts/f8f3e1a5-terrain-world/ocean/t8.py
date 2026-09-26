import sys, time, numpy as np
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
t0=time.perf_counter()
from terrain import ocean as O, config as C, noise as N
O._init(); print('init %.2f s'%(time.perf_counter()-t0))
def grid(cx,cy,res=257):
    i=np.arange(-1,res+1)/(res-1); return np.meshgrid((cx+i)*C.CHUNK_SIZE,(cy+i)*C.CHUNK_SIZE)
X,Y=grid(76,29)
ref=min((lambda t0: (N.perlin(X,Y,1,1e-4), time.perf_counter()-t0)[1])(time.perf_counter()) for _ in range(5))
print('reference: one noise.perlin on 259x259 = %.1f ms'%(ref*1e3))
cold=[]; warm=[]
for dx in range(-2,3):
    for dy in range(-2,3):
        X,Y=grid(76+dx,29+dy)
        O._CACHE.clear(); t0=time.perf_counter(); b,l=O.continent(X,Y); O.coast(X,Y,b,l); cold.append(time.perf_counter()-t0)
        ts=[]
        for k in range(3):
            O._CACHE.clear(); t0=time.perf_counter(); b,l=O.continent(X,Y); O.coast(X,Y,b,l); ts.append(time.perf_counter()-t0)
        warm.append(min(ts))
cold=np.array(cold); warm=np.array(warm)
print('5x5 around spawn: cold(first, incl. fjord traces) mean %.3f max %.3f | warm mean %.3f max %.3f s'%(cold.mean(),cold.max(),warm.mean(),warm.max()))
print('in perlin-units: warm mean %.1f max %.1f, cold max %.1f'%(warm.mean()/ref, warm.max()/ref, cold.max()/ref))
for lab,(cx,cy) in [('inland',(0,0)),('open sea',(140,10))]:
    X,Y=grid(cx,cy); ts=[]
    for k in range(3):
        O._CACHE.clear(); t0=time.perf_counter(); b,l=O.continent(X,Y); O.coast(X,Y,b,l); ts.append(time.perf_counter()-t0)
    print(lab, '%.3f s (%.1f perlin)'%(min(ts), min(ts)/ref))
