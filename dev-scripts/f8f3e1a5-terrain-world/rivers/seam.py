import sys, numpy as np
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
from terrain import config as C, ocean, world, rivers as R
def padded(cx, cy, lod):
    res = C.LOD_RES[lod]; step = C.CHUNK_SIZE/(res-1)
    t = np.arange(-1, res+1, dtype=np.float64)/(res-1)
    Xe, Ye = np.meshgrid((cx+t)*C.CHUNK_SIZE, (cy+t)*C.CHUNK_SIZE)
    He, Le = world.height(Xe, Ye, return_land=True)
    M = world.surface(Xe, Ye, He, Le, step)
    s = (slice(1,-1), slice(1,-1))
    return He[s], M['ice'][s], M['river'][s] if 'river' in M else None
cx, cy = world.chunk_of(1966439.0, 735875.0)
worst = 0; worst_i = 0; nriv = 0
for (a, b, axis) in [((cx, cy), (cx+1, cy), 'x'), ((cx, cy), (cx, cy+1), 'y'), ((cx-1, cy), (cx, cy), 'x'), ((cx, cy-1), (cx, cy), 'y'), ((cx+1,cy),(cx+1,cy+1),'y'), ((cx-1,cy+1),(cx,cy+1),'x')]:
    for lod in (0, 1):
        A = world.sample_chunk(*a, lod); B = world.sample_chunk(*b, lod)
        ea = A.H[:, -1] if axis == 'x' else A.H[-1, :]
        eb = B.H[:, 0] if axis == 'x' else B.H[0, :]
        pa = padded(*a, lod); pb = padded(*b, lod)
        ia = pa[1][:, -1] if axis == 'x' else pa[1][-1, :]
        ib = pb[1][:, 0] if axis == 'x' else pb[1][0, :]
        ra = pa[2][:, -1] if axis == 'x' else pa[2][-1, :]
        d = np.abs(ea - eb).max(); di = np.abs(ia - ib).max()
        # also the padded H equals sample_chunk H
        dp = np.abs(pa[0] - A.H).max()
        print(f"{a}->{b} lod{lod}: max |dH| edge {d:.3g}  max |d ice| edge {di:.3g}  river verts on edge {(ra>0.5).sum()}  padded-vs-sample {dp:.3g}")
        worst = max(worst, d); worst_i = max(worst_i, di); nriv += (ra > 0.5).sum()
print("WORST dH", worst, "WORST dice", worst_i, "river edge verts total", nriv)
