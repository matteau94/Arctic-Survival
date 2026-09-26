import sys, time, numpy as np
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
from terrain import config as C, ocean, valleys, world, rivers as R
import terrain.rivers as RM
orig_c, orig_s = RM.carve, RM.surface; T = {}
def wrap(f, n):
    def g(*a):
        t = time.perf_counter(); r = f(*a); T.setdefault(n, []).append(time.perf_counter() - t); return r
    return g
world.rivers.carve = wrap(orig_c, 'carve'); world.rivers.surface = wrap(orig_s, 'surface')
vi = valleys.valley_info
CS = (1966439.4553306517, 735875.7821322607)
cx, cy = world.chunk_of(*CS)
for dx in range(-2, 3):
    for dy in (0, 1):
        T.clear()
        res = 257
        i = np.arange(-1, res + 1, dtype=np.float64); t = i / (res - 1)
        Xe, Ye = np.meshgrid((cx+dx + t) * C.CHUNK_SIZE, (cy+dy + t) * C.CHUNK_SIZE)
        t0 = time.perf_counter(); He, Le = world.height(Xe, Ye, return_land=True); th = time.perf_counter()-t0
        t0 = time.perf_counter(); m = world.surface(Xe, Ye, He, Le, C.CHUNK_SIZE/256); ts = time.perf_counter()-t0
        print(f"chunk {cx+dx},{cy+dy}: height {th:.2f}s surface {ts:.2f}s | rivers.carve {T['carve'][0]*1000:.0f} ms, rivers.surface {T['surface'][0]*1000:.0f} ms, ice verts {(m['ice']>0.5).sum()}")
