import sys, time, numpy as np
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
from terrain import config as C, ocean, valleys, world, rivers as R
import terrain.rivers as RM
# time rivers.carve inside the pipeline
orig = RM.carve; T = []
def timed(*a):
    t = time.perf_counter(); r = orig(*a); T.append(time.perf_counter() - t); return r
world.rivers.carve = timed
CS = (1966439.4553306517, 735875.7821322607)
for name, p in (("coastal", CS), ("spawn", C.SPAWN)):
    cx, cy = world.chunk_of(*p)
    for lod in (0,):
        for k in range(2):
            T.clear(); t0 = time.perf_counter(); ctx = world.sample_chunk(cx, cy, lod); tt = time.perf_counter() - t0
            print(name, "chunk", cx, cy, "lod", lod, "carve %.3fs total %.3fs" % (T[0], tt))
    F = R._fields(ctx.X, ctx.Y)
    t = time.perf_counter(); F = R._fields(ctx.X+0.0, ctx.Y+1e-9); print(" raw _fields (uncached valley_info?) %.3f" % (time.perf_counter()-t))
    print(" max hw %.1f, trib max %.1f, lakes %d, river verts %d" % (F['hw'].max(), F['tw'].max(), len(F['lakes']),
          ((np.abs(F['sd']) < F['hw']) ).sum()))
