import sys, numpy as np; sys.path.insert(0, '.')
from png import save_png, hmap
h = np.load('h.npy'); save_png('map_continent.png', hmap(h))
