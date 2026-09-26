import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sdf import *
from face import *
zs = np.arange(1.53, 1.72, 0.004)
for x in (0.0, 0.02):
    P = np.stack([np.full_like(zs, x), np.zeros_like(zs), zs], -1)
    # march along -y from y=0 to find surface
    ys = np.linspace(-0.16, 0.0, 800)
    out = []
    for z in zs:
        Q = np.stack([np.full_like(ys, x), ys, np.full_like(ys, z)], -1)
        f = F_head(Q)
        i = np.argmax(f < 0)
        out.append(ys[i])
    print("x=", x, " ".join(f"{z:.3f}:{y:.4f}" for z, y in zip(zs, out)))
