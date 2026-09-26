"""Glacial valleys - owned by the valleys agent.

U-shaped glacial troughs carved along the shared drainage network (network.py):

  * major trunk valleys  - flat floors 2-5 km wide, steep walls in mountains, 1.5-2 km deep where
    they cut through ranges, 100-300 m troughs across the flat ice plateau.
  * minor tributaries    - floors 0.5-1.5 km wide, shallower, and HANGING: their floor sits above
    the trunk floor, so they end in a step where they meet a major valley.

Everything is a pure, vectorised function of world metres (chunk seams match exactly).

Public API
----------
valley_info(X, Y, h=None, land=None) -> dict   (rivers.py imports this; see its docstring)
floor_height(X, Y, h=None, land=None) -> array (convenience: effective valley floor height)
carve(X, Y, h, land) -> h                      (world.py pipeline step)
surface(X, Y, H, land, masks)                  (rock on steep valley walls, snow on floors)

How the floor is kept smooth and draining
-----------------------------------------
Floor heights are NOT derived from the incoming (noisy) h. They come from a coarse world-fixed
"regional" lattice (REGIONAL_SPACING) on which the continental base (ocean.continent) and the
mountain field (mountains.height) are box-averaged and then reconstructed with a cubic
B-spline (C2-smooth, no overshoot). Floor = regional base - trough depth(base), which is a
monotone function of the continental base, so floors fall toward the coast wherever the base
does. Tributaries hang above that by an amount that grows with regional mountain relief.

How the channel distance is made cheap and robust
-------------------------------------------------
network.py's |n|/|grad n| estimate ignores the warp chain rule (off by up to ~2x) and explodes
near saddle points. Here the raw signed network noise n is sampled on world-fixed lattices
(MAJOR_LATTICE / MINOR_LATTICE metres), the TRUE gradient of the warped field is taken by
central differences on that lattice, the signed distance n / max(|grad|, g_min) is clamped and
then bilinearly interpolated. Zero-lines (valley centre-lines) are identical to network.py's.
This is ~10x cheaper than evaluating the networks per vertex and gives the same values for
dense chunk grids and scattered point queries (so world.height(x, y) of a single point matches
the chunk mesh).
"""
import numpy as np
from . import noise as N
from . import network as NW
from .config import SEED, PLATEAU_HEIGHT, CONTINENT_RADIUS

try:                                   # ice-dome length scale of ocean.py's profile
    from .ocean import DOME_L
except Exception:                      # pragma: no cover - old stub
    DOME_L = 900e3

# --------------------------------------------------------------------------- tuning parameters
MAJOR_LATTICE = 500.0          # m, lattice for the major-network signed distance
MINOR_LATTICE = 250.0          # m, lattice for the minor-network signed distance
REGIONAL_SPACING = 4000.0      # m, lattice for smoothed base / relief / low-freq noise fields
REGIONAL_STENCIL = 4000.0      # m, half-size of the 3x3 box average taken at each regional node
MAJOR_CLAMP = 60000.0          # m, signed distance clamp (saddles / medial axes)
MINOR_CLAMP = 20000.0

MAJOR_HALF_FLOOR = (1000.0, 2500.0)   # half floor width range (floor 2-5 km)
MINOR_HALF_FLOOR = (250.0, 750.0)     # half floor width range (floor 0.5-1.5 km)
TROUGH_MIN = 100.0                    # trunk floor at least this far below the smoothed ice
FLOOR_DOME_MARGIN = 0.06              # trunk floor profile = dome(s)*(1-margin) - drop + tilt(s)
FLOOR_DROP = 80.0
INTERIOR_TILT = 150.0                 # extra floor rise over the flat interior (> DOME_L inland)
INTERIOR_TILT_LEN = 1.0e6             # ... spread over this much further inland distance
MINOR_PLATEAU_DEPTH = 35.0            # minor trough depth below base on the flat plateau
HANG_MOUNTAIN = (180.0, 420.0)        # tributary floor height above trunk-level in full relief
RELIEF_RANGE = (150.0, 1400.0)        # regional mean mountain height -> relief factor 0..1
MAJOR_WALL_SLOPE = (0.12, 1.15)       # wall slope (rise/run) on plateau .. in mountains
MINOR_WALL_SLOPE = (0.08, 0.95)
MAJOR_TOE = (500.0, 900.0)            # parabolic wall-toe length (U-shape rounding)
MINOR_TOE = (200.0, 350.0)
SHOULDER_K = (30.0, 90.0)             # smooth-min radius where walls meet the original terrain
MIN_FLOOR = 3.0                       # floors never go below this on land
MAX_RELIEF_W = 0.45                   # weight of regional max mountain height in the relief measure
MINOR_LIFT = 0.25                     # tributary floors rise by this fraction of mean mountain height
MINOR_NEAR_TRUNK = (6000.0, 16000.0)  # plateau tributaries only within this distance of a trunk
WALL_NOISE = 0.22                     # relative wall-height modulation (spurs / bays)
LAND_FADE = (0.0, 0.25)               # carve strength fades in over this land-mask range

