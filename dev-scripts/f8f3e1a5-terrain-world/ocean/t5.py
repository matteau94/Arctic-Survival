import sys, time, numpy as np
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival"); sys.path.insert(0,'.')
from terrain import ocean as O, config as C
from png import save_png
from t4h import shade, lakes
t0=time.perf_counter(); sp = O.find_coastal_spawn(); print('spawn', sp, time.perf_counter()-t0)
for (cx,cy,size,step,name) in [(sp[0],sp[1],120e3,150,'spawn120'), (sp[0],sp[1],400e3,400,'spawn400')]:
    t = np.arange(-size/2, size/2+1e-6, step); X, Y = np.meshgrid(cx+t, cy+t)
    t0=time.perf_counter(); h = O._ocean_only_height(X,Y)
    lk, nl = lakes(h, O.coast_distance(X,Y))
    print(name, 'eval %.1fs'%(time.perf_counter()-t0), 'sea frac %.2f'%(h<0).mean(), 'lake px', lk, 'lake comps', nl)
    save_png(name+'.png', shade(h, step))
