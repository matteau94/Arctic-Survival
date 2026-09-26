import sys, numpy as np
sys.path.insert(0, r"C:\Users\leosp\Documents\Blender\Artic-Survival")
exec(open('val.py').read().split("sx,sy = SPAWN")[0])
from terrain import mountains as M, ocean
t=np.arange(-2500,2500,25.0); X,Y=np.meshgrid(1042e3+t,402e3+t); base,land=ocean.continent(X,Y)
m=M.height(X,Y,land); save('st_m.png',m,25.0,3)
F=M._lattice(X,Y,M._macro).reshape(X.shape+(-1,))
for k,nm in enumerate(['amp','struct','wx','wy','rlo','wgt','nd']):
    f=F[...,k]; print(nm, f.min(), f.max())
nun=M._nunataks(X.ravel(),Y.ravel(),M.SEED+900+80).reshape(X.shape); save('st_nun.png',nun,25.0,3); print('nun',nun.max())
for k,nm in enumerate(['amp','struct','wx','wy','rlo','wgt','nd']):
    f=F[...,k]; png('st_f_%s.png'%nm, (f-f.min())/(np.ptp(f)+1e-9)*255)
