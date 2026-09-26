import sys, time; sys.path.insert(0,'.')
import fake
if '--real' not in sys.argv: fake.install()
import numpy as np
from terrain import valleys as V, ocean, mountains, config as C, noise as N
res = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 257
t=np.linspace(0,C.CHUNK_SIZE,res); X,Y=np.meshgrid(t+C.SPAWN[0],t+C.SPAWN[1]); b,l=ocean.continent(X,Y); h0=b+mountains.height(X,Y,l)
V.carve(X,Y,h0,l)
cv=[]; ref=[]
for i in range(15):
    V._CACHE.clear(); t0=time.perf_counter(); V.carve(X,Y,h0,l); cv.append(time.perf_counter()-t0)
    t0=time.perf_counter(); N.perlin(X,Y,5,1e-4); ref.append(time.perf_counter()-t0)
print(f"res {res}: carve min {min(cv)*1e3:.1f} ms median {np.median(cv)*1e3:.1f} ms | reference perlin min {min(ref)*1e3:.1f} ms (carve = {min(cv)/min(ref):.1f} perlins)")
