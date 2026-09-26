import sys, time; sys.path.insert(0, '.')
import fake
USE_FAKE = '--real' not in sys.argv
if USE_FAKE: fake.install()
import numpy as np
from terrain import valleys as V, world as W, ocean, mountains, network as NW, config as C, noise as N
rng = np.random.default_rng(0)
# 1. lattice sd accuracy vs exact FD at points
P = rng.uniform(-1, 1, (2, 20000)) * 150e3 + np.array(C.SPAWN)[:, None]
def exact_sd(fn, X, Y, gmin, e=1.0):
    n = fn(X, Y)[1]; gx = (fn(X+e,Y)[1]-fn(X-e,Y)[1])/(2*e); gy=(fn(X,Y+e)[1]-fn(X,Y-e)[1])/(2*e)
    return n/np.maximum(np.hypot(gx,gy),gmin), n/ np.maximum(fn(X,Y)[0],1e-9)*0+fn(X,Y)[0]
info = V.valley_info(P[0], P[1])
for nm, fn, f, key in (("major", NW.major_distance, NW.MAJOR_FREQ, 'sdist_major'), ("minor", NW.minor_distance, NW.MINOR_FREQ, 'sdist_minor')):
    sd, dnet = exact_sd(fn, P[0], P[1], 0.25*f)
    near = np.abs(sd) < 5000
    err = np.abs(info[key]-sd)[near]
    rat = (dnet/np.maximum(np.abs(sd),1))[near & (np.abs(sd)>200)]
    print(f"{nm}: lattice-vs-exact |err| (d<5km) p50 {np.median(err):.2f} p99 {np.percentile(err,99):.2f} max {err.max():.1f} m;  network d / trueFD d p5..p95 {np.percentile(rat,5):.2f}..{np.percentile(rat,95):.2f}")
# 2. point vs chunk consistency + 3. seams
cx, cy = W.chunk_of(*C.SPAWN)
c0 = W.sample_chunk(cx, cy, 0); c1 = W.sample_chunk(cx+1, cy, 0); c2 = W.sample_chunk(cx, cy+1, 0); c3 = W.sample_chunk(cx+1, cy, 1)
print("seam E (lod0/lod0) max |dh|", np.abs(c0.H[:, -1]-c1.H[:, 0]).max())
print("seam N (lod0/lod0) max |dh|", np.abs(c0.H[-1, :]-c2.H[0, :]).max())
print("seam E (lod0/lod1 shared verts) max |dh|", np.abs(c0.H[::2, -1]-c3.H[:, 0]).max())
idx = rng.integers(0, 257, (2, 200))
hp = np.array([W.height(np.array([c0.X[i,j]]), np.array([c0.Y[i,j]]))[0] for i,j in idx.T])
print("single-point vs chunk max |dh|", np.abs(hp - c0.H[idx[0], idx[1]]).max())
# timing: carve only, cold cache, 257 / 129 / 65
for res in (257, 129, 65):
    t=np.linspace(0,C.CHUNK_SIZE,res); X,Y=np.meshgrid(t+cx*C.CHUNK_SIZE,t+cy*C.CHUNK_SIZE)
    b,l = ocean.continent(X,Y); h0=b+mountains.height(X,Y,l)
    ts=[]
    for _ in range(7):
        V._CACHE.clear(); t0=time.perf_counter(); V.carve(X,Y,h0,l); ts.append(time.perf_counter()-t0)
    print(f"carve {res}^2 cold: median {np.median(ts)*1000:.1f} ms min {min(ts)*1000:.1f} ms")
