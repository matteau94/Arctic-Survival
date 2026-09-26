import sys; sys.path.insert(0,'.')
import fake
if "--real" not in sys.argv: fake.install()
import numpy as np
from terrain import valleys as V, ocean, mountains, config as C
def runmax(a, r):
    o = a.copy()
    for s in range(1, r+1):
        o[:, s:] = np.maximum(o[:, s:], a[:, :-s]); o[:, :-s] = np.maximum(o[:, :-s], a[:, s:])
    p = o.copy()
    for s in range(1, r+1):
        p[s:] = np.maximum(p[s:], o[:-s]); p[:-s] = np.maximum(p[:-s], o[s:])
    return p
def region(cx0, cy0, half, sp):
    t = np.arange(-half, half+sp/2, sp); X, Y = np.meshgrid(t+cx0, t+cy0)
    b, l = ocean.continent(X, Y); h0 = b + mountains.height(X, Y, l)
    V._CACHE.clear(); h1 = V.carve(X, Y, h0, l); v = V.valley_info(X, Y)
    return X, Y, h0, h1, v, l
allv=[]
for c in [(C.SPAWN[0], C.SPAWN[1]), (0, 1.6e6), (300e3, 300e3), (-900e3, -500e3)]:
    X, Y, h0, h1, v, l = region(c[0], c[1], 150e3, 300.)
    wd = runmax(h1, int(5000/300)) - v['floor_major']
    onM = v['dist_major'] < v['width_major']
    for lo, hi, rn in ((0,.2,'plateau'),(.2,.7,'foothill'),(.7,1.01,'mountain')):
        m = onM & (v['relief']>=lo)&(v['relief']<hi)
        if m.sum()>20: print(c, rn, "major valley depth (max h within 5km - floor) p10/50/90/max", np.percentile(wd[m],[10,50,90]).round(), wd[m].max().round(), "n", m.sum())
    onm = (v['dist_minor'] < v['width_minor']) & (v['minor_strength']>0.5) & (v['dist_major']>v['width_major']+4000)
    wdm = runmax(h1, int(2500/300)) - v['floor_minor']
    for lo, hi, rn in ((0,.2,'plateau'),(.2,.7,'foothill'),(.7,1.01,'mountain')):
        m = onm & (v['relief']>=lo)&(v['relief']<hi)
        if m.sum()>20: print(c, rn, "  minor valley depth (max h within 2.5km - floor) p10/50/90", np.percentile(wdm[m],[10,50,90]).round(), "n", m.sum())
    i = np.argmax(np.where(onM, wd, -1)); allv.append((wd.flat[i], X.flat[i], Y.flat[i]))
print(allv)
d, x, y = max(allv)
X, Y, h0, h1, v, l = region(x, y, 20e3, 50.)
s = fake.shade(h1, 50.); hn = np.clip(h1/3500,0,1)
fake.png('mtn_crossing40km_'+('real' if '--real' in sys.argv else 'fake')+'.png', np.stack([s*0.85+0.15*hn]*3,-1)[::-1])
# cross-section through the trunk
i = np.argmin(np.abs(v['sdist_major'][400]))
print("row cross-section h1 every 500 m around trunk:", h1[400, max(0,i-60):i+61:10].round())
X, Y, h0, h1, v, l = region(C.SPAWN[0], C.SPAWN[1], 40e3, 100.)
s = fake.shade(h1, 100.); hn = np.clip(h1/4000,0,1)
fake.png('spawn80km_'+('real' if '--real' in sys.argv else 'fake')+'.png', np.stack([s*0.85+0.15*hn]*3,-1)[::-1])
s = fake.shade(h0, 100.)
fake.png('spawn80km_uncarved.png', np.stack([s*0.85+0.15*hn]*3,-1)[::-1])
