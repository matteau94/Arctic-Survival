import sys, time; sys.path.insert(0, '.')
import fake; fake.install()
import numpy as np
from terrain import valleys as V, world as W, ocean, mountains, network as NW, config as C
t=np.linspace(0,C.CHUNK_SIZE,257); X,Y=np.meshgrid(t+C.SPAWN[0]-12000,t+C.SPAWN[1]-12000)
b,l = ocean.continent(X,Y); h0 = b + mountains.height(X,Y,l)
V.carve(X,Y,h0,l)
ts=[]
for i in range(5):
    V._CACHE.clear(); t0=time.perf_counter(); V.carve(X,Y,h0,l); ts.append(time.perf_counter()-t0)
print("carve 257^2 cold: min %.4f mean %.4f"%(min(ts), np.mean(ts)))
import cProfile, pstats
V._CACHE.clear(); cProfile.run('V.carve(X,Y,h0,l)','prof.out'); pstats.Stats('prof.out').sort_stats('cumtime').print_stats(12)
