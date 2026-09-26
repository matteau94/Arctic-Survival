import sys, numpy as np
sys.path.insert(0, r"C:\Users\leosp\Documents\Blender\Artic-Survival")
exec(open('val.py').read().split("sx,sy = SPAWN")[0])
from terrain import mountains as M, ocean
cxw, cyw, size, sp, name = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
t=np.arange(-size/2,size/2,sp); X,Y=np.meshgrid(cxw+t,cyw+t); base,land=ocean.continent(X,Y)
m=M.height(X,Y,land); save(name+'_m.png', m, sp, float(sys.argv[6]) if len(sys.argv)>6 else 1.0)
print(name, 'max', m.max(), 'mean', m.mean())