# 4. large-area stats
def stats(cx0, cy0, half, sp, tag, img=None):
    t = np.arange(-half, half+sp/2, sp); X, Y = np.meshgrid(t+cx0, t+cy0)
    b, l = ocean.continent(X, Y); h0 = b + mountains.height(X, Y, l)
    V._CACHE.clear(); h1 = V.carve(X, Y, h0, l); v = V.valley_info(X, Y)
    dep = h0 - h1
    onM = (v['dist_major'] < v['width_major']) & (l > 0.3)
    onm = (v['dist_minor'] < v['width_minor']) & (l > 0.3) & ~(v['dist_major'] < v['width_major'] + 3000)
    print(f"== {tag}: area {2*half/1e3:.0f} km @ {sp:.0f} m, land frac {np.mean(l>0):.2f}")
    for nm, m in (("major floor", onM), ("minor floor", onm)):
        if m.sum()==0: continue
        for lo, hi, rn in ((0, .2, 'plateau'), (.2, .7, 'foothill'), (.7, 1.01, 'mountain')):
            mm = m & (v['relief'] >= lo) & (v['relief'] < hi)
            if mm.sum() < 20: continue
            # local relief: depth relative to max carved-away terrain within the section: use h0 - floor
            print(f"  {nm:11s} {rn:9s} n={mm.sum():7d} cut depth p10/50/90/max {np.percentile(dep[mm],10):6.0f} {np.percentile(dep[mm],50):6.0f} {np.percentile(dep[mm],90):6.0f} {dep[mm].max():6.0f}")
    # wall relief: max h1 within 5 km of floor minus floor -> via coarse block max
    # hanging: minor floor above major floor
    hg = (v['floor_minor']-v['floor_major'])[onm]
    if hg.size: print(f"  minor floor above trunk floor: p10/50/90 {np.percentile(hg,10):.0f}/{np.percentile(hg,50):.0f}/{np.percentile(hg,90):.0f} m")
    print(f"  major trough (base_smooth - floor) on floor cells p10/50/90: {np.percentile((b - v['floor_major'])[onM],[10,50,90]).round()}")
    print(f"  floors below 0 on land(l>0): {(np.minimum(v['floor_major'],v['floor_minor'])[l>0] < 0).sum()}  min carved h on land {h1[l>0.3].min():.1f}")
    # descending: along-channel slope of floor_major vs outward direction
    gy, gx = np.gradient(v['floor_major'], sp); sy, sx = np.gradient(v['sdist_major'], sp)
    tn = np.hypot(sx, sy)+1e-12; tx, ty = -sy/tn, sx/tn
    sc = ocean.coast_distance(X, Y); gsy, gsx = np.gradient(sc, sp); gn = np.hypot(gsx, gsy)+1e-12
    rx, ry = -gsx/gn, -gsy/gn     # unit vector toward the coast
    out = tx*rx + ty*ry
    sgn = np.sign(out); ds = (gx*tx + gy*ty)*sgn     # floor slope moving outward along channel
    ok = onM & (np.abs(out) > 0.15)
    print(f"  major floor descending toward coast: {np.mean(ds[ok] < 0)*100:.1f}% of floor cells (strict), {np.mean(ds[ok] < 1e-3)*100:.1f}% within 1 m/km; along-slope p5/50/95 {np.percentile(ds[ok],5)*1000:.2f}/{np.percentile(ds[ok],50)*1000:.2f}/{np.percentile(ds[ok],95)*1000:.2f} m/km")
    gyr, gxr = np.gradient(h1, sp); fl_rough = np.hypot(gxr, gyr)[onM & (dep > 5)]
    print(f"  carved floor slope p50/p99 {np.median(fl_rough):.4f}/{np.percentile(fl_rough,99):.4f}")
    if img:
        s = fake.shade(h1, sp); hn = np.clip(h1/3500, 0, 1)
        rgb = np.stack([s*0.8+0.2*hn, s*0.85+0.15*hn, s*0.9+0.1], -1)
        rgb[onM] = rgb[onM]*np.array([0.6,0.8,1.0])
        fake.png(img, rgb[::-1])
    return X, Y, h0, h1, v, l
stats(C.SPAWN[0], C.SPAWN[1], 150e3, 300.0, "spawn region", "spawn300km.png")
stats(0.0, 1.6e6, 150e3, 300.0, "interior-ish (r~1600km)")
stats(0.0, 2.10e6, 150e3, 300.0, "near coast (r~2100km)", "coast300km.png")
stats(300e3, 300e3, 150e3, 300.0, "deep interior")
# 5. spawn
X, Y, h0, h1, v, l = stats(C.SPAWN[0], C.SPAWN[1], 30e3, 100.0, "spawn 60km", "spawn60km.png")
d = np.hypot(X-C.SPAWN[0], Y-C.SPAWN[1]); onM = v['dist_major'] < v['width_major']
print("spawn: nearest major floor", d[onM].min(), "m; depth there (h0-h1 max within 3km of floor):", (h0-h1)[onM & (d<30e3)].max(), " floor elev range", v['floor_major'][onM&(d<30e3)].min(), v['floor_major'][onM&(d<30e3)].max(), " surrounding h0 p90", np.percentile(h0[d<30e3],90))
