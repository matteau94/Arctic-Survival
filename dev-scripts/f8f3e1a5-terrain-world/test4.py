import sys; sys.path.insert(0,'.')
import fake; fake.install()
import numpy as np
from terrain import valleys as V, ocean, mountains
x, y = 395100.0, 333600.0
t = np.arange(-6000, 6000, 20.); X, Y = np.meshgrid(t+x+4000, t+y-6000)
b, l = ocean.continent(X, Y)
h0 = np.full(X.shape, 6000.0)
h1 = V.carve(X, Y, h0, l)
fake.png('flatcarve12km.png', np.stack([fake.shade(h1, 20.)]*3, -1)[::-1])
