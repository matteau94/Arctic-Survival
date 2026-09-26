def _sd_nodes(fn, IX, IY, S, gmin, clamp, grid):
    """Signed distance n / max(|grad n|, gmin) at lattice nodes, grad by central differences
    with the neighbouring lattice nodes (identical value whichever query touches a node)."""
    if grid:                       # regular (ny, nx) block: share neighbour evaluations
        ax = np.arange(IX[0, 0] - 1, IX[0, -1] + 2); ay = np.arange(IY[0, 0] - 1, IY[-1, 0] + 2)
        PX, PY = np.meshgrid(ax, ay)
        n = fn(*_node_xy(PX, PY, S))[1]
        n0 = n[1:-1, 1:-1]
        gx = (n[1:-1, 2:] - n[1:-1, :-2]) / (2 * S)
        gy = (n[2:, 1:-1] - n[:-2, 1:-1]) / (2 * S)
    else:
        def n_at(a, b):
            return fn(*_node_xy(a, b, S))[1]
        n0 = n_at(IX, IY)
        gx = (n_at(IX + 1, IY) - n_at(IX - 1, IY)) / (2 * S)
        gy = (n_at(IX, IY + 1) - n_at(IX, IY - 1)) / (2 * S)
    g = np.maximum(np.sqrt(gx * gx + gy * gy), gmin)
    return np.clip(n0 / g, -clamp, clamp)


def _bilerp(node_fn, X, Y, S, k):
    """Bilinear interpolation at points of k fields defined on the world lattice of spacing S.
    node_fn(IX, IY, grid) -> (..., k). Dense block evaluation for compact queries, per-corner
    evaluation for scattered ones (same node values either way)."""
    fx = X / S; fy = Y / S
    ix = np.floor(fx).astype(np.int64); iy = np.floor(fy).astype(np.int64)
    tx = (fx - ix).reshape(-1, 1); ty = (fy - iy).reshape(-1, 1)
    ix0, ix1, iy0, iy1 = ix.min(), ix.max() + 1, iy.min(), iy.max() + 1
    if _dense_ok(ix0, ix1, iy0, iy1, X.size):
        IX, IY = np.meshgrid(np.arange(ix0, ix1 + 1), np.arange(iy0, iy1 + 1))
        nx = IX.shape[1]
        G = node_fn(IX, IY, True).reshape(-1, k)
        flat = ((iy - iy0) * nx + (ix - ix0)).ravel()
        v00 = np.take(G, flat, axis=0); v10 = np.take(G, flat + 1, axis=0)
        v01 = np.take(G, flat + nx, axis=0); v11 = np.take(G, flat + nx + 1, axis=0)
    else:
        ix = ix.ravel(); iy = iy.ravel()
        v00 = node_fn(ix, iy, False).reshape(-1, k); v10 = node_fn(ix + 1, iy, False).reshape(-1, k)
        v01 = node_fn(ix, iy + 1, False).reshape(-1, k); v11 = node_fn(ix + 1, iy + 1, False).reshape(-1, k)
    a = v00 + (v10 - v00) * tx
    b = v01 + (v11 - v01) * tx
    return (a + (b - a) * ty).reshape(X.shape + (k,))


def _major_nodes(IX, IY, grid):
    """Per 500 m node: [signed major distance, 7 regional fields]."""
    sd = _sd_nodes(NW.major_distance, IX, IY, MAJOR_LATTICE, 0.25 * NW.MAJOR_FREQ, MAJOR_CLAMP, grid)
    reg = _regional(*_node_xy(IX, IY, MAJOR_LATTICE))
    return np.concatenate([sd[..., None], reg], axis=-1)


def _minor_nodes(IX, IY, grid):
    return _sd_nodes(NW.minor_distance, IX, IY, MINOR_LATTICE, 0.25 * NW.MINOR_FREQ, MINOR_CLAMP,
                     grid)[..., None]
