import sys, time, numpy as np, cProfile, pstats
sys.path.insert(0, r"C:\Users\leosp\Documents\Blender\Artic-Survival")
from terrain import mountains as M, ocean
from terrain.config import SPAWN, CHUNK_SIZE
x0,y0=np.floor(np.array(SPAWN)/CHUNK_SIZE)*CHUNK_SIZE
tt=np.linspace(0,CHUNK_SIZE,257); X,Y=np.meshgrid(x0+tt,y0+tt); base,land=ocean.continent(X,Y)
M.height(X,Y,land)
cProfile.run('for _ in range(3): M.height(X,Y,land)','p.out')
pstats.Stats('p.out').sort_stats('cumtime').print_stats(18)
