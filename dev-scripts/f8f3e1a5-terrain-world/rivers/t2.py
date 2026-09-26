import sys, time, numpy as np
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
from terrain import config as C, ocean, valleys, world, rivers as R, noise as N
CS = (1966439.4553306517, 735875.7821322607)
cx, cy = world.chunk_of(*CS)
for dx in range(3):
    ctx = world.sample_chunk(cx+dx, cy, 0)    # warms valley cache for this grid
    h = ctx.H
    R._CACHE.clear()
    t = time.perf_counter(); lk = R._lakes_in(ctx.X.min(), ctx.X.max(), ctx.Y.min(), ctx.Y.max()); tl = time.perf_counter()-t
    R._CACHE.clear()
    t = time.perf_counter(); v = valleys.valley_info(ctx.X, ctx.Y); tv = time.perf_counter()-t
    t = time.perf_counter(); s = ocean.coast_distance(ctx.X, ctx.Y); ts = time.perf_counter()-t
    t = time.perf_counter(); out = R.carve(ctx.X, ctx.Y, h, ctx.land); tc = time.perf_counter()-t
    t = time.perf_counter(); p = N.perlin(ctx.X, ctx.Y, 5, 1/3000.); tp = time.perf_counter()-t
    print(f"chunk {cx+dx}: lakes(cold) {tl:.3f} valley_info(hit) {tv:.4f} coast_dist {ts:.4f} carve(warm lakes) {tc:.3f} one perlin {tp:.4f}")
