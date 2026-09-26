import sys, time, numpy as np, cProfile, pstats
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
from terrain import config as C, ocean, valleys, world, rivers as R
CS = (1966439.4553306517, 735875.7821322607)
cx, cy = world.chunk_of(*CS)
res=257; i = np.arange(-1, res + 1, dtype=np.float64); t = i / (res - 1)
Xe, Ye = np.meshgrid((cx + t) * C.CHUNK_SIZE, (cy + t) * C.CHUNK_SIZE)
He, Le = world.height(Xe, Ye, return_land=True)
for k in range(8):
    R._CACHE.clear()
    t0=time.perf_counter(); R.carve(Xe, Ye, He, Le); print("carve warm", time.perf_counter()-t0)
R._CACHE.clear()
cProfile.run("R.carve(Xe, Ye, He, Le)", "p.out")
pstats.Stats("p.out").sort_stats("cumtime").print_stats(15)
import os; print("cpus", os.cpu_count())
