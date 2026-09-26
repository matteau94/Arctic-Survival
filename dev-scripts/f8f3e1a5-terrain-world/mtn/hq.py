import sys, numpy as np
sys.path.insert(0, r"C:\Users\leosp\Documents\Blender\Artic-Survival")
exec(open('val.py').read().split("sx,sy = SPAWN")[0])
from terrain import mountains as M
t=np.arange(0,400)*1.0; X,Y=np.meshgrid(1e6+t*40, 4e5+t*40)
n=M._pn(X,Y,977,1/250.0); png('hq_pn.png',(n*0.5+0.5)*255)
n=M._pn(X,Y,977,1/2000.0); png('hq_pn2.png',(n*0.5+0.5)*255)
