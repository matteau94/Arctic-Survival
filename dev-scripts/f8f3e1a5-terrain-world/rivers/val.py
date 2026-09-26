import sys, time, numpy as np
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
from terrain import config as C, ocean, valleys, world, rivers as R
rng = np.random.default_rng(3)

def fields(px, py):
    R._CACHE.clear()
    return R._fields(px, py)

def project(px, py, it=4):
    e = 5.0
    for _ in range(it):
        n = len(px)
        F = fields(np.concatenate([px, px + e, px]), np.concatenate([py, py, py + e]))
        sd = F['sd']; s0 = sd[:n]; gx = (sd[n:2*n] - s0) / e; gy = (sd[2*n:] - s0) / e
        g2 = gx*gx + gy*gy + 1e-12
        px = px - s0 * gx / g2; py = py - s0 * gy / g2
    return px, py, gx, gy

def seeds_in(cx, cy, half, step=200.0):
    t = np.arange(-half, half, step)
    X, Y = np.meshgrid(cx + t, cy + t)
    F = fields(X, Y)
    m = (np.abs(F['sd']) < step * 0.6) & (F['hw'] > 20)
    idx = np.nonzero(m.ravel())[0]
    if len(idx) > 40: idx = rng.choice(idx, 40, replace=False)
    return X.ravel()[idx], Y.ravel()[idx]

def trace(px, py, nsteps=120, ds=100.0):
    px, py, gx, gy = project(px, py)
    recs = []
    alive = np.ones(len(px), bool)
    prev_t = None
    for k in range(nsteps):
        g = np.hypot(gx, gy) + 1e-12
        tx, ty = -gy / g, gx / g
        if prev_t is None:
            sa = ocean.coast_distance(px + 50*tx, py + 50*ty); sb = ocean.coast_distance(px - 50*tx, py - 50*ty)
            sgn = np.where(sa < sb, 1.0, -1.0)
        else:
            sgn = np.where(tx*prev_t[0] + ty*prev_t[1] >= 0, 1.0, -1.0)
        tx, ty = tx*sgn, ty*sgn; prev_t = (tx, ty)
        H, L = world.height(px[None], py[None], return_land=True); H = H[0]
        v = valleys.valley_info(px, py); F = fields(px, py)
        s = ocean.coast_distance(px, py)
        recs.append(dict(x=px.copy(), y=py.copy(), H=H, s=s, floor=v['floor_major'].copy(), lvl=F['lvl'].copy(),
                         hw=F['hw'].copy(), alive=alive.copy(), wM=v['width_major'].copy(), sdM=v['sdist_major'].copy()))
        alive &= (F['hw'] > 1) & (s > 0) & (H > 0.5)
        px, py, gx, gy = project(px + ds*tx, py + ds*ty, 2)
    return recs

def analyse(recs, label):
    up = []; dh_all = []; onfloor = []; lvl_err = []; bank = []; offfloor = []
    for a, b in zip(recs[:-1], recs[1:]):
        m = a['alive'] & b['alive'] & (b['hw'] > 1) & (b['H'] > 0.5) & (b['s'] > 0)
        ds_ = b['s'] - a['s']; dh = b['H'] - a['H']
        # orient coastward
        dh_c = np.where(ds_ < 0, dh, -dh)[m & (np.abs(ds_) > 1)]
        dh_all.append(dh_c)
    for r in recs:
        m = r['alive'] & (r['hw'] > 1) & (r['H'] > 0.5)
        onfloor.append((r['H'] - r['floor'])[m]); lvl_err.append((r['H'] - r['lvl'])[m])
        offfloor.append((np.abs(r['sdM']) + r['hw'] - r['wM'])[m])
    dh = np.concatenate(dh_all); of = np.concatenate(onfloor); le = np.concatenate(lvl_err); off = np.concatenate(offfloor)
    print(f"[{label}] centre-line samples {len(of)}, coastward steps {len(dh)}")
    for thr in (0.01, 0.1, 0.5, 2.0):
        print(f"   uphill coastward > {thr} m: {100*np.mean(dh > thr):.2f} %")
    print(f"   max uphill step {dh.max():.2f} m, median step {np.median(dh):.2f} m")
    print(f"   H - valley floor_major: median {np.median(of):.2f}, p5 {np.percentile(of,5):.2f}, p95 {np.percentile(of,95):.2f}, min {of.min():.1f}, max {of.max():.1f}")
    print(f"   H - river level: median {np.median(le):.3f}, |err|>0.5m {100*np.mean(np.abs(le)>0.5):.2f} %")
    print(f"   river edge beyond floor edge (>0 = off floor): {100*np.mean(off>0):.2f} %  max {off.max():.0f} m")

regions = {'coastal_spawn': (1966439.0, 735875.0)}
# random land windows around the continent
ang = rng.uniform(0, 2*np.pi, 60)
pts = []
for a in ang:
    for r in (1.3e6, 1.7e6, 2.0e6):
        x, y = r*np.cos(a), r*np.sin(a)
        s = ocean.coast_distance(np.array([x]), np.array([y]))[0]
        if 5e3 < s < 900e3: pts.append((x, y, s))
sel = rng.choice(len(pts), min(8, len(pts)), replace=False)
for i in sel: regions[f"rand_s{pts[i][2]/1e3:.0f}km"] = pts[i][:2]
allrecs = []
for name, (cx, cy) in regions.items():
    t0 = time.time()
    sx, sy = seeds_in(cx, cy, 30000.0)
    if len(sx) == 0: print(name, "no river seeds"); continue
    recs = trace(sx, sy)
    analyse(recs, name + f" ({time.time()-t0:.0f}s)")
    allrecs.append(recs)
# merge
print("=== ALL ===")
merged = [ {k: np.concatenate([rs[i][k] for rs in allrecs]) for k in allrecs[0][0]} for i in range(len(allrecs[0])) ]
analyse(merged, "all")
