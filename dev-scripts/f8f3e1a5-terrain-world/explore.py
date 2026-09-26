import sys, time; sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
import numpy as np
from terrain import network as NW, config as C
for name, fn, f in (("major", NW.major_distance, NW.MAJOR_FREQ), ("minor", NW.minor_distance, NW.MINOR_FREQ)):
    s = 400e3 if name=="major" else 80e3
    t = np.linspace(-s, s, 801); X, Y = np.meshgrid(t + 1e6, t + 3e5)
    t0=time.time(); d, n = fn(X, Y); dt=time.time()-t0
    g = np.abs(n)/np.maximum(d,1e-9)
    print(name, "time", dt, "g/freq pct", np.percentile(g/f, [1,5,25,50,75,95]), "d pct", np.percentile(d,[10,50,90,99]))
    # true distance check via zero crossings sampled: compare estimate for d<5km
    sp = t[1]-t[0]
    zc = (np.sign(n[:,1:])!=np.sign(n[:,:-1]))
    print(" frac cells with crossing", zc.mean(), "spacing", sp)
d,n = NW.major_distance(np.array([C.SPAWN[0]]), np.array([C.SPAWN[1]])); print("spawn major d", d)
t = np.linspace(-40e3, 40e3, 321); X,Y = np.meshgrid(t+C.SPAWN[0], t+C.SPAWN[1])
d,n = NW.major_distance(X,Y); i=np.unravel_index(np.argmin(d), d.shape); print("min d near spawn", d.min(), X[i]-C.SPAWN[0], Y[i]-C.SPAWN[1])
X1=np.full((257,257),1.0)*C.SPAWN[0]; 
t=np.linspace(0,C.CHUNK_SIZE,257); X,Y=np.meshgrid(t+1e6,t+4e5)
t0=time.time(); NW.major_distance(X,Y); NW.minor_distance(X,Y); print("both nets 257^2", time.time()-t0)
