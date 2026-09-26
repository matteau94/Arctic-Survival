import sys, time, numpy as np
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival"); sys.path.insert(0,'.')
from terrain import ocean as O, config as C
from png import save_png
sp=(1960654.0, 741261.6)
size, step = 200e3, 400
t = np.arange(-size/2, size/2+1e-6, step); X, Y = np.meshgrid(sp[0]+t, sp[1]+t)
F = O._get_fields(X, Y); s = F['s']; lat = F['lat']
x=X.ravel(); y=Y.ravel()
wi,wr,wb,W = O._types(lat)
fok = O._fjord_ok(F, lat, wb)
n,gx,gy,_,_ = O._network_n(x,y)
dm = np.abs(n)/np.hypot(gx,gy)
band = (s>-6e3)&(s<75e3)
conn = np.zeros_like(s); conn[band & (dm<5e3)] = O._fjord_conn(x[band&(dm<5e3)], y[band&(dm<5e3)])
print('fok stats in band', np.percentile(fok[band],[5,25,50,75,95]))
print('wb', np.percentile(wb[band],[5,50,95]), 'fw', np.percentile(lat[band,O.F_FW],[5,50,95]))
rgb = np.zeros((len(t),len(t),3))
rgb[...,0] = (conn.reshape(X.shape))*255
rgb[...,1] = (fok.reshape(X.shape))*200
rgb[...,2] = np.clip(1-dm.reshape(X.shape)/3000,0,1)*255
rgb[(s<0).reshape(X.shape)] *= 0.4
save_png('diag.png', rgb[::-1])
