import sys, time, numpy as np
sys.path.insert(0, r"C:\Users\leosp\Documents\Blender\Artic-Survival")
from terrain import mountains as M, ocean, world, noise as N
from terrain.config import SPAWN, CHUNK_SIZE
cx,cy=world.chunk_of(*SPAWN)
def tmin(f,n=5):
    b=1e9
    for _ in range(n):
        t0=time.perf_counter(); f(); b=min(b,time.perf_counter()-t0)
    return b
res=[]; refs=[]
for j in range(cy-2,cy+3):
  for i in range(cx-2,cx+3):
    tt=np.linspace(0,CHUNK_SIZE,257); X,Y=np.meshgrid(i*CHUNK_SIZE+tt,j*CHUNK_SIZE+tt); base,land=ocean.continent(X,Y)
    res.append(tmin(lambda: M.height(X,Y,land),3)); refs.append(tmin(lambda: N.perlin(X,Y,1,1/5000),3))
res=np.array(res); refs=np.array(refs)
print(f"height min-of-3 per chunk: mean {res.mean()*1e3:.1f} max {res.max()*1e3:.1f} ms | noise.perlin ref {refs.mean()*1e3:.1f} ms (22.5 unloaded) | normalised mean {np.mean(res/refs)*22.5:.1f} max {np.max(res/refs)*22.5:.1f} ms")
