import sys, time, numpy as np
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
from terrain import ocean as O, config as C
O._init()
t0=time.perf_counter(); sp=O.find_coastal_spawn(); print('spawn', sp, 'time', time.perf_counter()-t0)
print('s at spawn', O.coast_distance(np.array([sp[0]]),np.array([sp[1]])))
def grid(cx,cy,res=257):
    i=np.arange(-1,res+1)/(res-1); return np.meshgrid((cx+i)*C.CHUNK_SIZE,(cy+i)*C.CHUNK_SIZE)
def timeit(cx,cy,label):
    X,Y=grid(cx,cy)
    ts=[]
    for k in range(4):
        O._CACHE.clear()
        t0=time.perf_counter(); b,l=O.continent(X,Y); h=O.coast(X,Y,b,l); ts.append(time.perf_counter()-t0)
    print(label,(cx,cy),'best %.3f med %.3f'%(min(ts),np.median(ts)),'hmin %.1f hmax %.1f'%(h.min(),h.max()),'sea frac %.2f'%(h<0).mean())
    return X,Y,h
cx,cy=int(sp[0]//C.CHUNK_SIZE),int(sp[1]//C.CHUNK_SIZE)
for dx in range(-2,3):
    for dy in range(-2,3):
        timeit(cx+dx,cy+dy,'near-spawn')
timeit(0,0,'inland')
timeit(140,10,'open sea')
import cProfile, pstats
X,Y=grid(cx,cy)
def run():
    O._CACHE.clear(); b,l=O.continent(X,Y); O.coast(X,Y,b,l)
cProfile.run('run()','prof.out'); pstats.Stats('prof.out').sort_stats('cumtime').print_stats(14)
