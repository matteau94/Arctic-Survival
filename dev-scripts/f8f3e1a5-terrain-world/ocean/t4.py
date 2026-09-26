import sys, time, numpy as np
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival"); sys.path.insert(0,'.')
from terrain import ocean as O, config as C, world
from png import save_png
def shade(h, step):
    gy, gx = np.gradient(h, step)
    l = np.clip(0.6 + (-gx*0.6 + gy*0.6)/np.sqrt(1+gx*gx+gy*gy)*1.2, 0.2, 1.3)
    rgb = np.zeros(h.shape+(3,))
    sea = h < 0
    d = np.clip(-h/600,0,1)
    rgb[sea] = np.stack([10+50*(1-d), 40+100*(1-d), 90+120*(1-d)],-1)[sea]
    lnd = np.stack([225*l, 230*l, 235*l],-1)
    rgb[~sea] = lnd[~sea]
    return rgb[::-1]
def region(cx, cy, size, step, fn, name, full=False):
    t = np.arange(-size/2, size/2+1e-6, step)
    X, Y = np.meshgrid(cx+t, cy+t)
    t0=time.perf_counter()
    h = world.height(X,Y) if full else O._ocean_only_height(X,Y)
    print(name, 'eval', time.perf_counter()-t0, 'min', h.min(), 'max', h.max(), 'sea frac', (h<0).mean())
    save_png(fn, shade(h, step)); return X,Y,h
sp = O.find_coastal_spawn(); print('spawn', sp)
region(sp[0], sp[1], 120e3, 150, 'spawn120.png', 'spawn120')
region(sp[0], sp[1], 120e3, 150, 'spawn120_world.png', 'spawn120 world', full=True)
region(sp[0], sp[1], 600e3, 600, 'spawn600.png', 'spawn600')
