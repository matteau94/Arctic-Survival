import sys, time, numpy as np
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
from terrain import config as C, ocean, valleys, world
sp = C.SPAWN
print("spawn", sp, "s=", ocean.coast_distance(np.array([sp[0]]), np.array([sp[1]])))
t=time.time(); cs = ocean.find_coastal_spawn(); print("coastal spawn", cs, time.time()-t)
for p in (sp, cs):
    if p is None: continue
    t = np.arange(-20000, 20001, 250.0)
    X, Y = np.meshgrid(p[0]+t, p[1]+t)
    v = valleys.valley_info(X, Y)
    s = ocean.coast_distance(X, Y)
    print("pt", p, "min dist_major", v['dist_major'].min(), "min dist_minor", v['dist_minor'].min(),
          "floor_major range", v['floor_major'].min(), v['floor_major'].max(), "s range", s.min(), s.max())
    t0=time.time(); ctx = world.sample_chunk(*world.chunk_of(*p), 0); print("sample_chunk", time.time()-t0)
