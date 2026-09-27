"""Mountain ranges and nunataks - owned by the mountains agent.

height(X, Y, land) returns additive metres on top of the ice-sheet base:
  * NAMED RANGES (RANGES below): long, jittered, domain-warped crest polylines with a smooth
    cross-profile. Peaks reach ~0.9-1.0 x the range amplitude above the plateau
    (Transantarctic ~3 200 m, Ellsworth ~3 600 m).
  * NOISE BELTS: the zero-contours of a very low frequency (1/380 km) warped noise, gated on/off
    by a 1/300 km mask, give secondary elongated ranges elsewhere; most of the continent stays
    flat ice plateau.
  * Inside a range the massif is (drainage structure) x (ridged multifractal): height is
    suppressed towards network.major/minor channel centre-lines (so valleys.py carving and our
    ridges agree; ridges sit on the watersheds between channels), with 7 ridged octaves
    (16 km -> 250 m wavelength) for sharp crests / aretes and a Worley pass for cirque bowls.
  * NUNATAKS: sparse isolated rock peaks (10 km cells) on the plateau, denser on range fringes.

Everything is a pure per-point function of world metres. Smooth, low-frequency inputs
(range envelope, network distances, warp offsets, the three lowest octaves) are evaluated on a
WORLD-ALIGNED 500 m lattice and bilinearly interpolated: the lattice is identical for every
chunk, so seams still match exactly, and it is ~20x cheaper than evaluating the network per
vertex. High octaves use a local float32 gradient noise (about 3x faster than noise.perlin).
"""
import numpy as np
from . import noise as N
from . import network
from .config import SEED, SPAWN

# ----------------------------------------------------------------------------- parameters
LATTICE = 500.0                 # m, macro-field lattice spacing
RIDGE_LOW_FREQS = (1 / 16000.0, 1 / 8000.0, 1 / 4000.0)     # on lattice
RIDGE_HIGH_FREQS = (1 / 2000.0, 1 / 1000.0, 1 / 500.0, 1 / 250.0)  # per vertex (>=250 m)
RIDGE_GAIN = 0.62
DETAIL_WARP_FREQ = 1 / 24000.0
DETAIL_WARP_AMT = 3000.0

# drainage suppression (metres from channel centre-line)
MAJOR_CLAMP = 30000.0           # network distance blows up near saddles -> clamp
MINOR_CLAMP = 8000.0
MAJOR_IN, MAJOR_OUT = 800.0, 7000.0     # floor at <= IN, full height at >= OUT (linear ramp)
MINOR_IN, MINOR_OUT = 150.0, 5000.0     # > half tributary spacing -> creased watersheds
MINOR_FLOOR = 0.38              # height fraction kept on tributary centre-lines
MAJOR_FLOOR = 0.22              # height fraction kept on trunk centre-lines

# range crest warp
RANGE_WARP_FREQ = 1 / 70000.0
RANGE_WARP_AMT = 9000.0

# noise belts (secondary ranges)
BELT_FREQ = 1 / 520000.0
BELT_GATE_FREQ = 1 / 300000.0   # the ~1/300 km range mask: which belts are mountains
BELT_WIDTH = 34000.0
BELT_AMP = 2100.0
BELT_GATE = (0.0, 0.30)
BELT_TRENDS = (28.0, -52.0)      # degrees; two regional grain directions
BELT_ANISO = 4.0                # along-trend stretch of the belt noise

# cirques
CIRQUE_CELL = 4200.0
CIRQUE_PROB = 0.65
CIRQUE_DEPTH = 0.38             # fraction of local height removed at bowl floor
CIRQUE_BAND = (0.10, 0.30)     # relative height band (h / range amp) where cirques bite
# nunataks
NUNATAK_CELL = 10000.0
NUNATAK_PROB = 0.40
NUNATAK_HEIGHT = (140.0, 750.0)
NUNATAK_RADIUS = (1100.0, 3000.0)
NUNATAK_ASPECT = 2.0            # max elongation; radius*aspect must stay < 0.7 cell (2x2 search)
PEAK_GAIN = 1.45                # overall scale so the highest crests reach ~range amplitude
MASSIF_BASE = 0.05              # massif height fraction where the ridged noise is 0
MASSIF_POW = 1.6                # >1 sharpens peaks and broadens valleys
NUNATAK_PLATEAU = 0.8           # max nunatak density on open plateau (fringes reach 1)

