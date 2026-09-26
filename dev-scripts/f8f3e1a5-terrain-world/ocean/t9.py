import sys, time, numpy as np, cProfile, pstats
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
from terrain import ocean as O, config as C
cProfile.run('O._init()','p0.out'); pstats.Stats('p0.out').sort_stats('cumtime').print_stats(8)
def grid(cx,cy,res=257):
    i=np.arange(-1,res+1)/(res-1); return np.meshgrid((cx+i)*C.CHUNK_SIZE,(cy+i)*C.CHUNK_SIZE)
worst=None
for dx in range(-2,3):
    for dy in range(-2,3):
        X,Y=grid(76+dx,29+dy); O._CACHE.clear(); b,l=O.continent(X,Y); O.coast(X,Y,b,l)
        O._CACHE.clear(); t0=time.perf_counter(); b,l=O.continent(X,Y); O.coast(X,Y,b,l); t=time.perf_counter()-t0
        if worst is None or t>worst[0]: worst=(t,dx,dy)
print('worst', worst)
X,Y=grid(76+worst[1],29+worst[2])
def run():
    O._CACHE.clear(); b,l=O.continent(X,Y); O.coast(X,Y,b,l)
cProfile.run('run()','p1.out'); pstats.Stats('p1.out').sort_stats('tottime').print_stats(14)