_S_WIDTH_MAJ = SEED + 9101
_S_WIDTH_MIN = SEED + 9102
_S_SLOPE = SEED + 9103
_S_HANG = SEED + 9104
_S_WALL = SEED + 9105

_CACHE = []                    # tiny LRU of (key, info) so carve/rivers/surface share one eval
_CACHE_SIZE = 3


# --------------------------------------------------------------------------- lattice helpers
def _ss(e0, e1, x):
    return N.smoothstep(e0, e1, x)


def _lerp(a, b, t):
    return a + (b - a) * t


def _dense_ok(ix0, ix1, iy0, iy1, npts):
    return (ix1 - ix0 + 1) * (iy1 - iy0 + 1) <= max(4 * npts, 4096)


def _node_xy(ix, iy, S):
    return ix.astype(np.float64) * S, iy.astype(np.float64) * S


def _coast_distance(X, Y):
    """Signed distance to the coast (+ inland) from ocean.py; radial fallback for old stubs."""
    from . import ocean
    f = getattr(ocean, 'coast_distance', None)
    if f is not None:
        return f(X, Y)
    return CONTINENT_RADIUS - np.sqrt(X * X + Y * Y)


def _regional_nodes(xn, yn):
    """Fields stored on the regional lattice, evaluated at node coords (any shape).
    Returns (..., 8): base_mean, mtn_mean, mtn_max, u_wmaj, u_wmin, u_slope, u_hang, s_mean."""
    from . import ocean, mountains          # lazy: avoid import cycles with sibling modules
    s = REGIONAL_STENCIL
    offs = (-s, 0.0, s)
    # evaluate all 9 stencil taps in one call (cheaper than 9 small calls)
    XS = np.stack([xn + dx for dy in offs for dx in offs])
    YS = np.stack([yn + dy for dy in offs for dx in offs])
    # don't let these helper queries evict the chunk grid from the siblings' tiny LRU caches
    saved = [(m, list(m._CACHE)) for m in (ocean, mountains) if isinstance(getattr(m, '_CACHE', None), list)]
    try:
        base, land = ocean.continent(XS, YS)
        mtn = mountains.height(XS, YS, land)
        sc = np.clip(_coast_distance(XS, YS), -50e3, 5e6).mean(axis=0)
    finally:
        for m, c in saved:
            m._CACHE[:] = c
    base = np.where(land > 0, np.maximum(base, 0.0), 0.0)
    bsum = base.mean(axis=0); msum = np.maximum(mtn, 0.0).mean(axis=0)
    mmax = np.maximum(mtn, 0.0).max(axis=0)
    u1 = N.fbm(xn, yn, _S_WIDTH_MAJ, 1.0 / 45000.0, 2)
    u2 = N.fbm(xn, yn, _S_WIDTH_MIN, 1.0 / 20000.0, 2)
    u3 = N.fbm(xn, yn, _S_SLOPE, 1.0 / 30000.0, 2)
    u4 = N.fbm(xn, yn, _S_HANG, 1.0 / 35000.0, 2)
    return np.stack([bsum, msum, mmax, u1, u2, u3, u4, sc], axis=-1)


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
    Three evaluation paths that give bit-identical results for the same point (same node values,
    same weights, same summation order: sum_b wy_b * (sum_a wx_a * G)):
      * axis-aligned grid (chunk meshgrid): separable, x pass then y pass
      * compact point cloud: one dense block of nodes, 16 gathers
      * scattered points: only the distinct nodes they touch."""
    def weights(f):
        i = np.floor(f).astype(np.int64); t = f - i
        if cubic:
            return i - 1, _bspline_w(t)
        return i, (1.0 - t, t)

    grid = (X.ndim == 2 and X.shape[0] > 1 and X.shape[1] > 1 and
            np.array_equal(X, np.broadcast_to(X[:1, :], X.shape)) and
            np.array_equal(Y, np.broadcast_to(Y[:, :1], Y.shape)))
    if grid:
        jx, wx = weights(X[0] / S); jy, wy = weights(Y[:, 0] / S)
        m = len(wx)
        ix0, ix1 = jx.min(), jx.max() + m - 1
        iy0, iy1 = jy.min(), jy.max() + m - 1
    if grid and not _dense_ok(ix0, ix1, iy0, iy1, X.size):
        grid = False                 # coarse overview grid: nodes >> points, go scattered
    if grid:
        IX, IY = np.meshgrid(np.arange(ix0, ix1 + 1), np.arange(iy0, iy1 + 1))
        G = node_fn(IX, IY, True).reshape(IX.shape + (k,))
        A = np.zeros((G.shape[0], jx.size, k))
        for a in range(m):
            A += wx[a][None, :, None] * G[:, jx - ix0 + a, :]
        out = np.zeros((jy.size, jx.size, k))
        for b in range(m):
            out += wy[b][:, None, None] * A[jy - iy0 + b]
        return out

    ix, wx = weights(X.ravel() / S); iy, wy = weights(Y.ravel() / S)
    m = len(wx)
    ix0, ix1 = ix.min(), ix.max() + m - 1
    iy0, iy1 = iy.min(), iy.max() + m - 1
    if _dense_ok(ix0, ix1, iy0, iy1, ix.size):
        IX, IY = np.meshgrid(np.arange(ix0, ix1 + 1), np.arange(iy0, iy1 + 1))
        nx = IX.shape[1]
        G = node_fn(IX, IY, True).reshape(-1, k)
        flat = (iy - iy0) * nx + (ix - ix0)
        taps = [np.take(G, flat + (b * nx + a), axis=0) for b in range(m) for a in range(m)]
    else:
        taps = _unique_nodes(lambda a, b: node_fn(a, b, False),
                             [(ix + a, iy + b) for b in range(m) for a in range(m)])
    out = np.zeros((ix.size, k))
    for b in range(m):
        row = np.zeros((ix.size, k))
        for a in range(m):
            row += wx[a][:, None] * taps[b * m + a]
        out += wy[b][:, None] * row
    return out.reshape(X.shape + (k,))


def _regional(X, Y):
    """Regional fields (B-spline over the REGIONAL_SPACING lattice) at points -> (..., 7)."""
    S = REGIONAL_SPACING
    return _lattice_interp(lambda IX, IY, g: _regional_nodes(*_node_xy(IX, IY, S)),
                           X, Y, S, 8, cubic=True)


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


def _minor_nodes(IX, IY, g):
    sd = _sd_nodes(NW.minor_distance, IX, IY, MINOR_LATTICE, 0.25 * NW.MINOR_FREQ, MINOR_CLAMP, g)
    lump = N.perlin(*_node_xy(IX, IY, MINOR_LATTICE), _S_WALL, 1.0 / 2600.0)
    return np.concatenate([sd, lump[..., None]], axis=-1)


def _sdist_minor(X, Y):
    """(signed minor distance, wall-lump noise) at points."""
    R = _lattice_interp(_minor_nodes, X, Y, MINOR_LATTICE, 2, cubic=True)
    return R[..., 0], R[..., 1]


_DERIVED = ('floor_major', 'floor_minor', 'width_major', 'width_minor', 'relief', '_sv')


def _derived(xn, yn):
    """Smooth per-position valley parameters from the regional fields -> (..., 10)."""
    F = _regional(xn, yn)
    base, mtn_mean, mtn_max = F[..., 0], F[..., 1], F[..., 2]
    u_wM, u_wm, u_s, u_h = (np.clip(0.5 + 0.9 * F[..., i], 0, 1) for i in (3, 4, 5, 6))
    # ridges avoid the channel lines, so the box mean under-reads relief right at a trunk; blend
    # in the box max so a trunk crossing a range still counts as "in the mountains".
    relief = _ss(RELIEF_RANGE[0], RELIEF_RANGE[1], np.maximum(mtn_mean, MAX_RELIEF_W * mtn_max))
    coast = _ss(0.0, 500.0, base)                        # trough fades out at the coast
    # Trunk floor: a smooth profile that is MONOTONE in coast distance s (so it drains to the
    # sea even across the flat, undulating interior dome), capped to stay >= TROUGH_MIN below the
    # local smoothed ice surface.
    sc = F[..., 7]
    u = np.clip(sc / DOME_L, 0.0, 1.0)
    dome = PLATEAU_HEIGHT * np.sqrt(u * (2.0 - u))
    tilt = INTERIOR_TILT * np.clip((sc - DOME_L) / INTERIOR_TILT_LEN, 0.0, 1.0)
    f_mono = dome * (1.0 - FLOOR_DOME_MARGIN) - FLOOR_DROP + tilt
    f_cap = base - TROUGH_MIN * _ss(0.0, 300.0, base)
    floor_M = np.maximum(np.minimum(f_mono, f_cap), MIN_FLOOR)
    hang = _lerp(HANG_MOUNTAIN[0], HANG_MOUNTAIN[1], u_h) * relief + MINOR_LIFT * mtn_mean
    floor_m = base - MINOR_PLATEAU_DEPTH * coast + hang
    floor_m = np.maximum(np.maximum(floor_m, floor_M + 30.0 * coast), MIN_FLOOR)
    return np.stack([
        floor_M, floor_m,
        _lerp(MAJOR_HALF_FLOOR[0], MAJOR_HALF_FLOOR[1], u_wM),
        _lerp(MINOR_HALF_FLOOR[0], MINOR_HALF_FLOOR[1], u_wm),
        relief, 0.85 + 0.3 * u_s,
    ], axis=-1)


def _derived_fine(X, Y):
    """_derived() evaluated on the MAJOR_LATTICE nodes and bilinearly resampled at points (the
    fields are smooth on a >= 8 km scale, so this is visually exact and much cheaper)."""
    S = MAJOR_LATTICE
    return _lattice_interp(lambda IX, IY, g: _derived(*_node_xy(IX, IY, S)),
                           X, Y, S, len(_DERIVED), cubic=False)


def _cache_key(X, Y):
    return (X.shape, hash(X.tobytes()), hash(Y.tobytes()))


# --------------------------------------------------------------------------- public API
def valley_info(X, Y, h=None, land=None):
    """Valley geometry at world points (X, Y). Pure & deterministic; h / land are accepted for
    API symmetry but NOT used (all geometry is derived from world position alone, so calling it
    before or after carving gives identical results). Cached for repeated identical grids.

    Returned dict (all arrays shaped like X, float64, metres unless noted):
      dist_major  unsigned distance to the nearest major (trunk) centre-line, clamped <= 60 km
      dist_minor  unsigned distance to the nearest minor (tributary) centre-line, clamped <= 20 km
      sdist_major / sdist_minor   signed versions (sign = side of the channel)
      floor_major trunk floor elevation here (smooth field, defined everywhere, >= MIN_FLOOR on
                  land). Inside the trunk floor (dist_major < width_major) the carved surface
                  is exactly this height (unless the original terrain was already lower).
      floor_minor tributary floor elevation (always >= floor_major + ~30 m where relief exists
                  -> hanging valleys). Carved surface == this inside the minor floor, except
                  where the trunk cuts deeper.
      width_major HALF-width of the flat trunk floor (1.0-2.5 km -> floor 2-5 km wide)
      width_minor HALF-width of the flat tributary floor (0.25-0.75 km)
      mask        0..1 valley influence: 1 on a (major or minor) floor, fading to 0 across the
                  wall toe. Multiplied by the land fade.
      floor_mask_major / floor_mask_minor   1 on that floor, 0 past the toe (no land fade)
      floor       effective floor height: floor_major on/near the trunk, else floor_minor
      minor_strength 0..1 where tributaries exist (relief, or plateau within ~6-16 km of a trunk)
      relief      0..1 regional mountain-relief factor (0 flat plateau, 1 full ranges)
      carve_fade  0..1 land fade applied by carve()
    Rivers: lay trunk ice at floor_major where dist_major < width_major (use sdist_major for
    across-channel position; the centre-line is sdist_major == 0, same zero line as network.py).
    """
    X = np.asarray(X, dtype=np.float64); Y = np.asarray(Y, dtype=np.float64)
    key = _cache_key(X, Y)
    for k, v in _CACHE:
        if k == key:
            return v

    sdM = _sdist_major(X, Y)
    sdm, lump = _sdist_minor(X, Y)
    D = _derived_fine(X, Y)
    info = {name: np.ascontiguousarray(D[..., i]) for i, name in enumerate(_DERIVED)}
    rel = info['relief']; sv = info.pop('_sv')
    info['toe_major'] = _lerp(MAJOR_TOE[0], MAJOR_TOE[1], rel)
    info['toe_minor'] = _lerp(MINOR_TOE[0], MINOR_TOE[1], rel)
    info['slope_major'] = _lerp(MAJOR_WALL_SLOPE[0], MAJOR_WALL_SLOPE[1], rel) * sv
    info['slope_minor'] = _lerp(MINOR_WALL_SLOPE[0], MINOR_WALL_SLOPE[1], rel) * sv
    info['shoulder_k'] = _lerp(SHOULDER_K[0], SHOULDER_K[1], rel)
    wM, wm = info['width_major'], info['width_minor']
    dM = np.abs(sdM); dm = np.abs(sdm)
    fmM = 1.0 - _ss(wM, wM + info['toe_major'], dM)
    # tributaries exist in relief and near trunks; the open plateau stays mostly smooth
    minor_on = np.maximum(np.sqrt(info['relief']),
                          1.0 - _ss(MINOR_NEAR_TRUNK[0], MINOR_NEAR_TRUNK[1], dM))
    minor_on = _ss(0.0, 1.0, minor_on)
    fmm = (1.0 - _ss(wm, wm + info['toe_minor'], dm)) * minor_on

    if land is None:
        from . import ocean
        land = ocean.continent(X, Y)[1]
    fade = _ss(LAND_FADE[0], LAND_FADE[1], np.asarray(land, dtype=np.float64))

    info.update(
        dist_major=dM, dist_minor=dm, sdist_major=sdM, sdist_minor=sdm,
        floor_mask_major=fmM, floor_mask_minor=fmm, minor_strength=minor_on,
        mask=np.maximum(fmM, fmm) * fade,
        floor=np.where(fmM >= fmm, info['floor_major'], info['floor_minor']),
        carve_fade=fade, _lump=lump,
    )
    _CACHE.insert(0, (key, info))
    del _CACHE[_CACHE_SIZE:]
    return info


def floor_height(X, Y, h=None, land=None):
    """Effective valley floor elevation (see valley_info()['floor'])."""
    return valley_info(X, Y, h, land)['floor']


def _wall(x, slope, toe):
    """U-profile rise above the floor at distance x past the floor edge: parabolic toe that
    reaches `slope` at x == toe, then a straight wall of that slope."""
    xc = np.minimum(x, toe)
    return (slope / (2.0 * toe)) * xc * xc + slope * (x - xc)


def _smin(a, b, k):
    t = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * t - k * t * (1.0 - t)


def carve(X, Y, h, land):
    h = np.asarray(h, dtype=np.float64)
    v = valley_info(X, Y, h, land)
    # lumpy walls: modulate wall height (0 on the floor) so walls get spurs and bays
    lump = 1.0 + WALL_NOISE * v['_lump']
    candM = v['floor_major'] + lump * _wall(np.maximum(v['dist_major'] - v['width_major'], 0.0),
                                            v['slope_major'], v['toe_major'])
    candm = v['floor_minor'] + lump * _wall(np.maximum(v['dist_minor'] - v['width_minor'], 0.0),
                                            v['slope_minor'], v['toe_minor'])
    candm = candm + (1.0 - v['minor_strength']) * 2000.0       # fade tributaries out
    k = v['shoulder_k']
    cand = _smin(candM, candm, 0.6 * k)
    out = _smin(h, cand, k)
    # smooth-min may dip below; never below the floor, never above the original terrain
    out = np.maximum(out, np.minimum(h, np.minimum(v['floor_major'], v['floor_minor'])))
    out = np.minimum(out, h)
    return h + (out - h) * v['carve_fade']


def surface(X, Y, H, land, masks):
    """Exposed rock on steep valley walls, clean snow/firn on valley floors."""
    v = valley_info(X, Y, H, land)
    slope = masks.get('slope')
    if slope is None:
        return
    near = np.maximum(1.0 - _ss(v['width_major'] + v['toe_major'], v['width_major'] + v['toe_major'] + 3000.0,
                                v['dist_major']),
                      1.0 - _ss(v['width_minor'] + v['toe_minor'], v['width_minor'] + v['toe_minor'] + 1500.0,
                                v['dist_minor'])) * v['carve_fade']
    wall_rock = np.clip((slope - 0.42) / 0.3, 0.0, 1.0) * near
    rock = np.maximum(masks['rock'], wall_rock)
    floor = np.maximum(v['floor_mask_major'], v['floor_mask_minor']) * v['carve_fade']
    rock = rock * (1.0 - _ss(0.5, 0.95, floor))
    delta = rock - masks['rock']                      # move weight between rock and snow only
    masks['rock'] = rock
    masks['snow'] = np.clip(masks['snow'] - delta, 0.0, 1.0)


def chunk_objects(ctx):
    return []
