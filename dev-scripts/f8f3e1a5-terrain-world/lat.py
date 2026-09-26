def _bspline_w(t):
    t2 = t * t; t3 = t2 * t
    return ((1 - t) ** 3 / 6.0, (3 * t3 - 6 * t2 + 4) / 6.0,
            (-3 * t3 + 3 * t2 + 3 * t + 1) / 6.0, t3 / 6.0)


def _unique_nodes(fn, corners):
    """Evaluate fn(IX, IY) -> (..., k) once per distinct node across a list of (ix, iy) arrays
    (scattered-point queries). Returns one (n, k) array per corner entry."""
    n = corners[0][0].size
    IX = np.concatenate([c[0] for c in corners])
    IY = np.concatenate([c[1] for c in corners])
    uk, inv = np.unique(np.stack([IX, IY], axis=1), axis=0, return_inverse=True)
    vals = fn(uk[:, 0], uk[:, 1])
    vals = vals.reshape(len(uk), -1)[inv.ravel()]
    return [vals[i * n:(i + 1) * n] for i in range(len(corners))]


def _lattice_interp(node_fn, X, Y, S, k, cubic):
    """Interpolate k fields living on the world-fixed lattice of spacing S at points (X, Y).
    cubic=True: uniform cubic B-spline (C2, smoothing, no overshoot); else bilinear.
    node_fn(IX, IY, grid) -> (..., k); grid=True means IX/IY are a regular (ny, nx) block.
    Compact queries evaluate one dense block of nodes; scattered queries evaluate only the
    distinct nodes they touch. Node values are identical either way -> seams/points match."""
    fx = X.ravel() / S; fy = Y.ravel() / S
    ix = np.floor(fx).astype(np.int64); iy = np.floor(fy).astype(np.int64)
    tx = fx - ix; ty = fy - iy
    if cubic:
        wx = _bspline_w(tx); wy = _bspline_w(ty); o0 = -1
    else:
        wx = (1.0 - tx, tx); wy = (1.0 - ty, ty); o0 = 0
    m = len(wx)
    out = np.zeros((fx.size, k))
    ix0, ix1 = ix.min() + o0, ix.max() + o0 + m - 1
    iy0, iy1 = iy.min() + o0, iy.max() + o0 + m - 1
    if _dense_ok(ix0, ix1, iy0, iy1, fx.size):
        IX, IY = np.meshgrid(np.arange(ix0, ix1 + 1), np.arange(iy0, iy1 + 1))
        nx = IX.shape[1]
        G = node_fn(IX, IY, True).reshape(-1, k)
        flat = (iy + o0 - iy0) * nx + (ix + o0 - ix0)
        taps = [np.take(G, flat + (b * nx + a), axis=0) for b in range(m) for a in range(m)]
    else:
        taps = _unique_nodes(lambda a, b: node_fn(a, b, False),
                             [(ix + o0 + a, iy + o0 + b) for b in range(m) for a in range(m)])
    for b in range(m):
        for a in range(m):
            out += (wx[a] * wy[b])[:, None] * taps[b * m + a]
    return out.reshape(X.shape + (k,))


def _regional(X, Y):
    """Regional fields (B-spline over the REGIONAL_SPACING lattice) at points -> (..., 7)."""
    S = REGIONAL_SPACING
    return _lattice_interp(lambda IX, IY, g: _regional_nodes(*_node_xy(IX, IY, S)),
                           X, Y, S, 7, cubic=True)


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
    return np.clip(n0 / g, -clamp, clamp)[..., None]


def _sdist_major(X, Y):
    fn = lambda IX, IY, g: _sd_nodes(NW.major_distance, IX, IY, MAJOR_LATTICE,
                                     0.25 * NW.MAJOR_FREQ, MAJOR_CLAMP, g)
    return _lattice_interp(fn, X, Y, MAJOR_LATTICE, 1, cubic=True)[..., 0]


def _sdist_minor(X, Y):
    fn = lambda IX, IY, g: _sd_nodes(NW.minor_distance, IX, IY, MINOR_LATTICE,
                                     0.25 * NW.MINOR_FREQ, MINOR_CLAMP, g)
    return _lattice_interp(fn, X, Y, MINOR_LATTICE, 1, cubic=True)[..., 0]


def _regional_fine(X, Y):
    """Regional fields bilinearly resampled from a MAJOR_LATTICE-spaced cache lattice (the
    B-spline is evaluated only at those nodes; the fields are smooth at that scale)."""
    S = MAJOR_LATTICE
    return _lattice_interp(lambda IX, IY, g: _regional(*_node_xy(IX, IY, S)),
                           X, Y, S, 7, cubic=False)
