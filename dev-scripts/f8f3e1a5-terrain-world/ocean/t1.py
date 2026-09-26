import sys, time, numpy as np
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
t0=time.perf_counter()
from terrain import ocean as O, config as C
O._init(); print('init', time.perf_counter()-t0, 'islands', len(O._T['isl_arr']))
# continent scale
t=np.arange(-3e6,3e6+1,10e3); X,Y=np.meshgrid(t,t)
t0=time.perf_counter()
b,l=O.continent(X,Y); h=O.coast(X,Y,b,l)
print('continent grid', X.shape, time.perf_counter()-t0)
print('land frac (h>0)', (h>0).mean(), 'land>0.5', (l>0.5).mean(), 'max', h.max(), 'min', h.min())
s=O.coast_distance(X,Y)
area_land=(h>0).sum()*1e8; print('land area km2', area_land/1e6, 'equiv radius km', np.sqrt(area_land/np.pi)/1e3)
np.save(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/f8f3e1a5-a64d-4376-bcb4-8359c5ce6238/scratchpad/ocean/h.npy", h)
