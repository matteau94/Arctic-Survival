import sys, time, numpy as np
sys.path.insert(0, r"C:\Users\leosp\Documents\Blender\Artic-Survival")
from terrain import mountains as M
def tmin(f,n=7):
    b=1e9
    for _ in range(n):
        t0=time.perf_counter(); f(); b=min(b,time.perf_counter()-t0)
    return b*1e3
t=np.linspace(0,25749,257); X,Y=np.meshgrid(1e6+t,4e5+t); x=X.ravel(); y=Y.ravel()
print("pn", tmin(lambda: M._pn(x,y,5,1/500)))
GC=(M._GA+1j*M._GB).astype(np.complex64)
def pn2(X,Y,seed,freq):
    x = X * freq; y = Y * freq
    xf = np.floor(x); yf = np.floor(y)
    fx = (x - xf).astype(np.float32); fy = (y - yf).astype(np.float32)
    ix = xf.astype(np.int32); iy = yf.astype(np.int32)
    hx0 = ix * np.int32(374761393); hx1 = hx0 + np.int32(374761393)
    hy0 = iy * np.int32(668265263) + np.int32((seed * 1013904223) & 0x7FFFFFFF)
    hy1 = hy0 + np.int32(668265263)
    def g(hx, hy, dx, dy):
        h = hx ^ hy
        h *= np.int32(1274126177)
        h >>= 28
        h &= 15
        c = GC[h]
        return c.real * dx + c.imag * dy
    fx1 = fx - 1; fy1 = fy - 1
    n00 = g(hx0, hy0, fx, fy); n10 = g(hx1, hy0, fx1, fy)
    n01 = g(hx0, hy1, fx, fy1); n11 = g(hx1, hy1, fx1, fy1)
    u = fx * fx * fx * (fx * (fx * 6 - 15) + 10)
    v = fy * fy * fy * (fy * (fy * 6 - 15) + 10)
    a = n00 + u * (n10 - n00); b = n01 + u * (n11 - n01)
    return a + v * (b - a)
print("pn2", tmin(lambda: pn2(x,y,5,1/500)))
n=pn2(x,y,5,1/500); print(n.std(), n.min(), n.max())
print("floor+astype", tmin(lambda: np.floor(x*0.002).astype(np.int32)))
print("cirq", tmin(lambda: M._cirques(x,y,5)))
print("nun", tmin(lambda: M._nunataks(x,y,5)))
print("lattice", tmin(lambda: M._lattice(X,Y,M._macro)))
xs=x.copy(); print("macro 2809", tmin(lambda: M._macro(xs[:2809],ys[:2809]) if False else M._macro(x[:2809]*1.0,y[:2809]*1.0)))