KM = 1000.0

# Named ranges: (name, control points in km, amplitude m, half-width km).
# The Transantarctic crest runs SW->NE ~30 km north-west of SPAWN; the Aurora Spur ~28 km to its
# south-east, so the spawn sits in a broad glacier corridor between two ranges.
RANGES = [
    ("Transantarctic Range",
     [(-1650, -1050), (-1150, -900), (-650, -660), (-200, -330), (260, -40), (690, 250),
      (1030, 446), (1360, 690), (1620, 990), (1800, 1290)], 3200.0, 55.0),
    ("Aurora Spur",
     [(930, 300), (1070, 392), (1200, 452), (1300, 470)], 1900.0, 22.0),
    ("Ellsworth Massif",
     [(-980, 560), (-860, 790), (-740, 1000), (-690, 1120)], 3600.0, 42.0),
    ("Queen Maud Range",
     [(380, -1680), (780, -1520), (1180, -1270), (1450, -960)], 2600.0, 45.0),
    ("Prince Charles Range",
     [(-1780, -160), (-1530, 150), (-1370, 500)], 2200.0, 36.0),
    ("Vostok Uplands",
     [(-420, 380), (-170, 560), (120, 640)], 1500.0, 38.0),
]
_JITTER_KM = 12.0               # perpendicular wiggle of the crest polyline
_SEG_KM = 12.0


# ----------------------------------------------------------------------------- fast noise
_GA = (np.cos(np.linspace(0, 2 * np.pi, 16, endpoint=False)) * 1.41421356).astype(np.float32)
_GB = (np.sin(np.linspace(0, 2 * np.pi, 16, endpoint=False)) * 1.41421356).astype(np.float32)
_GC = (_GA + 1j * _GB).astype(np.complex64)   # one gather per corner


def _pn(X, Y, seed, freq):
    """float32 gradient noise ~[-1,1]; arithmetic hash (no perm table), elementwise-pure."""
    x = X * freq; y = Y * freq
    xf = np.floor(x); yf = np.floor(y)
    fx = (x - xf).astype(np.float32); fy = (y - yf).astype(np.float32)
    ix = xf.astype(np.int32); iy = yf.astype(np.int32)
    hx0 = ix * np.int32(374761393); hx1 = hx0 + np.int32(374761393)
    hy0 = iy * np.int32(668265263) + np.int32((seed * 1013904223) & 0x7FFFFFFF)
    hy1 = hy0 + np.int32(668265263)

    def g(hx, hy, dx, dy):
        h = hx ^ hy
        h ^= h >> 13
        h *= np.int32(1274126177)
        h >>= 28
        h &= 15
        c = _GC[h]
        return c.real * dx + c.imag * dy

    fx1 = fx - 1; fy1 = fy - 1
    n00 = g(hx0, hy0, fx, fy); n10 = g(hx1, hy0, fx1, fy)
    n01 = g(hx0, hy1, fx, fy1); n11 = g(hx1, hy1, fx1, fy1)
    u = fx * fx * fx * (fx * (fx * 6 - 15) + 10)
    v = fy * fy * fy * (fy * (fy * 6 - 15) + 10)
    a = n00 + u * (n10 - n00); b = n01 + u * (n11 - n01)
    return a + v * (b - a)


def _fbm(X, Y, seed, freq, octaves):
    t = 0.0; amp = 1.0; norm = 0.0
    for o in range(octaves):
        t = t + amp * _pn(X, Y, seed + 31 * o, freq)
        norm += amp; amp *= 0.5; freq *= 2.0
    return t / norm


def _sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _hash(ix, iy, seed):
    """uniform [0,1) per integer cell, int64 arithmetic."""
    h = (ix * 73856093) ^ (iy * 19349663) ^ (seed * 83492791)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF).astype(np.float64) / float(0x1000000)


def _ridge_op(n, weight):
    r = 1.0 - np.abs(n)
    r = r * r * weight
    return r, np.minimum(r * 1.5, 1.0)


