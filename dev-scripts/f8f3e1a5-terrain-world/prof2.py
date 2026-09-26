import sys; sys.path.insert(0,'.'); import fake; fake.install()
import numpy as np, cProfile, pstats, time
from terrain import valleys as V, ocean, mountains, config as C
RES=int([a for a in sys.argv if a.isdigit()][0]) if any(a.isdigit() for a in sys.argv) else 257
t=np.linspace(0,C.CHUNK_SIZE,RES); X,Y=np.meshgrid(t+C.SPAWN[0],t+C.SPAWN[1]); b,l=ocean.continent(X,Y); h0=b+mountains.height(X,Y,l)
V.carve(X,Y,h0,l)
pr=cProfile.Profile()
for i in range(5):
    V._CACHE.clear(); pr.enable(); V.carve(X,Y,h0,l); pr.disable()
pstats.Stats(pr).sort_stats('tottime').print_stats(14)