# ----------------------------------------------------------------------------- named ranges
def _build_polylines():
    rng = np.random.default_rng(SEED + 4242)
    segs = []                         # rows: ax, ay, bx, by, s0, s1, L, amp, width, id
    for rid, (name, pts, amp, wkm) in enumerate(RANGES):
        P = np.array(pts, dtype=np.float64)
        # Catmull-Rom densify
        Pp = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
        out = []
        for i in range(1, len(Pp) - 2):
            p0, p1, p2, p3 = Pp[i - 1], Pp[i], Pp[i + 1], Pp[i + 2]
            n = max(2, int(np.ceil(np.linalg.norm(p2 - p1) / _SEG_KM)))
            for t in np.linspace(0, 1, n, endpoint=False):
                t2, t3 = t * t, t * t * t
                out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
        out.append(P[-1])
        C = np.array(out)
        # perpendicular jitter (sum of random sines along arc length), tapered at the ends
        d = np.diff(C, axis=0); L = np.linalg.norm(d, axis=1)
        s = np.concatenate([[0], np.cumsum(L)])
        tang = np.gradient(C, axis=0); tang /= np.linalg.norm(tang, axis=1)[:, None] + 1e-9
        nrm = np.stack([-tang[:, 1], tang[:, 0]], 1)
        j = np.zeros(len(C))
        for k, wl in enumerate((160.0, 70.0, 33.0)):
            j += np.sin(2 * np.pi * s / wl + rng.uniform(0, 2 * np.pi)) / (k + 1)
        j *= _JITTER_KM / 1.83 * np.clip(np.minimum(s, s[-1] - s) / 40.0, 0.2, 1.0)
        # keep the crest near the spawn where it was placed
        sp = np.array(SPAWN) / KM
        j *= np.clip((np.linalg.norm(C - sp, axis=1) - 40.0) / 80.0, 0.0, 1.0)
        C = (C + nrm * j[:, None]) * KM
        s = s * KM
        for i in range(len(C) - 1):
            segs.append((C[i, 0], C[i, 1], C[i + 1, 0], C[i + 1, 1], s[i], s[i + 1], s[-1],
                         amp, wkm * KM, rid))
    return np.array(segs)


_SEGS = _build_polylines()


def _named_ranges(X, Y):
    """amp-weighted envelope (metres) and envelope [0,1] from the named crest polylines.
    X, Y: 1-D lattice coords (already warped)."""
    n = X.size
    best_amp = np.zeros(n); best_env = np.zeros(n); rid_out = np.full(n, -1)
    if n == 0:
        return best_amp, best_env, rid_out
    x0, x1, y0, y1 = X.min(), X.max(), Y.min(), Y.max()
    S = _SEGS
    W = S[:, 8]
    keep = ((np.minimum(S[:, 0], S[:, 2]) - W <= x1) & (np.maximum(S[:, 0], S[:, 2]) + W >= x0) &
            (np.minimum(S[:, 1], S[:, 3]) - W <= y1) & (np.maximum(S[:, 1], S[:, 3]) + W >= y0))
    S = S[keep]
    for rid in np.unique(S[:, 9]).astype(int):
        R = S[S[:, 9] == rid]
        ax, ay, bx, by, s0, s1, L, amp, w = (R[:, k][:, None] for k in range(9))
        # chunk the points to bound memory
        for a in range(0, n, 65536):
            px = X[None, a:a + 65536]; py = Y[None, a:a + 65536]
            dx, dy = bx - ax, by - ay
            t = np.clip(((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy), 0.0, 1.0)
            ex = px - (ax + t * dx); ey = py - (ay + t * dy)
            d2 = ex * ex + ey * ey
            k = np.argmin(d2, axis=0)
            cols = np.arange(d2.shape[1])
            d = np.sqrt(d2[k, cols])
            sarc = s0[k, 0] + t[k, cols] * (s1[k, 0] - s0[k, 0])
            Ltot = L[0, 0]; ww = w[0, 0]
            end_taper = _sstep(0.0, 0.9 * ww, np.minimum(sarc, Ltot - sarc))
            env = (1.0 - _sstep(0.12, 1.0, d / ww)) * (0.35 + 0.65 * end_taper)
            env = np.where(d < ww, env, 0.0)
            ampv = amp[0, 0] * env
            sl = slice(a, a + 65536)
            better = ampv > best_amp[sl]
            best_amp[sl] = np.where(better, ampv, best_amp[sl])
            best_env[sl] = np.maximum(best_env[sl], env)
            rid_out[sl] = np.where(better & (env > 0), rid, rid_out[sl])
    return best_amp, best_env, rid_out


# ----------------------------------------------------------------------------- macro lattice
def _macro(X, Y):
    """Smooth fields at lattice nodes (1-D arrays). Returns (n, 7) float32."""
    s = SEED + 900
    # range crest warp
    rx = X + RANGE_WARP_AMT * _fbm(X, Y, s + 1, RANGE_WARP_FREQ, 2)
    ry = Y + RANGE_WARP_AMT * _fbm(X, Y, s + 2, RANGE_WARP_FREQ, 2)
    amp, env, _ = _named_ranges(rx, ry)

    # noise belts: zero-contours of very low frequency noise, stretched along two regional
    # "tectonic grain" directions -> long, gently curving secondary ranges (not blobs)
    sel = _sstep(-0.25, 0.25, _pn(X, Y, s + 8, 1 / 900000.0))
    benv = np.zeros_like(amp)
    for fam, (ang, sel_w) in enumerate(((BELT_TRENDS[0], sel), (BELT_TRENDS[1], 1.0 - sel))):
        ca, sa = np.cos(np.radians(ang)), np.sin(np.radians(ang))

        def bn(px, py):
            u = (px * ca + py * sa) / BELT_ANISO; v = -px * sa + py * ca
            return _pn(u, v, s + 5 + 17 * fam, BELT_FREQ).astype(np.float64)
        e = 2000.0
        b0 = bn(rx, ry)
        bgx = (bn(rx + e, ry) - b0) / e; bgy = (bn(rx, ry + e) - b0) / e
        bd = np.minimum(np.abs(b0) / (np.sqrt(bgx * bgx + bgy * bgy) + 1e-12), 5 * BELT_WIDTH)
        gate = _sstep(BELT_GATE[0], BELT_GATE[1], _pn(X, Y, s + 6 + 17 * fam, BELT_GATE_FREQ))
        benv = np.maximum(benv, (1.0 - _sstep(0.12, 1.0, bd / BELT_WIDTH)) * gate * sel_w)
    bamp = BELT_AMP * benv
    amp = np.maximum(amp, bamp); env = np.maximum(env, benv)
    # along-range amplitude variation -> distinct high massifs and lower cols
    amp = amp * (0.82 + 0.30 * _fbm(X, Y, s + 7, 1 / 90000.0, 2))

    # drainage network (shared contract) - clamp the saddle blow-ups. Structure factor:
    # MAJOR_FLOOR on trunk channels, MINOR_FLOOR on tributaries, 1 on the watersheds between
    # them -> ridges sit between the valleys carved by valleys.py
    dM, _ = network.major_distance(X, Y)
    dm, _ = network.minor_distance(X, Y)
    # linear ramps (not smoothsteps): the distance field's medial axis stays a sharp crease,
    # i.e. an arete along the watershed; a smoothstep would round it into blobs
    sM = np.clip((np.minimum(dM, MAJOR_CLAMP) - MAJOR_IN) / (MAJOR_OUT - MAJOR_IN), 0.0, 1.0)
    sM = sM * (2.0 - sM) * 0.5 + sM * 0.5          # slightly convex valley walls
    sm = np.clip((np.minimum(dm, MINOR_CLAMP) - MINOR_IN) / (MINOR_OUT - MINOR_IN), 0.0, 1.0)
    struct = (MAJOR_FLOOR + (1 - MAJOR_FLOOR) * sM) * (MINOR_FLOOR + (1 - MINOR_FLOOR) * sm)

    # detail warp + the three lowest ridged octaves (partial sum and cascade weight)
    wx = DETAIL_WARP_AMT * _fbm(X, Y, s + 11, DETAIL_WARP_FREQ, 2)
    wy = DETAIL_WARP_AMT * _fbm(X, Y, s + 12, DETAIL_WARP_FREQ, 2)
    rlo = 0.0; wgt = 1.0; ao = 1.0
    for i, f in enumerate(RIDGE_LOW_FREQS):
        r, wgt = _ridge_op(_pn(X + wx, Y + wy, s + 20 + i, f), wgt)
        rlo = rlo + ao * r; ao *= RIDGE_GAIN

    # nunatak density: sparse on the plateau, clustered, denser on range fringes; rising out
    # of the drainage-suppressed terrain
    nd = _sstep(0.12, 0.55, _fbm(X, Y, s + 30, 1 / 260000.0, 2)) * NUNATAK_PLATEAU
    fringe = _sstep(0.0, 0.08, env) * (1.0 - _sstep(0.25, 0.5, env))
    nd = np.clip(nd + fringe, 0.0, 1.0) * (1.0 - _sstep(0.3, 0.6, env)) * (0.35 + 0.65 * sM)

    ampe = amp * (0.55 + 0.45 * env) ** 1.25 * PEAK_GAIN
    return np.stack([ampe, struct, wx, wy, rlo, wgt, nd], axis=1).astype(np.float32)


_F_AMP, _F_STRUCT, _F_WX, _F_WY, _F_RLO, _F_WGT, _F_ND = range(7)


def _bspline_w(t):
    """Uniform cubic B-spline weights (C2: no creases along lattice lines, no overshoot)."""
    t2 = t * t; t3 = t2 * t; it = 1.0 - t
    return (it * it * it * np.float32(1 / 6), (3 * t3 - 6 * t2 + 4) * np.float32(1 / 6),
            (-3 * t3 + 3 * t2 + 3 * t + 1) * np.float32(1 / 6), t3 * np.float32(1 / 6))


def _lattice(X, Y, fn, s=LATTICE):
    """Cubic B-spline interpolation of fn() sampled on the world-aligned lattice (spacing s).
    Pure per point: node values depend only on node coordinates, and the regular-grid fast
    path performs exactly the same float32 operations per point as the general path.
    Returns (X.size, k) float32 in X's row-major order."""
    X = np.asarray(X); Y = np.asarray(Y)
    grid = (X.ndim == 2 and X.shape[0] > 1 and X.shape[1] > 1
            and bool((X == X[:1]).all()) and bool((Y == Y[:, :1]).all()))
    xs, ys = (X[0], Y[:, 0]) if grid else (X.ravel(), Y.ravel())
    gx = xs / s; gy = ys / s
    fx0 = np.floor(gx); fy0 = np.floor(gy)
    wx = _bspline_w((gx - fx0).astype(np.float32)[:, None])
    wy = _bspline_w((gy - fy0).astype(np.float32)[:, None])
    ix = fx0.astype(np.int64); iy = fy0.astype(np.int64)
    x0, x1 = int(ix.min()) - 1, int(ix.max()) + 2
    y0, y1 = int(iy.min()) - 1, int(iy.max()) + 2
    nx, ny = x1 - x0 + 1, y1 - y0 + 1
    if grid or nx * ny <= max(16 * X.size, 4096):
        LX, LY = np.meshgrid(np.arange(x0, x1 + 1, dtype=np.int64), np.arange(y0, y1 + 1, dtype=np.int64))
        F = fn(LX.ravel().astype(np.float64) * s, LY.ravel().astype(np.float64) * s)
        k = F.shape[1]
        cx = ix - 1 - x0; cy = iy - 1 - y0
        if grid:
            F = F.reshape(ny, nx, k)
            wxg = [w[None] for w in wx]                          # (1, ncols, 1)
            A = wxg[0] * F[:, cx] + wxg[1] * F[:, cx + 1] + wxg[2] * F[:, cx + 2] + wxg[3] * F[:, cx + 3]
            wyg = [w[:, None] for w in wy]                       # (nrows, 1, 1)
            out = wyg[0] * A[cy] + wyg[1] * A[cy + 1] + wyg[2] * A[cy + 2] + wyg[3] * A[cy + 3]
            return out.reshape(-1, k)
        rows = []
        for r in range(4):
            b0 = (cy + r) * nx + cx
            rows.append(wx[0] * F[b0] + wx[1] * F[b0 + 1] + wx[2] * F[b0 + 2] + wx[3] * F[b0 + 3])
    else:   # sparse, widely spread samples: evaluate only the needed nodes
        B = 1 << 24; H = B >> 1                  # lattice index range +-8.4M nodes
        kx = np.concatenate([ix + (j - 1) for r in range(4) for j in range(4)])
        ky = np.concatenate([iy + (r - 1) for r in range(4) for j in range(4)])
        uk, inv = np.unique((kx + H) * B + (ky + H), return_inverse=True)
        F = fn((uk // B - H).astype(np.float64) * s, (uk % B - H).astype(np.float64) * s)
        inv = inv.reshape(4, 4, -1)
        rows = [wx[0] * F[inv[r, 0]] + wx[1] * F[inv[r, 1]] + wx[2] * F[inv[r, 2]] + wx[3] * F[inv[r, 3]]
                for r in range(4)]
    return wy[0] * rows[0] + wy[1] * rows[1] + wy[2] * rows[2] + wy[3] * rows[3]


class _Cells:
    """Jittered-feature cell grid over the samples (X, Y). For each point, the 4 cells that can
    hold a feature closer than ~0.65 cell (own cell + neighbours on the side of the nearest
    edges; exact for features jittered in [0.15, 0.85] of the cell). Per-cell parameters are
    computed once per cell of the bounding box from the cell index only -> pure."""

    def __init__(self, X, Y, c):
        gx = X / c; gy = Y / c
        fx0 = np.floor(gx); fy0 = np.floor(gy)
        ix = fx0.astype(np.int64); iy = fy0.astype(np.int64)
        self.x0 = int(ix.min()) - 1; self.y0 = int(iy.min()) - 1
        self.nx = int(ix.max()) + 2 - self.x0; self.ny = int(iy.max()) + 2 - self.y0
        base = ((iy - self.y0) * self.nx + (ix - self.x0)).astype(np.int32)
        ox = np.where(gx - fx0 < 0.5, -1, 1).astype(np.int32)
        oy = np.where(gy - fy0 < 0.5, -self.nx, self.nx).astype(np.int32)
        self.cand = (base, base + ox, base + oy, base + ox + oy)
        # float32 position relative to each candidate cell's corner. Depends only on the point
        # and cell index (never on the bbox), so neighbouring chunks round identically.
        lx = (X - fx0 * c).astype(np.float32); ly = (Y - fy0 * c).astype(np.float32)
        sx = (ox * c).astype(np.float32); sy = (np.sign(oy) * c).astype(np.float32)
        self.rel = ((lx, ly), (lx - sx, ly), (lx, ly - sy), (lx - sx, ly - sy))

    def table(self, fn):
        CX, CY = np.meshgrid(np.arange(self.x0, self.x0 + self.nx, dtype=np.int64),
                             np.arange(self.y0, self.y0 + self.ny, dtype=np.int64))
        return fn(CX.ravel(), CY.ravel())


def _cirques(X, Y, seed):
    """Bowl factor in [0,1] (1 = bowl floor) from a jittered Worley grid (F1)."""
    c = CIRQUE_CELL
    C = _Cells(X, Y, c)

    def params(cx, cy):
        pres = _hash(cx, cy, seed) < CIRQUE_PROB
        px = (0.15 + 0.7 * _hash(cx, cy, seed + 1)) * c       # relative to the cell corner
        py = (0.15 + 0.7 * _hash(cx, cy, seed + 2)) * c
        return np.where(pres, px, 1e9).astype(np.float32), py.astype(np.float32)
    PX, PY = C.table(params)
    d2 = None
    for k, (lx, ly) in zip(C.cand, C.rel):
        dx = lx - PX[k]; dy = ly - PY[k]
        q = dx * dx + dy * dy
        d2 = q if d2 is None else np.minimum(d2, q)
    R = 0.62 * c
    return 1.0 - _sstep(np.float32(0.35 * R), np.float32(R), np.sqrt(d2))


def _nunataks(X, Y, seed):
    """Isolated elongated rock cones (height in metres before detail)."""
    c = NUNATAK_CELL
    C = _Cells(X, Y, c)

    def params(cx, cy):
        pres = _hash(cx, cy, seed) < NUNATAK_PROB
        px = (0.2 + 0.6 * _hash(cx, cy, seed + 1)) * c
        py = (0.2 + 0.6 * _hash(cx, cy, seed + 2)) * c
        r0 = NUNATAK_RADIUS[0] + (NUNATAK_RADIUS[1] - NUNATAK_RADIUS[0]) * _hash(cx, cy, seed + 3)
        hh = NUNATAK_HEIGHT[0] + (NUNATAK_HEIGHT[1] - NUNATAK_HEIGHT[0]) * _hash(cx, cy, seed + 4) ** 1.5
        ang = np.pi * _hash(cx, cy, seed + 5)
        asp = 1.0 + (NUNATAK_ASPECT - 1.0) * _hash(cx, cy, seed + 6)
        ca, sa = np.cos(ang), np.sin(ang)
        return [v.astype(np.float32) for v in
                (px, py, ca / (asp * r0), sa / (asp * r0), ca / r0, sa / r0, np.where(pres, hh, 0.0))]
    P = C.table(params)
    out = None
    for k, (lx, ly) in zip(C.cand, C.rel):
        hh = P[6][k]
        dx = lx - P[0][k]; dy = ly - P[1][k]
        u = dx * P[2][k] + dy * P[3][k]; v = dy * P[4][k] - dx * P[5][k]
        cone = np.maximum(1.0 - np.sqrt(u * u + v * v), 0.0)
        cone = cone * np.sqrt(cone) * hh         # ^1.5 profile
        out = cone if out is None else np.maximum(out, cone)
    return out


def _coastal_relief(X, Y, land):
    """Broken coastal spurs, including a readable skyline around the arrival valley.

    Coordinates are world metres, never chunk-relative. Broad compact supports
    taper the local spurs into regional terrain without a circular rim or wall.
    Valley/river carving still runs after this additive field in world.height.
    """
    x = X - SPAWN[0]; y = Y - SPAWN[1]
    result = np.zeros_like(X, dtype=np.float64)
    # centre offsets, crest direction, along/across support, peak addition.
    for cx, cy, angle, length, width, amplitude in (
        (-3300., 1700., 1.05, 6500., 2300., 1150.),
        (2200., 4300., -0.35, 5100., 2100., 1050.),
        (-1800., -4400., -0.65, 5800., 2500., 950.),
    ):
        dx = x - cx; dy = y - cy
        ca, sa = np.cos(angle), np.sin(angle)
        u = ca * dx + sa * dy
        v = -sa * dx + ca * dy
        v += 330.0 * _fbm(X, Y, SEED + 1801, 1 / 2200., 2)
        taper = 1.0 - _sstep(0.25, 1.0, np.abs(u) / length)
        flank = np.maximum(1.0 - np.abs(v) / width, 0.0) ** 1.35
        saddles = 0.78 + 0.22 * _pn(X, Y, SEED + 1802, 1 / 1700.)
        result = np.maximum(result, amplitude * taper * flank * saddles)
    # Regional foothills have irregular, warped crests and spacious low areas.
    wx = X + 2200.0 * _fbm(X, Y, SEED + 1810, 1 / 17000., 2)
    wy = Y + 2200.0 * _fbm(X, Y, SEED + 1811, 1 / 17000., 2)
    gate = _sstep(-0.12, 0.4, _pn(X, Y, SEED + 1812, 1 / 65000.))
    ridge = np.maximum(1.0 - np.abs(_pn(wx, wy, SEED + 1813, 1 / 7200.)) * 2.8, 0.0) ** 2
    regional = 460.0 * gate * ridge
    # Leave an open arrival basin; the apron reaches full relief before the
    # nearby crests, with a smooth slope rather than a flattened circular edge.
    apron = _sstep(550.0, 1900.0, np.hypot(x, y))
    return np.maximum(result, regional) * apron * _sstep(0.25, 1.0, land)


def height(X, Y, land):
    X = np.asarray(X, dtype=np.float64); Y = np.asarray(Y, dtype=np.float64)
    shape = X.shape
    out = np.zeros(X.size)
    if X.size == 0:
        return out.reshape(shape)
    Xf = X.ravel(); Yf = Y.ravel()
    lf = np.broadcast_to(np.asarray(land, dtype=np.float64), shape).ravel()
    coastal = _coastal_relief(Xf, Yf, lf)
    F = _lattice(X if X.ndim == 2 else Xf, Y if Y.ndim == 2 else Yf, _macro)
    fade = _sstep(0.0, 1.0, lf.astype(np.float32))
    act = ((F[:, _F_AMP] > 1.0) | (F[:, _F_ND] > 1e-3)) & (fade > 0)
    if not act.any():
        return coastal.reshape(shape)
    if act.all():
        idx = slice(None); n = X.size
    else:
        idx = np.nonzero(act)[0]; F = F[idx]; n = idx.size
    x = Xf[idx]; y = Yf[idx]
    xw = x + F[:, _F_WX]; yw = y + F[:, _F_WY]
    s = SEED + 900

    # ridged multifractal, 7 octaves: 3 from the lattice, 4 per vertex (>= 250 m wavelength)
    total = F[:, _F_RLO].copy(); weight = F[:, _F_WGT]; ao = RIDGE_GAIN ** 3
    norm = sum(RIDGE_GAIN ** i for i in range(len(RIDGE_LOW_FREQS) + len(RIDGE_HIGH_FREQS)))
    for i, f in enumerate(RIDGE_HIGH_FREQS):
        r, weight = _ridge_op(_pn(xw, yw, s + 40 + i, f), weight)
        total += np.float32(ao) * r; ao *= RIDGE_GAIN
    ridge = total * np.float32(1.0 / norm)

    a = F[:, _F_AMP]
    massif = F[:, _F_STRUCT] * (MASSIF_BASE + (1.0 - MASSIF_BASE) * ridge)
    hm = a * massif ** np.float32(MASSIF_POW)             # >1: sharp tops, broad valleys

    # cirque bowls on the upper flanks (aretes / horns remain between adjacent bowls)
    cm = np.nonzero(a > 300.0)[0]
    if cm.size:
        w = _sstep(CIRQUE_BAND[0], CIRQUE_BAND[1], hm[cm] / (a[cm] + 1e-6))
        sub = np.nonzero(w > 0)[0]
        if sub.size:
            j = cm[sub]
            hm[j] *= 1.0 - CIRQUE_DEPTH * w[sub] * _cirques(xw[j], yw[j], s + 60)

    # nunataks (plateau + range fringes); ridged detail gives them crests and gullies
    nm = np.nonzero(F[:, _F_ND] > 1e-3)[0]
    if nm.size:
        nun = _nunataks(x[nm], y[nm], s + 80) * (0.55 + 0.75 * ridge[nm]) * F[nm, _F_ND]
        hm[nm] = np.maximum(hm[nm], nun)

    out[idx] = hm * fade[idx]
    return np.maximum(out, coastal).reshape(shape)


def range_name(x, y):
    """Name of the named range whose envelope dominates at world point (x, y), or None."""
    X = np.array([float(x)]); Y = np.array([float(y)])
    s = SEED + 900
    rx = X + RANGE_WARP_AMT * _fbm(X, Y, s + 1, RANGE_WARP_FREQ, 2)
    ry = Y + RANGE_WARP_AMT * _fbm(X, Y, s + 2, RANGE_WARP_FREQ, 2)
    _, env, rid = _named_ranges(rx, ry)
    return RANGES[int(rid[0])][0] if rid[0] >= 0 and env[0] > 0.05 else None


# ----------------------------------------------------------------------------- surface
def surface(X, Y, H, land, masks):
    """More rock on steep convex crests and nunatak tops; keep snow in concave bowls/lee."""
    if H.ndim != 2 or min(H.shape) < 3:
        return
    sp = float(abs(X[0, 1] - X[0, 0])) or 100.0
    slope = masks.get('slope')
    if slope is None:
        gy, gx = np.gradient(H, sp); slope = np.hypot(gx, gy)
    Hp = np.pad(H, 1, mode='edge')
    lap = (Hp[1:-1, :-2] + Hp[1:-1, 2:] + Hp[:-2, 1:-1] + Hp[2:, 1:-1] - 4 * H) / (sp * sp)
    lap = lap * (sp / 100.0)            # soften the spacing dependence across LODs
    convex = _sstep(0.0008, 0.004, -lap)
    concave = _sstep(0.0005, 0.003, lap)
    # break-up so rock appears in patches/bands, not a uniform mask
    brk = 0.5 + 0.5 * _pn(X, Y, SEED + 991, 1 / 700.0).astype(np.float64)
    crest_rock = convex * _sstep(0.30, 0.65, slope) * (0.55 + 0.45 * brk)
    rock = np.maximum(masks['rock'], np.minimum(crest_rock, 0.9))
    rock = rock * (1.0 - 0.8 * concave * (1.0 - _sstep(0.9, 1.4, slope)))  # snow in bowls
    rock = np.clip(rock, 0.0, 1.0)
    masks['rock'] = rock
    masks['snow'] = np.clip(1.0 - rock - masks.get('ice', 0.0) - masks.get('water', 0.0), 0.0, 1.0)


def chunk_objects(ctx):
    return []
