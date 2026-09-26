"""Continent outline, ice-sheet profile, sea floor, coast, sea ice and icebergs.
Owned by the ocean agent.

Everything height-related is a pure, vectorised function of world metres. Cost is kept low by
evaluating all noise ONCE at import onto world-fixed tables and interpolating at query time:

* _LAT   2-D lattice (LAT_D = 20 km) of low-frequency fields: domain warp, ice-sheet undulation,
         coast type, shelf/fjord/cliff controls, sea-floor variation.
* _TAB_R 1-D angular table (250 m knots on the CONTINENT_RADIUS circle) of the coastline radius
         R(theta) with large + medium + fine fractal detail. The continent is star-shaped in
         warped space  ->  NO inland lakes or random islets from coastline noise, by construction.
* peninsula / bay / island outlines use the same trick (noise tabulated along a curve or angle).
* the major drainage network (network.py) is sampled on a world-fixed 500 m lattice with true
  central-difference gradients (same approach as valleys.py) only inside the fjord band.

Signed coast distance  s  (metres, + inland, - offshore) is the backbone:
    land     = smoothstep(LAND_E0, LAND_E1, s)
    base     = ice-sheet dome P*sqrt(u(2-u)), u = s/DOME_L   (s > 0)
             = shelf / slope / abyssal plain from o = -s       (s < 0)
coast() then shapes the last few km by coast type (ice cliff / rocky headland / beach), builds
floating ice shelves (flat ~40 m tops, sheer fronts, land=0 underneath), floods fjords along
network.py major channels, and clamps: sea (s<0, not shelf) <= -0.4 m, land (s>edge) >= 0.4 m.

continent() caches its per-point fields (small LRU keyed on the X/Y arrays) so coast() and
surface() on the same grid don't recompute them; a miss simply recomputes (pure function).
"""
import hashlib
import math
import os
import numpy as np

from . import noise as N
from . import network
from .config import (CONTINENT_RADIUS, WORLD_RADIUS, PLATEAU_HEIGHT, SEED, CHUNK_SIZE, SPAWN)

S0 = SEED + 9000
TAU = 2.0 * math.pi

# =========================================================================== tuning parameters
# continent outline (warped space)
WARP_AMT = 200e3            # m, low-frequency domain warp of the whole continent
WARP_FREQ = 1.0 / 1.5e6
COAST_LARGE_AMP = 0.19 * CONTINENT_RADIUS    # ~430 km lobes
COAST_LARGE_FREQ = 1.0 / 1.5e6
COAST_MED_AMP = 100e3       # bays / peninsulas, ~300 km wavelength
COAST_MED_FREQ = 1.0 / 300e3
COAST_FINE_AMP = 20e3       # fractal coves & headlands down to ~2.5 km
COAST_FINE_FREQ = 1.0 / 50e3
COAST_CRAG_AMP = 22e3       # ridged term: sharp pointed headlands between rounded bays
COAST_CRAG_FREQ = 1.0 / 70e3
TAB_STEP = 250.0            # m between angular table knots (on the CONTINENT_RADIUS circle)
DETAIL_FADE = (160e3, 650e3)   # medium+fine coast detail fades out this far from the coarse coast
                               # (keeps interior/sea floor free of radial streaks; keeps s monotone)

# big embayments (Ross / Weddell-like), filled with ice shelves; angle deg, radius m
BAYS = ((128.0, 430e3), (218.0, 480e3))
BAY_STRETCH = 1.45          # bays are elongated radially (deep, V-ish embayments)
BAY_K = 40e3                # smooth-min blend
BAY_FRONT = 0.35            # shelf front sits BAY_FRONT*Rb inside the bay's outer edge

# Antarctic-Peninsula-like arm
PEN_ANGLE = 162.0           # deg, direction it leaves the continent (warped space)
PEN_START = 0.72            # starts at PEN_START * R(angle)
PEN_LEN = 1350e3
PEN_TURN = 0.75             # rad of curvature over the length
PEN_W0, PEN_W1 = 140e3, 20e3   # half-width at base / tip
PEN_K = 60e3                # smooth-max blend into the continent

# offshore islands: (cell m, prob, Rmin, Rmax, min offshore gap, max offshore distance)
ISLAND_TIERS = ((300e3, 0.45, 12e3, 45e3, 30e3, 700e3),
                (90e3, 0.30, 2.5e3, 10e3, 6e3, 160e3))

ISLAND_REACH = 50e3          # island shelf / flank reach (m offshore)

# ice-sheet profile
DOME_L = 900e3              # m inland where the dome flattens to PLATEAU_HEIGHT
UND_AMP = 0.08              # broad undulation (fraction of height)
LAND_E0, LAND_E1 = -500.0, 3000.0

# sea floor
SHELF_W, SHELF_W_VAR = 150e3, 50e3
SHELF_D, SHELF_D_VAR = 500.0, 100.0
SHELF_NEAR = 8e3            # e-folding of the generic near-shore drop
SLOPE_W = 130e3
ABYSS_D, ABYSS_VAR = 3750.0, 250.0

# coast types
CLIFF_H, CLIFF_H_VAR = 35.0, 15.0       # ice-cliff tops 20-50 m
ROCK_H, ROCK_H_VAR = 90.0, 40.0         # rocky headland tops
SHELF_TOP, SHELF_TOP_VAR = 40.0, 10.0   # floating ice shelves 30-50 m
SHELF_ICE_W = 25e3                      # max width of ordinary coastal ice shelves

# fjords
FJ_LEN, FJ_LEN_VAR = 45e3, 15e3         # sea reaches 30-60 km up major channels
FJ_DEPTH = 400.0
FJ_WALL = 900.0                         # trough walls rise FJ_WALL m at FJ_HALF from centre
FJ_HALF = 4000.0
FJ_LAT = 500.0                          # lattice for the network sampling
FJ_SEA_FADE = (-6e3, -2e3)
FJ_NODE = 2000.0                        # world-fixed lattice of 'channel reaches the sea' flags
FJ_TRACE_STEP = 2500.0                  # step when tracing a channel toward the sea

# sea ice / icebergs (chunk_objects)
PACK_EDGE, PACK_EDGE_VAR = 30e3, 10e3   # dense pack ice within ~20-40 km of the ice edge
FLOE_BIG_CELL, FLOE_SMALL_CELL = 360.0, 120.0
BERG_TAB_CELL, BERG_IRR_CELL, BERG_BIT_CELL = 8000.0, 3500.0, 700.0

# =========================================================================== small helpers


def _smoothstep(e0, e1, x):
    t = (x - e0) / (e1 - e0)
    np.clip(t, 0.0, 1.0, out=t)
    r = 3.0 - 2.0 * t
    r *= t
    r *= t
    return r


def _smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def _smax(a, b, k):
    return -_smin(-a, -b, k)


def _fbm(X, Y, seed, freq, octaves, gain=0.5):
    return N.fbm(X, Y, seed, freq, octaves, 2.0, gain)


# =========================================================================== world-fixed tables
LAT_D = 25e3
LAT_EXT = 4.3e6
LAT_N = int(round(2 * LAT_EXT / LAT_D)) + 1
F_WX, F_WY, F_UND, F_CT, F_FW, F_SV, F_AB, F_FL, F_CH = range(9)

_T = {}


_HEAVY = ('lat', 'Rc', 'Rm', 'Rf', 'front', 'isl', 'pen_side')


def _cache_path():
    try:
        h = hashlib.md5()
        for f in (N.__file__, __file__):
            with open(f, 'rb') as fh:
                h.update(fh.read())
        h.update(repr((SEED, CONTINENT_RADIUS, WORLD_RADIUS)).encode())
        d = os.path.join(os.path.dirname(__file__), '__pycache__')
        return os.path.join(d, 'ocean_tables_%s.npz' % h.hexdigest()[:16])
    except Exception:
        return None


def _init():
    if _T:
        return
    path = _cache_path()
    if path and os.path.exists(path):
        try:
            with np.load(path) as z:
                loaded = {k: z[k] for k in z.files}
            _T['lat'] = loaded['lat'].astype(np.float64)
            for k in ('Rc', 'Rm', 'Rf', 'front', 'isl'):
                _T[k] = loaded[k]
            _T['pen_side'] = [loaded['pen_side'][0], loaded['pen_side'][1]]
        except Exception:
            _T.clear()
    if 'lat' not in _T:
        _compute_tables()
        if path:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                tmp = path + '.%d.tmp' % os.getpid()
                with open(tmp, 'wb') as fh:
                    np.savez(fh, lat=_T['lat'].astype(np.float32), Rc=_T['Rc'], Rm=_T['Rm'], Rf=_T['Rf'],
                             front=_T['front'], isl=_T['isl'], pen_side=np.stack(_T['pen_side']))
                os.replace(tmp, path)
            except Exception:
                pass
    _T['lat3'] = _T['lat'].reshape(LAT_N, LAT_N, 9)
    _T['R'] = _T['Rc'] + _T['Rm'] + _T['Rf']
    _derived()


def _compute_tables():
    # ---- 2-D lattice (stored/used as float32-rounded so cached and fresh runs are identical)
    t = -LAT_EXT + np.arange(LAT_N) * LAT_D
    X, Y = np.meshgrid(t, t)
    f = [None] * 9
    f[F_WX] = _fbm(X, Y, S0 + 1, WARP_FREQ, 3)
    f[F_WY] = _fbm(X, Y, S0 + 2, WARP_FREQ, 3)
    f[F_UND] = _fbm(X, Y, S0 + 3, 1 / 350e3, 3)
    f[F_CT] = _fbm(X, Y, S0 + 4, 1 / 150e3, 2) * 1.35
    f[F_FW] = _fbm(X, Y, S0 + 5, 1 / 400e3, 2) * 1.35
    f[F_SV] = _fbm(X, Y, S0 + 6, 1 / 600e3, 2) * 1.35
    f[F_AB] = _fbm(X, Y, S0 + 7, 1 / 900e3, 2) * 1.35
    f[F_FL] = _fbm(X, Y, S0 + 8, 1 / 220e3, 2) * 1.35
    f[F_CH] = _fbm(X, Y, S0 + 9, 1 / 120e3, 2) * 1.35
    _T['lat'] = np.ascontiguousarray(np.stack(f, -1).reshape(-1, 9)).astype(np.float32).astype(np.float64)

    # ---- angular coastline table
    n = int(round(TAU * CONTINENT_RADIUS / TAB_STEP))
    a = np.arange(n) * (TAU / n)
    cx, cy = CONTINENT_RADIUS * np.cos(a), CONTINENT_RADIUS * np.sin(a)
    _T['Rc'] = CONTINENT_RADIUS + COAST_LARGE_AMP * _fbm(cx, cy, S0 + 20, COAST_LARGE_FREQ, 3)
    _T['Rm'] = COAST_MED_AMP * _fbm(cx, cy, S0 + 21, COAST_MED_FREQ, 3)
    _T['Rf'] = (COAST_FINE_AMP * _fbm(cx, cy, S0 + 22, COAST_FINE_FREQ, 5, 0.55)
                + COAST_CRAG_AMP * (N.ridged(cx, cy, S0 + 25, COAST_CRAG_FREQ, 4) - 0.45))
    _T['front'] = _fbm(cx, cy, S0 + 23, 1 / 60e3, 4)
    # small periodic table for star-shaped islands / bay rims (4 base cycles round the circle)
    m = 2048
    b = np.arange(m) * (TAU / m)
    _T['isl'] = _fbm(np.cos(b) * 4 / TAU, np.sin(b) * 4 / TAU, S0 + 24, 1.0, 6, 0.55)
    na = int(PEN_LEN / TAB_STEP) + 2
    arc = np.arange(na) * TAB_STEP
    side = []
    for sd in (0, 1):
        yy = np.full(na, 7.3e5 * (sd + 1))
        side.append(22e3 * _fbm(arc, yy, S0 + 30 + sd, 1 / 180e3, 2)
                    + 5e3 * _fbm(arc, yy, S0 + 32 + sd, 1 / 25e3, 4, 0.55))
    _T['pen_side'] = side


def _derived():

    # ---- bays
    bays = []
    for i, (deg, rb) in enumerate(BAYS):
        th = math.radians(deg)
        rr = float(_tab(_T['R'], np.array([th]))[0])
        cen = (rr + 0.15 * rb)
        bays.append((cen * math.cos(th), cen * math.sin(th), rb, cen, 1.7 * i + 0.3))
    _T['bays'] = bays

    # ---- peninsula polyline (warped space)
    th0 = math.radians(PEN_ANGLE)
    r0 = PEN_START * float(_tab(_T['R'], np.array([th0]))[0])
    k = 40
    tt = np.linspace(0.0, 1.0, k)
    head = th0 + PEN_TURN * tt ** 1.4 + 0.06 * np.sin(3.0 * math.pi * tt)
    ds = PEN_LEN / (k - 1)
    px = np.empty(k); py = np.empty(k)
    px[0], py[0] = r0 * math.cos(th0), r0 * math.sin(th0)
    for i in range(1, k):
        px[i] = px[i - 1] + ds * math.cos(head[i - 1])
        py[i] = py[i - 1] + ds * math.sin(head[i - 1])
    hw = PEN_W1 + (PEN_W0 - PEN_W1) * (1.0 - tt) ** 1.2
    _T['pen'] = (px, py, hw, tt * PEN_LEN)
    pad = max(PEN_W0, PEN_W1) + 30e3 + PEN_K
    _T['pen_seg_box'] = (np.minimum(px[:-1], px[1:]) - pad, np.maximum(px[:-1], px[1:]) + pad,
                         np.minimum(py[:-1], py[1:]) - pad, np.maximum(py[:-1], py[1:]) + pad)

    # ---- islands (world space, validated against the mainland outline)
    isl = []
    for ti, (cell, prob, rmin, rmax, gap, omax) in enumerate(ISLAND_TIERS):
        nc = int(LAT_EXT / cell) + 1
        ii, jj = np.meshgrid(np.arange(-nc, nc + 1), np.arange(-nc, nc + 1))
        ii = ii.ravel().astype(np.int64); jj = jj.ravel().astype(np.int64)
        sd = S0 + 100 + ti * 10
        ok = N.hash2(ii, jj, sd) < prob
        ii, jj = ii[ok], jj[ok]
        cxs = (ii + 0.2 + 0.6 * N.hash2(ii, jj, sd + 1)) * cell
        cys = (jj + 0.2 + 0.6 * N.hash2(ii, jj, sd + 2)) * cell
        rad = rmin + (rmax - rmin) * N.hash2(ii, jj, sd + 3) ** 1.5
        ph = N.hash2(ii, jj, sd + 4) * TAU
        sm = _mainland(cxs, cys)[0]
        o = -sm
        ok = (o > rad + gap) & (o < omax) & (np.hypot(cxs, cys) < WORLD_RADIUS - 300e3)
        for a_ in zip(cxs[ok], cys[ok], rad[ok], ph[ok]):
            isl.append(a_)
    _T['isl_arr'] = np.array(isl).reshape(-1, 4)


def _tabw(th, n):
    """Interpolation indices/weights on an n-knot periodic angular table."""
    u = th * (n / TAU)
    i = np.floor(u)
    f = u - i
    i = i.astype(np.int64) % n
    i1 = i + 1
    i1[i1 == n] = 0
    return i, i1, f


def _tapply(tab, w):
    i, i1, f = w
    a = tab[i]
    return a + (tab[i1] - a) * f


def _tab(tab, th):
    return _tapply(tab, _tabw(np.asarray(th, np.float64), tab.shape[0]))


def _tab_lin(tab, x):
    u = np.clip(x / TAB_STEP, 0.0, tab.shape[0] - 1.000001)
    i = u.astype(np.int64)
    f = u - i
    return tab[i] * (1.0 - f) + tab[i + 1] * f


def _lat_axes(xs, ys):
    """Separable (bit-identical) version of _lat for a regular grid given by its axes."""
    L3 = _T['lat3']
    u = np.clip((xs + LAT_EXT) / LAT_D, 0.0, LAT_N - 1.000001)
    v = np.clip((ys + LAT_EXT) / LAT_D, 0.0, LAT_N - 1.000001)
    i = u.astype(np.int64); j = v.astype(np.int64)
    fu = (u - i)[:, None]; fv = (v - j)[:, None, None]
    rows = np.unique(np.concatenate([j, j + 1]))
    Lr = L3[rows]
    Rx = Lr[:, i] * (1 - fu) + Lr[:, i + 1] * fu
    p0 = np.searchsorted(rows, j); p1 = np.searchsorted(rows, j + 1)
    return (Rx[p0] * (1 - fv) + Rx[p1] * fv).reshape(-1, 9)


def _lat(x, y):
    """Bilinear lookup of all lattice fields -> (n, 9)."""
    L = _T['lat']
    u = np.clip((x + LAT_EXT) / LAT_D, 0.0, LAT_N - 1.000001)
    v = np.clip((y + LAT_EXT) / LAT_D, 0.0, LAT_N - 1.000001)
    i = u.astype(np.int64); j = v.astype(np.int64)
    fu = (u - i)[:, None]; fv = (v - j)[:, None]
    b = j * LAT_N + i
    return ((L[b] * (1 - fu) + L[b + 1] * fu) * (1 - fv)
            + (L[b + LAT_N] * (1 - fu) + L[b + LAT_N + 1] * fu) * fv)


# =========================================================================== fjord connectivity
_FJ_FLAGS = {}          # memo of a pure function: (i, j) node -> 0/1


def _net_eval(x, y):
    h = 25.0
    n = network.major_distance(x, y)[1]
    gx = (network.major_distance(x + h, y)[1] - n) / h
    gy = (network.major_distance(x, y + h)[1] - n) / h
    return n, gx, gy


FJ_P_FAIL = 400e3       # path length stored for nodes whose channel never reaches the sea


def _trace_flags(ii, jj):
    """For FJ_NODE lattice nodes: follow the nearest major channel (both directions) until it
    reaches the sea. Returns (P, A): path length to the sea along the channel, and the minimum
    'fjords allowed' factor met on the way (0 where no connection). Both are monotone along a
    channel, so fjord depth/width derived from them can't pinch off into lakes.
    Pure function of the node -> identical for every chunk / LOD / point query."""
    x = ii * FJ_NODE; y = jj * FJ_NODE
    n0 = len(x)
    P = np.full(n0, FJ_P_FAIL); A = np.zeros(n0)
    F = _fields(x, y)
    lim = 2.5 * (FJ_LEN + FJ_LEN_VAR * F['lat'][:, F_FL]) + 30e3
    s_start = F['s'].copy()
    px, py = x.copy(), y.copy()
    for _ in range(3):          # project onto the channel (Newton)
        n, gx, gy = _net_eval(px, py)
        g2 = gx * gx + gy * gy + 1e-18
        stp = np.clip(n / g2, -4e3 / np.sqrt(g2), 4e3 / np.sqrt(g2))
        px -= stp * gx; py -= stp * gy
    n, gx, gy = _net_eval(px, py)
    g = np.sqrt(gx * gx + gy * gy) + 1e-12
    alive = (np.abs(n) / g < 400.0) & (np.hypot(px - x, py - y) < 7e3)
    Fp = _fields(px, py)
    s = Fp['s']
    ok0 = _fjord_ok(Fp, Fp['lat'], _types(Fp['lat'])[2])
    at_sea = alive & (s < 0)
    P[at_sea] = 0.0; A[at_sea] = ok0[at_sea]
    alive &= s >= 0
    tx, ty = -gy / g, gx / g
    a = np.nonzero(alive)[0]
    idx = np.concatenate([a, a])
    px, py = np.concatenate([px[a], px[a]]), np.concatenate([py[a], py[a]])
    tx, ty = np.concatenate([tx[a], -tx[a]]), np.concatenate([ty[a], -ty[a]])
    sp = np.concatenate([s[a], s[a]]); amin = np.concatenate([ok0[a], ok0[a]])
    path = np.zeros(len(idx)); s0 = s_start[idx]; lim = lim[idx]
    while len(idx):
        px = px + tx * FJ_TRACE_STEP; py = py + ty * FJ_TRACE_STEP
        path = path + FJ_TRACE_STEP
        n, gx, gy = _net_eval(px, py)
        g2 = gx * gx + gy * gy + 1e-18
        stp = np.clip(n / g2, -1.5e3 / np.sqrt(g2), 1.5e3 / np.sqrt(g2))
        px -= stp * gx; py -= stp * gy
        g = np.sqrt(g2)
        nt_x, nt_y = -gy / g, gx / g
        sg = np.where(nt_x * tx + nt_y * ty >= 0, 1.0, -1.0)
        tx, ty = nt_x * sg, nt_y * sg
        Fp = _fields(px, py)
        s = Fp['s']
        amin = np.minimum(amin, _fjord_ok(Fp, Fp['lat'], _types(Fp['lat'])[2]))
        off = np.abs(n) / g > 1500.0
        done = (s < 0) & ~off
        if done.any():
            frac = sp[done] / np.maximum(sp[done] - s[done], 1e-6)
            pl = path[done] - FJ_TRACE_STEP * (1.0 - np.clip(frac, 0.0, 1.0))
            k = idx[done]
            better = pl < P[k]
            # two directions may both succeed: keep the shorter connection
            for kk, pv, av in zip(k[better].tolist(), pl[better].tolist(), amin[done][better].tolist()):
                if pv < P[kk]:
                    P[kk] = pv; A[kk] = av
        fail = off | (s > s0 + 6000.0) | (path > lim)
        keep = ~((s < 0) | fail)
        idx, px, py, tx, ty, path, s0, lim, sp, amin = (
            idx[keep], px[keep], py[keep], tx[keep], ty[keep], path[keep], s0[keep], lim[keep],
            s[keep], amin[keep])
    return P, A


def _fjord_conn(x, y):
    """Bilinear (P, A) from the memoised node traces."""
    u = x / FJ_NODE; v = y / FJ_NODE
    i = np.floor(u).astype(np.int64); j = np.floor(v).astype(np.int64)
    fu = u - i; fv = v - j
    keys = np.unique(np.concatenate([(i + a) * 10_000_019 + (j + b)
                                     for a in (0, 1) for b in (0, 1)]))
    todo = [k for k in keys.tolist() if k not in _FJ_FLAGS]
    if todo:
        kk = np.array(todo, np.int64)
        ki = np.floor_divide(kk + 5_000_000, 10_000_019)
        kj = kk - ki * 10_000_019
        Pn, An = _trace_flags(ki.astype(np.float64), kj.astype(np.float64))
        for k, p_, a_ in zip(todo, Pn.tolist(), An.tolist()):
            _FJ_FLAGS[k] = (p_, a_)
        if len(_FJ_FLAGS) > 400_000:
            _FJ_FLAGS.clear()
    vals = np.array([_FJ_FLAGS.get(k, (FJ_P_FAIL, 0.0)) for k in keys.tolist()]).reshape(-1, 2)

    def val(a, b):
        return vals[np.searchsorted(keys, (i + a) * 10_000_019 + (j + b))]
    fu = fu[:, None]; fv = fv[:, None]
    r = ((val(0, 0) * (1 - fu) + val(1, 0) * fu) * (1 - fv)
         + (val(0, 1) * (1 - fu) + val(1, 1) * fu) * fv)
    return r[:, 0], r[:, 1]


# =========================================================================== coast distance


def _mainland(x, y, lat=None):
    """Mainland (continent - bays + peninsula) signed distance for flat arrays.
    Returns (s, th_w, r_w, f_bay, bay_d, lat)."""
    if lat is None:
        lat = _lat(x, y)
    wx = x + WARP_AMT * lat[:, F_WX]
    wy = y + WARP_AMT * lat[:, F_WY]
    rw = np.hypot(wx, wy)
    th = np.arctan2(wy, wx)
    tw = _tabw(th, _T['R'].shape[0])
    d0 = _tapply(_T['Rc'], tw) - rw
    fade = 1.0 - _smoothstep(DETAIL_FADE[0], DETAIL_FADE[1], np.abs(d0))
    rf = _tapply(_T['Rf'], tw) * fade
    s = d0 + _tapply(_T['Rm'], tw) * fade + rf
    # distance used for the ice-sheet PROFILE: fine coastal detail fades out ~30 km inland so it
    # doesn't streak the plateau radially (the outline itself still uses s)
    sp_ = s - rf * _smoothstep(3e3, 30e3, s)
    qx0, qx1, qy0, qy1 = wx.min(), wx.max(), wy.min(), wy.max()

    # bays (sea) + their shelf-ice field
    f_bay = np.full(x.shape, -1e9)
    bay_d = np.full(x.shape, 1e9)
    for bx, by, rb, cen, ph in _T['bays']:
        ddx = max(qx0 - bx, 0.0, bx - qx1); ddy = max(qy0 - by, 0.0, by - qy1)
        if math.hypot(ddx, ddy) > rb * BAY_STRETCH * 1.4 + 200e3:
            continue
        dx, dy = wx - bx, wy - by
        ux, uy = bx / cen, by / cen                  # radial axis of the bay
        rad_c = (dx * ux + dy * uy) / BAY_STRETCH    # compress radially -> elongated inland
        tan_c = (-dx * uy + dy * ux) * (0.4 + 0.6 * _smoothstep(-rb, rb * 0.5, dx * ux + dy * uy))
        d = np.hypot(rad_c, tan_c)
        rim = rb * (1.0 + 0.22 * _tab(_T['isl'], np.arctan2(tan_c, rad_c) + ph))
        bsd = d - rim
        s = _smin(s, bsd, BAY_K)
        sp_ = _smin(sp_, bsd, BAY_K)
        front = cen - BAY_FRONT * rb + 12e3 * _tapply(_T['front'], tw) - rw
        f_bay = np.maximum(f_bay, np.minimum(front, -bsd))
        bay_d = np.minimum(bay_d, bsd)

    # peninsula
    px, py, hw, arc = _T['pen']
    x0b, x1b, y0b, y1b = _T['pen_seg_box']
    segs = np.nonzero((x1b >= qx0) & (x0b <= qx1) & (y1b >= qy0) & (y0b <= qy1))[0]
    if len(segs):
        best = np.full(x.shape, -1e12)
        barc = np.zeros(x.shape); bside = np.zeros(x.shape); bd = np.zeros(x.shape)
        bhw = np.ones(x.shape)
        for i in segs:
            ax, ay = px[i], py[i]
            ex, ey = px[i + 1] - ax, py[i + 1] - ay
            L2 = ex * ex + ey * ey
            rx, ry = wx - ax, wy - ay
            t = np.clip((rx * ex + ry * ey) / L2, 0.0, 1.0)
            dx, dy = rx - t * ex, ry - t * ey
            d = np.sqrt(dx * dx + dy * dy)
            h_ = hw[i] + (hw[i + 1] - hw[i]) * t
            sv = h_ - d
            m = sv > best
            best = np.where(m, sv, best)
            barc = np.where(m, arc[i] + t * (arc[i + 1] - arc[i]), barc)
            bside = np.where(m, ex * ry - ey * rx, bside)
            bd = np.where(m, d, bd)
            bhw = np.where(m, h_, bhw)
        det = np.where(bside >= 0, _tab_lin(_T['pen_side'][0], barc), _tab_lin(_T['pen_side'][1], barc))
        det *= _smoothstep(0.3, 0.7, bd / bhw)
        sp = best + det
        s = _smax(s, sp, PEN_K)
        sp_ = _smax(sp_, sp, PEN_K)
    return s, th, rw, f_bay, bay_d, lat, sp_


def _islands(x, y, s):
    """Returns (combined s, island-only s; -1e9 where no island is near)."""
    arr = _T['isl_arr']
    si_all = np.full(x.shape, -1e9)
    if not len(arr):
        return s, si_all
    pad = arr[:, 2] * 1.35 + ISLAND_REACH
    qx0, qx1, qy0, qy1 = x.min(), x.max(), y.min(), y.max()
    sel = np.nonzero((arr[:, 0] + pad >= qx0) & (arr[:, 0] - pad <= qx1)
                     & (arr[:, 1] + pad >= qy0) & (arr[:, 1] - pad <= qy1))[0]
    if not len(sel):
        return s, si_all
    for k in sel:
        cx, cy, rad, ph = arr[k]
        p = pad[k]
        m = np.nonzero((np.abs(x - cx) < p) & (np.abs(y - cy) < p))[0]
        if not len(m):
            continue
        dx, dy = x[m] - cx, y[m] - cy
        d = np.hypot(dx, dy)
        si = rad * (1.0 + 0.3 * _tab(_T['isl'], np.arctan2(dy, dx) + ph)) - d
        si_all[m] = np.maximum(si_all[m], si)
    return np.maximum(s, si_all), si_all


def _fields(x, y, axes=None):
    """All per-point fields for flat arrays x, y (axes=(xs, ys) if they form a meshgrid)."""
    lat = _lat_axes(*axes) if axes is not None else _lat(x, y)
    s, th, rw, f_bay, bay_d, lat, sp_ = _mainland(x, y, lat)
    s_main = s
    s, s_isl = _islands(x, y, s)
    s_prof = np.maximum(np.maximum(sp_, s_isl), 0.15 * s)
    return {'s': s, 's_main': s_main, 's_isl': s_isl, 's_prof': s_prof, 'th': th, 'rw': rw, 'f_bay': f_bay, 'bay_d': bay_d, 'lat': lat}


# ---- tiny LRU keyed on the query arrays (continent -> coast -> surface on the same grid)
_CACHE = []
_CACHE_N = 6


def _key(X, Y):
    X = np.asarray(X); Y = np.asarray(Y)
    n = X.size
    if n == 0:
        return None
    xf = X.reshape(-1); yf = Y.reshape(-1)
    return (X.shape, float(xf[0]), float(xf[-1]), float(yf[0]), float(yf[-1]),
            float(xf[n // 2]), float(yf[n // 3]), float(xf[::97].sum()), float(yf[::89].sum()))


def _get_fields(X, Y):
    _init()
    k = _key(X, Y)
    for kk, v in _CACHE:
        if kk == k:
            return v
    X = np.asarray(X, np.float64); Y = np.asarray(Y, np.float64)
    x = X.reshape(-1)
    y = Y.reshape(-1)
    axes = None
    if (X.ndim == 2 and X.shape[0] > 2 and X.shape[1] > 2 and np.array_equal(X[0], X[-1])
            and np.array_equal(X[0], X[X.shape[0] // 2]) and np.array_equal(Y[:, 0], Y[:, -1])
            and np.array_equal(Y[:, 0], Y[:, Y.shape[1] // 2])):
        axes = (X[0], Y[:, 0])
    v = _fields(x, y, axes)
    _CACHE.insert(0, (k, v))
    del _CACHE[_CACHE_N:]
    return v


# =========================================================================== public: heights


def _ice_profile(s, lat):
    u = np.clip(s / DOME_L, 0.0, 1.0)
    return PLATEAU_HEIGHT * (1.0 + UND_AMP * lat[:, F_UND]) * np.sqrt(u * (2.0 - u))


def _shelf_depth(lat):
    return SHELF_D - SHELF_D_VAR * lat[:, F_SV]


def _sea_floor(o, lat):
    sd = _shelf_depth(lat)
    sw = SHELF_W + SHELF_W_VAR * lat[:, F_SV]
    ab = ABYSS_D + ABYSS_VAR * lat[:, F_AB]
    depth = sd * (1.0 - np.exp(-o / SHELF_NEAR)) + (ab - sd) * _smoothstep(sw, sw + SLOPE_W, o)
    depth += 40.0 * lat[:, F_CH] * _smoothstep(0.0, 30e3, o)
    return -(0.5 + depth)


def continent(X, Y):
    """(base_h, land). base: ice-sheet dome over land, shelf/slope/abyss over sea."""
    X = np.asarray(X, np.float64); Y = np.asarray(Y, np.float64)
    F = _get_fields(X, Y)
    s, lat = F['s'], F['lat']
    land_h = _ice_profile(F['s_prof'], lat)
    sea_h = _sea_floor(np.maximum(-F['s_main'], 0.0), lat)
    si = F['s_isl']
    if si.max() > -1e8:
        # islands: own shelf + steep flanks down past the abyss (max -> shallower floor wins)
        oi = np.maximum(-si, 0.0)
        isl_floor = -(0.5 + 350.0 * (1.0 - np.exp(-oi / 3000.0)) + 4500.0 * _smoothstep(6e3, ISLAND_REACH - 2e3, oi))
        sea_h = np.maximum(sea_h, isl_floor)
    base = np.where(s > 0.0, land_h, sea_h)
    land = _smoothstep(LAND_E0, LAND_E1, s)
    return base.reshape(X.shape), land.reshape(X.shape)


def _types(lat):
    """Coast-type weights (ice cliff, rock headland, beach) and ordinary shelf width."""
    ct, fw = lat[:, F_CT], lat[:, F_FW]
    shelf_frac = _smoothstep(0.2, 0.7, fw)
    wi = np.maximum(_smoothstep(-0.05, 0.12, ct), _smoothstep(0.05, 0.25, fw))
    wb = (1.0 - _smoothstep(-0.45, -0.28, ct)) * (1.0 - wi)
    wr = np.clip(1.0 - wi - wb, 0.0, 1.0)
    return wi, wr, wb, SHELF_ICE_W * shelf_frac


def _shelf_field(s, F, W):
    return np.maximum(W + s, F['f_bay'])


def _fjord_ok(F, lat, wb):
    return ((1.0 - _smoothstep(0.0, 0.15, lat[:, F_FW]))
            * _smoothstep(30e3, 70e3, F['bay_d']) * (1.0 - 0.9 * wb))


def _network_n(x, y):
    """Major-network noise n and its gradient, bilinear from a world-fixed FJ_LAT lattice
    (central differences), so any query (chunk grid or single point) gets identical values."""
    d = FJ_LAT
    i0 = int(np.floor(x.min() / d)) - 1; i1 = int(np.floor(x.max() / d)) + 2
    j0 = int(np.floor(y.min() / d)) - 1; j1 = int(np.floor(y.max() / d)) + 2
    nb = (i1 - i0 + 1) * (j1 - j0 + 1)
    if nb <= max(4 * x.size + 400, 20000) and nb < 4_000_000:
        gx_ = np.arange(i0, i1 + 1) * d; gy_ = np.arange(j0, j1 + 1) * d
        GX, GY = np.meshgrid(gx_, gy_)
        n = network.major_distance(GX, GY)[1]
        nx = np.zeros_like(n); ny = np.zeros_like(n)
        nx[:, 1:-1] = (n[:, 2:] - n[:, :-2]) / (2 * d)
        ny[1:-1, :] = (n[2:, :] - n[:-2, :]) / (2 * d)
        u = (x / d) - i0; v = (y / d) - j0
        i = np.floor(u).astype(np.int64); j = np.floor(v).astype(np.int64)
        fu = (u - i)[:, None]; fv = (v - j)[:, None]
        Wd = n.shape[1]
        A = np.stack([n, nx, ny], -1).reshape(-1, 3)
        b = j * Wd + i
        r = ((A[b] * (1 - fu) + A[b + 1] * fu) * (1 - fv)
             + (A[b + Wd] * (1 - fu) + A[b + Wd + 1] * fu) * fv)
        return r[:, 0], r[:, 1], r[:, 2]
    # sparse queries (continent-scale validation): direct evaluation + finite differences
    h = 50.0
    n = network.major_distance(x, y)[1]
    nx = (network.major_distance(x + h, y)[1] - n) / h
    ny = (network.major_distance(x, y + h)[1] - n) / h
    return n, nx, ny


def _sea_typed(hb, sb, lb, wi, wr, wb):
    """Replace the generic near-shore drop with the coast-type one (steep under cliffs)."""
    o = np.maximum(-sb, 0.0)
    sd = _shelf_depth(lb)
    lt = wi * 300.0 + wr * 1200.0 + wb * 20000.0
    return np.minimum(hb + sd * (np.exp(-o / lt) - np.exp(-o / SHELF_NEAR)), -0.4)


def _coast_flat(x, y, h, F):
    """Core of coast() on flat arrays."""
    s, lat, fbay = F['s'], F['lat'], F['f_bay']
    out = h.copy()
    bay = fbay > -500.0
    # A: open sea beyond the coastal band -> just keep it under water
    A = (s < -60e3) & ~bay
    if A.any():
        out[A] = np.minimum(out[A], -0.4)
    # B: near-shore sea (typed shelf profile), unless an ice shelf reaches it
    B = np.nonzero((s >= -60e3) & (s < -6e3) & ~bay)[0]
    Cm = (s >= -6e3) & (s < 9e3) | bay & (s < 9e3)
    if len(B):
        lb = lat[B]
        wi, wr, wb, W = _types(lb)
        shelfy = (W + s[B]) > -200.0
        Cm[B[shelfy]] = True
        k = ~shelfy
        Bk = B[k]
        out[Bk] = _sea_typed(h[Bk], s[Bk], lb[k], wi[k], wr[k], wb[k])
    # D: inland part of the band -> keep above sea (fjords below may cut it)
    D = np.nonzero((s >= 9e3) & (s < 80e3))[0]
    if len(D):
        out[D] = np.maximum(out[D], 0.4)
    C = np.nonzero(Cm)[0]
    if len(C):
        sb = s[C]; lb = lat[C]; hb = h[C]
        wi, wr, wb, W = _types(lb)
        ch = lb[:, F_CH]
        e = wi * 40.0 + wr * 150.0 + wb * 700.0
        h_sea = _sea_typed(hb, sb, lb, wi, wr, wb)
        sl = np.maximum(sb, 0.0)
        h_land = np.maximum(hb, (CLIFF_H + CLIFF_H_VAR * ch) * wi * (1.0 - _smoothstep(1500.0, 4000.0, sl)))
        rock = ((ROCK_H + ROCK_H_VAR * ch) * (1.0 - np.exp(-sl / 350.0)) * wr
                * (1.0 - _smoothstep(2000.0, 5000.0, sl)))
        h_land = np.maximum(h_land, rock)
        fade = wb * (1.0 - _smoothstep(2500.0, 9000.0, sl))
        h_land = h_land + (np.minimum(h_land, 0.4 + 0.012 * sl) - h_land) * fade
        h_land = np.maximum(h_land, 0.4)
        t = _smoothstep(0.0, e, sb)
        hc = h_sea + (h_land - h_sea) * t
        # floating ice shelves (ordinary coastal + bay-filling), sheer ~40 m fronts
        fsh = np.maximum(W + sb, fbay[C])
        sm = _smoothstep(0.0, 60.0, fsh) * (sb < 5000.0)
        top = SHELF_TOP + SHELF_TOP_VAR * lb[:, F_FL] + 1.5 * lb[:, F_CH]
        hc = hc + (np.maximum(hc, top) - hc) * sm
        out[C] = hc
    # fjords: flood major-network channels near the coast
    Fm = np.nonzero((s > FJ_SEA_FADE[0]) & (s < FJ_LEN + FJ_LEN_VAR * 1.4 + 15e3) & ~bay)[0]
    if len(Fm):
        lb = lat[Fm]
        wb = _types(lb)[2]
        fok = _fjord_ok({'bay_d': F['bay_d'][Fm]}, lb, wb)
        flen = FJ_LEN + FJ_LEN_VAR * lb[:, F_FL]
        sb = s[Fm]
        k = (fok > 0.01) & (sb < flen + 15e3)
        cand, fok, flen, sb = Fm[k], fok[k], flen[k], sb[k]
        if len(cand):
            n, gx, gy = _network_n(x[cand], y[cand])
            g = np.sqrt(gx * gx + gy * gy) + 1e-12
            dm = np.abs(n) / g
            near = dm < FJ_HALF * 1.6
            if near.any():
                c2 = cand[near]
                dm = dm[near]
                s2, fl = sb[near], flen[near]
                # path length to the sea along the channel (P) and allowed factor (A): both are
                # monotone along the channel, so the fjord only narrows/shoals going inland
                Pp, Aa = _fjord_conn(x[c2], y[c2])
                w = (Aa * (1.0 - _smoothstep(fl, fl + 15e3, Pp))
                     * _smoothstep(FJ_SEA_FADE[0], FJ_SEA_FADE[1], s2))
                # weak weight -> narrower & shallower fjord (never a dry half-depth groove)
                D_ = FJ_DEPTH * np.clip(1.0 - Pp / fl, 0.0, 1.0) ** 0.6
                dfac = _smoothstep(0.2, 0.5, w)
                centre = np.where(Pp < fl, -D_, (Pp - fl) * 0.03) * dfac + (1.0 - dfac) * 40.0
                wid = FJ_HALF * np.maximum(_smoothstep(0.15, 0.7, w), 1e-3)
                floor = centre + FJ_WALL * (dm / wid) ** 2
                cur = out[c2]
                out[c2] = np.where(wid > 30.0, np.minimum(cur, floor), cur)
    return out


def coast(X, Y, h, land):
    X = np.asarray(X, np.float64); Y = np.asarray(Y, np.float64)
    F = _get_fields(X, Y)
    out = _coast_flat(X.reshape(-1), Y.reshape(-1), np.asarray(h, np.float64).reshape(-1), F)
    return out.reshape(X.shape)


def surface(X, Y, H, land, masks):
    """'water' below sea level, 'ice' on ice shelves / ice-cliff faces, 'rock' on headlands."""
    X = np.asarray(X, np.float64); Y = np.asarray(Y, np.float64)
    F = _get_fields(X, Y)
    s = F['s']
    Hf = np.asarray(H, np.float64).reshape(-1)
    shape = X.shape
    water = _smoothstep(0.3, -0.3, Hf)
    ice = np.zeros_like(Hf); rock = np.zeros_like(Hf)
    band = np.nonzero((s > -60e3) & (s < 6e3) | (F['f_bay'] > -500.0))[0]
    if len(band):
        lb = F['lat'][band]
        sb = s[band]
        wi, wr, wb, W = _types(lb)
        Fb = {'f_bay': F['f_bay'][band]}
        fsh = _shelf_field(sb, Fb, W)
        above = Hf[band] > 0.5
        shelf = _smoothstep(-50.0, 50.0, fsh) * (sb < 400.0) * above
        cliff = wi * (1.0 - _smoothstep(150.0, 500.0, sb)) * above
        ice[band] = np.maximum(shelf, cliff)
        rock[band] = wr * (1.0 - _smoothstep(1500.0, 3500.0, sb)) * above * (1.0 - ice[band])
    ice = np.maximum(ice, 0.0) * (1.0 - water)
    keep = 1.0 - np.maximum(water, ice)
    for k in ('snow', 'rock', 'ice', 'water'):
        if k not in masks:
            masks[k] = np.zeros(shape)
    snow = np.asarray(masks['snow'], np.float64).reshape(-1) * keep
    rk = np.maximum(np.asarray(masks['rock'], np.float64).reshape(-1) * keep, rock * keep)
    snow = np.minimum(snow, 1.0 - rk - np.maximum(water, ice))
    masks['snow'] = np.clip(snow, 0.0, 1.0).reshape(shape)
    masks['rock'] = rk.reshape(shape)
    masks['ice'] = np.maximum(np.asarray(masks['ice'], np.float64).reshape(-1) * keep, ice).reshape(shape)
    masks['water'] = np.maximum(np.asarray(masks['water'], np.float64).reshape(-1), water).reshape(shape)


# =========================================================================== queries / helpers


def coast_distance(X, Y):
    """Signed distance to the grounded coastline (m, + inland). Pure, cheap."""
    X = np.asarray(X, np.float64)
    return _get_fields(X, Y)['s'].reshape(X.shape)


def ice_edge_distance(x, y):
    """Offshore distance to the nearest grounded coast OR floating ice-shelf front (flat arrays).
    Negative = on land / shelf."""
    _init()
    F = _fields(x, y)
    W = _types(F['lat'])[3]
    return -np.maximum(F['s'], _shelf_field(F['s'], F, W)), F


def _ocean_only_height(X, Y):
    base, land = continent(X, Y)
    return coast(X, Y, base, land)


def find_coastal_spawn(near=SPAWN, inland=(15e3, 30e3), box=260e3, step=500.0):
    """Deterministic land point 15-30 km from a dramatic (ice-cliff / rock) coast that overlooks
    a sea-connected fjord 2.5-7 km away. Searches a box around where the ray from the origin
    through `near` meets the coast; returns (x, y) world metres (closest-to-ray candidate)."""
    _init()
    ang = math.atan2(near[1], near[0])
    rr = np.arange(1.0e6, 3.6e6, 1000.0)
    sx, sy = rr * math.cos(ang), rr * math.sin(ang)
    ss = coast_distance(sx, sy)
    idx = np.nonzero((ss[:-1] > 0) & (ss[1:] <= 0))[0]
    rc = rr[idx[0]] if len(idx) else CONTINENT_RADIUS
    cx0, cy0 = rc * math.cos(ang), rc * math.sin(ang)
    n = int(box / step) + 1
    t = np.arange(n) * step - box / 2
    X, Y = np.meshgrid(cx0 + t, cy0 + t)
    H = _ocean_only_height(X, Y)
    F = _get_fields(X, Y)
    s = F['s'].reshape(X.shape)
    wi, wr, wb, W = _types(F['lat'])
    wb = wb.reshape(X.shape)
    water = H < 0.0
    # flood-fill from open sea to find sea-connected water
    conn = water & (s < -5e3)
    for _ in range(4 * n):
        grown = conn.copy()
        grown[1:, :] |= conn[:-1, :]; grown[:-1, :] |= conn[1:, :]
        grown[:, 1:] |= conn[:, :-1]; grown[:, :-1] |= conn[:, 1:]
        grown &= water
        if (grown == conn).all():
            break
        conn = grown
    fj = conn & (s > 2e3)                      # sea-connected fjord water well inland

    def dil(m, k):
        m = m.copy()
        for _ in range(k):
            g = m.copy()
            g[1:, :] |= m[:-1, :]; g[:-1, :] |= m[1:, :]
            g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]
            m = g
        return m
    near_fj = dil(fj, int(7e3 / step)) & ~dil(fj, int(2.5e3 / step))
    dramatic = dil((np.abs(s) < 1e3) & (wb < 0.2), int(35e3 / step))
    cand = (~water) & (s > inland[0]) & (s < inland[1]) & near_fj & dramatic & (H > 20.0)
    if not cand.any():
        cand = (~water) & (s > inland[0]) & (s < inland[1]) & near_fj
    if not cand.any():
        return None
    # closest to the ray point `inland` midpoint in from the coast
    tx = cx0 - math.cos(ang) * 0.5 * sum(inland); ty = cy0 - math.sin(ang) * 0.5 * sum(inland)
    d = np.where(cand, (X - tx) ** 2 + (Y - ty) ** 2, np.inf)
    k = int(np.argmin(d))
    return float(X.flat[k]), float(Y.flat[k])


# =========================================================================== chunk objects
WATER_MAT, SEAICE_MAT, BERG_MAT = "Ocean_Water", "Ocean_SeaIce", "Ocean_Iceberg"
PLANE_MESH = "Ocean_Plane_Mesh"
PROTO_TAB = ["Ocean_Berg_Tab_%d" % i for i in range(3)]
PROTO_IRR = ["Ocean_Berg_Irr_%d" % i for i in range(3)]


def _build_water(mat):
    import bpy  # noqa
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (600, 0)
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); bs.location = (250, 0)
    bs.inputs['Base Color'].default_value = (0.004, 0.012, 0.022, 1.0)
    bs.inputs['Roughness'].default_value = 0.06
    bs.inputs['IOR'].default_value = 1.333
    geo = nt.nodes.new('ShaderNodeNewGeometry'); geo.location = (-700, 0)
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.location = (-450, 100)
    nz.inputs['Scale'].default_value = 0.035
    nz.inputs['Detail'].default_value = 6.0
    nz.inputs['Roughness'].default_value = 0.6
    nz2 = nt.nodes.new('ShaderNodeTexNoise'); nz2.location = (-450, -150)
    nz2.inputs['Scale'].default_value = 0.4
    nz2.inputs['Detail'].default_value = 3.0
    add = nt.nodes.new('ShaderNodeMath'); add.location = (-250, 0); add.operation = 'ADD'
    nt.links.new(geo.outputs['Position'], nz.inputs['Vector'])
    nt.links.new(geo.outputs['Position'], nz2.inputs['Vector'])
    nt.links.new(nz.outputs['Fac'], add.inputs[0])
    mul = nt.nodes.new('ShaderNodeMath'); mul.location = (-250, -150); mul.operation = 'MULTIPLY'
    nt.links.new(nz2.outputs['Fac'], mul.inputs[0]); mul.inputs[1].default_value = 0.35
    nt.links.new(mul.outputs[0], add.inputs[1])
    bump = nt.nodes.new('ShaderNodeBump'); bump.location = (0, -200)
    bump.inputs['Strength'].default_value = 0.12
    bump.inputs['Distance'].default_value = 0.6
    nt.links.new(add.outputs[0], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
    nt.links.new(bs.outputs['BSDF'], out.inputs['Surface'])
    _fog(mat, bs.outputs['BSDF'])


def _build_ice(mat, base, rough, sss, blue_below=None):
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (700, 0)
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); bs.location = (350, 0)
    bs.inputs['Roughness'].default_value = rough
    bs.inputs['Subsurface Weight'].default_value = sss
    bs.inputs['Subsurface Radius'].default_value = (0.3, 0.6, 1.0)
    bs.inputs['Subsurface Scale'].default_value = 0.5
    geo = nt.nodes.new('ShaderNodeNewGeometry'); geo.location = (-800, 0)
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.location = (-550, 150)
    nz.inputs['Scale'].default_value = 0.08
    nz.inputs['Detail'].default_value = 4.0
    nt.links.new(geo.outputs['Position'], nz.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.location = (-300, 150)
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (base[0] * 0.86, base[1] * 0.93, base[2], 1.0)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = (*base, 1.0)
    nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac'])
    col = ramp.outputs['Color']
    if blue_below is not None:
        sep = nt.nodes.new('ShaderNodeSeparateXYZ'); sep.location = (-550, -150)
        nt.links.new(geo.outputs['Position'], sep.inputs['Vector'])
        mr = nt.nodes.new('ShaderNodeMapRange'); mr.location = (-300, -150)
        mr.inputs['From Min'].default_value = blue_below
        mr.inputs['From Max'].default_value = -1.0
        nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
        mix = nt.nodes.new('ShaderNodeMix'); mix.location = (0, 0)
        mix.data_type = 'RGBA'
        nt.links.new(mr.outputs['Result'], mix.inputs[0])
        nt.links.new(col, mix.inputs[6])
        mix.inputs[7].default_value = (0.25, 0.55, 0.75, 1.0)
        col = mix.outputs[2]
    nt.links.new(col, bs.inputs['Base Color'])
    nt.links.new(bs.outputs['BSDF'], out.inputs['Surface'])
    _fog(mat, bs.outputs['BSDF'])


def _fog(mat, sock):
    try:
        from . import materials as M
        M.add_distance_fog(mat, sock)
    except Exception:
        pass


def _material(name, builder):
    import bpy
    try:
        from . import materials as M
        return M.get_or_create(name, builder)
    except ImportError:
        m = bpy.data.materials.get(name)
        if m is None:
            m = bpy.data.materials.new(name); builder(m); m.use_fake_user = True
        return m


def _mats():
    w = _material(WATER_MAT, _build_water)
    si = _material(SEAICE_MAT, lambda m: _build_ice(m, (0.80, 0.87, 0.93), 0.6, 0.05))
    bg = _material(BERG_MAT, lambda m: _build_ice(m, (0.86, 0.93, 0.98), 0.35, 0.25, blue_below=6.0))
    return w, si, bg


def _mesh_from_arrays(name, verts, faces_flat, face_sizes, mat=None, smooth=False):
    import bpy
    me = bpy.data.meshes.new(name)
    nv = len(verts)
    me.vertices.add(nv)
    me.vertices.foreach_set('co', np.asarray(verts, np.float32).ravel())
    me.loops.add(len(faces_flat))
    me.loops.foreach_set('vertex_index', np.asarray(faces_flat, np.int32))
    me.polygons.add(len(face_sizes))
    starts = np.concatenate([[0], np.cumsum(face_sizes)[:-1]]).astype(np.int32)
    me.polygons.foreach_set('loop_start', starts)
    if smooth:
        me.polygons.foreach_set('use_smooth', np.ones(len(face_sizes), bool))
    me.update(calc_edges=True)
    if mat is not None:
        me.materials.append(mat)
    return me


def _plane_mesh(mat):
    import bpy
    me = bpy.data.meshes.get(PLANE_MESH)
    if me is None:
        s = CHUNK_SIZE
        me = _mesh_from_arrays(PLANE_MESH, [(0, 0, 0), (s, 0, 0), (s, s, 0), (0, s, 0)],
                               [0, 1, 2, 3], [4], mat)
        me.use_fake_user = True
    return me


def _ring_mesh(outline, zs, scales, cap_top=True, cap_bottom=True):
    """Stacked rings of an outline (m,2) at heights zs with radial scales -> verts, faces."""
    m = len(outline)
    verts = []
    for z, sc in zip(zs, scales):
        verts += [(outline[i, 0] * sc, outline[i, 1] * sc, z) for i in range(m)]
    faces, sizes = [], []
    for r in range(len(zs) - 1):
        for i in range(m):
            a = r * m + i; b = r * m + (i + 1) % m
            faces += [a, b, b + m, a + m]; sizes.append(4)
    if cap_top:
        c = len(verts); verts.append((0.0, 0.0, zs[-1] + 0.01))
        top = (len(zs) - 1) * m
        for i in range(m):
            faces += [top + i, top + (i + 1) % m, c]; sizes.append(3)
    if cap_bottom:
        faces += list(range(m - 1, -1, -1)); sizes.append(m)
    return verts, faces, sizes


def _protos(mat):
    """Unit prototypes (radius ~1, freeboard 1): 3 tabular + 3 irregular. Created once."""
    import bpy
    rng = np.random.default_rng(S0 + 77)
    tabs = []
    for i, name in enumerate(PROTO_TAB):
        me = bpy.data.meshes.get(name)
        if me is None:
            m = 48
            a = np.linspace(0, TAU, m, endpoint=False)
            aspect = [1.0, 0.62, 0.8][i]
            r = 1.0 + 0.06 * np.sin(a * 3 + rng.uniform(0, 6)) + 0.04 * np.sin(a * 7 + rng.uniform(0, 6))
            r += rng.normal(0, 0.025, m)
            notch = rng.integers(0, m, 3)
            for nn in notch:
                r[nn] *= 0.86; r[(nn + 1) % m] *= 0.92
            ol = np.stack([np.cos(a) * r, np.sin(a) * r * aspect], -1)
            v, f, s = _ring_mesh(ol, [-1.6, -0.1, 0.35, 0.93, 1.0], [0.88, 1.0, 1.005, 1.0, 0.975])
            me = _mesh_from_arrays(name, v, f, s, mat)
            me.use_fake_user = True
        tabs.append(me)
    irr = []
    for i, name in enumerate(PROTO_IRR):
        me = bpy.data.meshes.get(name)
        if me is None:
            # lat-long blob, displaced by random harmonics, pinnacles on top
            nu, nvv = 20, 11
            ph = rng.uniform(0, TAU, 6)
            verts = []
            for j in range(1, nvv):
                el = -math.pi / 2 + math.pi * j / nvv
                for k in range(nu):
                    az = TAU * k / nu
                    rr = (1.0 + 0.18 * math.sin(3 * az + ph[0]) * math.cos(2 * el + ph[1])
                          + 0.12 * math.sin(5 * az + ph[2] + 2 * el) + 0.06 * math.sin(9 * az + ph[3]))
                    x, y = math.cos(el) * math.cos(az) * rr, math.cos(el) * math.sin(az) * rr * 0.8
                    z = math.sin(el) * rr
                    if z > 0:
                        z *= 1.0 + 0.9 * max(0.0, math.sin(2 * az + ph[4] + i)) ** 2
                    else:
                        z *= 1.3
                    verts.append((x, y, z * 0.9))
            bot = len(verts); verts.append((0, 0, -1.25))
            top = len(verts); verts.append((0, 0, 1.0 + 0.3 * i))
            faces, sizes = [], []
            for j in range(nvv - 2):
                for k in range(nu):
                    a = j * nu + k; b = j * nu + (k + 1) % nu
                    faces += [a, b, b + nu, a + nu]; sizes.append(4)
            for k in range(nu):
                faces += [(k + 1) % nu, k, bot]; sizes.append(3)
                last = (nvv - 2) * nu
                faces += [last + k, last + (k + 1) % nu, top]; sizes.append(3)
            v = np.array(verts)
            v[:, 2] = v[:, 2] - 0.0
            v[:, 2] /= max(1e-6, v[:, 2].max())      # freeboard = 1
            me = _mesh_from_arrays(name, v, faces, sizes, mat)
            me.use_fake_user = True
        irr.append(me)
    return tabs, irr


def _sample_H(ctx, x, y):
    res = ctx.res
    fx = np.clip((x - ctx.origin[0]) / ctx.size * (res - 1), 0, res - 1.000001)
    fy = np.clip((y - ctx.origin[1]) / ctx.size * (res - 1), 0, res - 1.000001)
    i = fx.astype(np.int64); j = fy.astype(np.int64)
    u = fx - i; v = fy - j
    H = ctx.H
    return ((H[j, i] * (1 - u) + H[j, i + 1] * u) * (1 - v)
            + (H[j + 1, i] * (1 - u) + H[j + 1, i + 1] * u) * v)


def _cells(ctx, cell, seed, prob_fn, jit=0.2):
    """Scatter one candidate per global cell; keep those whose centre lies in this chunk.
    Returns ix, iy, x, y (world) after hash-jitter; prob_fn(x, y) -> keep probability."""
    x0, y0 = ctx.origin
    i0 = int(math.floor(x0 / cell)); i1 = int(math.floor((x0 + ctx.size) / cell))
    j0 = int(math.floor(y0 / cell)); j1 = int(math.floor((y0 + ctx.size) / cell))
    ii, jj = np.meshgrid(np.arange(i0, i1 + 1, dtype=np.int64), np.arange(j0, j1 + 1, dtype=np.int64))
    ii = ii.ravel(); jj = jj.ravel()
    x = (ii + 0.5 + (N.hash2(ii, jj, seed + 1) - 0.5) * 2 * jit) * cell
    y = (jj + 0.5 + (N.hash2(ii, jj, seed + 2) - 0.5) * 2 * jit) * cell
    inside = (x >= x0) & (x < x0 + ctx.size) & (y >= y0) & (y < y0 + ctx.size)
    ii, jj, x, y = ii[inside], jj[inside], x[inside], y[inside]
    return ii, jj, x, y


def _floes(ctx, mat, skirts, small):
    """Merged pack-ice mesh for the chunk (or None)."""
    x0, y0 = ctx.origin
    # candidate big floes
    tiers = [(FLOE_BIG_CELL, S0 + 300, 0.2, 0.5, 9)]
    if small:
        tiers.append((FLOE_SMALL_CELL, S0 + 400, 0.18, 0.45, 7))
    all_v, all_f, all_s = [], [], []
    vbase = 0
    big = None
    for cell, sd, rlo, rhi, nsides in tiers:
        ii, jj, x, y = _cells(ctx, cell, sd, None)
        if not len(x):
            continue
        oe, F = ice_edge_distance(x, y)
        lat = F['lat']
        edge = PACK_EDGE + PACK_EDGE_VAR * lat[:, F_CH]
        patch = 0.65 + 0.45 * N.perlin(x, y, S0 + 310, 1 / 9000.0)
        dens = np.clip(0.95 * (1.0 - _smoothstep(0.5 * edge, edge, oe)) * patch, 0, 0.95)
        rad = cell * (rlo + (rhi - rlo) * N.hash2(ii, jj, sd + 3) ** 1.3)
        keep = (N.hash2(ii, jj, sd) < dens) & (oe > rad + 30.0)
        if keep.any():
            hH = _sample_H(ctx, x, y)
            keep &= hH < -0.5
        if big is not None and keep.any():
            bx, by, br = big
            # reject small floes overlapping big ones (spatial hash on the big cell grid)
            bi = np.floor(bx / FLOE_BIG_CELL).astype(np.int64); bj = np.floor(by / FLOE_BIG_CELL).astype(np.int64)
            key = {}
            for k_, (a_, b_) in enumerate(zip(bi, bj)):
                key.setdefault((a_, b_), []).append(k_)
            si = np.floor(x / FLOE_BIG_CELL).astype(np.int64); sj = np.floor(y / FLOE_BIG_CELL).astype(np.int64)
            for k_ in np.nonzero(keep)[0]:
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        for q in key.get((si[k_] + da, sj[k_] + db), ()):
                            if (x[k_] - bx[q]) ** 2 + (y[k_] - by[q]) ** 2 < (br[q] + rad[k_] + 4.0) ** 2:
                                keep[k_] = False
                                break
                        if not keep[k_]:
                            break
                    if not keep[k_]:
                        break
        ii, jj, x, y, rad = ii[keep], jj[keep], x[keep], y[keep], rad[keep]
        if big is None:
            big = (x, y, rad)
        n = len(x)
        if n == 0:
            continue
        k = np.arange(nsides)
        ang = (k[None, :] + (N.hash2(ii[:, None] * nsides + k[None, :], jj[:, None], sd + 5) - 0.5) * 0.7) * (TAU / nsides)
        ang += N.hash2(ii, jj, sd + 6)[:, None] * TAU
        rr = rad[:, None] * (0.72 + 0.4 * N.hash2(ii[:, None] * nsides + k[None, :], jj[:, None], sd + 7))
        z = 0.25 + 0.45 * N.hash2(ii, jj, sd + 8)
        vx = x[:, None] - x0 + np.cos(ang) * rr
        vy = y[:, None] - y0 + np.sin(ang) * rr
        top = np.stack([vx, vy, np.broadcast_to(z[:, None], vx.shape)], -1)      # (n, m, 3)
        if skirts:
            bot = np.stack([vx, vy, np.full(vx.shape, -0.4)], -1)
            V = np.concatenate([top, bot], 1).reshape(-1, 3)
            per = 2 * nsides
        else:
            V = top.reshape(-1, 3)
            per = nsides
        base = vbase + np.arange(n)[:, None] * per
        Ft = (base + k[None, :]).reshape(-1)
        all_f.append(Ft); all_s.append(np.full(n, nsides))
        if skirts:
            a = base + k[None, :]; b = base + (k[None, :] + 1) % nsides
            q = np.stack([b, a, a + nsides, b + nsides], -1).reshape(-1)
            all_f.append(q); all_s.append(np.full(n * nsides, 4))
        all_v.append(V)
        vbase += len(V)
    if not all_v:
        return None
    return _mesh_from_arrays("SeaIce_%d_%d" % (ctx.cx, ctx.cy), np.concatenate(all_v),
                             np.concatenate(all_f), np.concatenate(all_s), mat)


def _bergs(ctx, mat, col, root):
    import bpy
    tabs, irr = _protos(mat)
    objs = []
    x0, y0 = ctx.origin
    specs = []
    # tabular: 150 m - 2 km across, 20-60 m freeboard
    ii, jj, x, y = _cells(ctx, BERG_TAB_CELL, S0 + 500, None, 0.3)
    if len(x):
        oe, F = ice_edge_distance(x, y)
        diam = 150.0 + 1850.0 * N.hash2(ii, jj, S0 + 503) ** 2.2
        p = 0.35 * _smoothstep(2e3, 10e3, oe) * (1.0 - _smoothstep(400e3, 700e3, oe))
        keep = (N.hash2(ii, jj, S0 + 500) < p) & (oe > diam * 0.65 + 400.0)
        for k in np.nonzero(keep)[0]:
            specs.append(('T', ii[k], jj[k], x[k], y[k], diam[k] * 0.5,
                          20.0 + 40.0 * N.hash2(ii[k], jj[k], S0 + 504)))
    # irregular: 20-150 m, 5-35 m high
    ii, jj, x, y = _cells(ctx, BERG_IRR_CELL, S0 + 600, None, 0.3)
    if len(x):
        oe, F = ice_edge_distance(x, y)
        diam = 20.0 + 130.0 * N.hash2(ii, jj, S0 + 603) ** 1.7
        p = 0.3 * _smoothstep(300.0, 3e3, oe) * (1.0 - _smoothstep(150e3, 300e3, oe))
        keep = (N.hash2(ii, jj, S0 + 600) < p) & (oe > diam + 60.0)
        for k in np.nonzero(keep)[0]:
            specs.append(('I', ii[k], jj[k], x[k], y[k], diam[k] * 0.5,
                          (5.0 + 30.0 * N.hash2(ii[k], jj[k], S0 + 604)) * min(1.0, diam[k] / 80.0 + 0.3)))
    if specs:
        hx = np.array([sp[3] for sp in specs]); hy = np.array([sp[4] for sp in specs])
        hH = _sample_H(ctx, hx, hy)
    for n_, (kind, i, j, x, y, rad, fb) in enumerate(specs):
        if hH[n_] > -3.0:
            continue
        h = N.hash2(np.int64(i), np.int64(j), S0 + 700)
        if kind == 'T':
            me = tabs[int(h * 3) % 3]
            sc = (rad, rad, fb)
            rot = (0.0, 0.0, float(N.hash2(np.int64(i), np.int64(j), S0 + 701) * TAU))
        else:
            me = irr[int(h * 3) % 3]
            sc = (rad, rad * (0.7 + 0.5 * h), fb)
            t1 = (N.hash2(np.int64(i), np.int64(j), S0 + 702) - 0.5) * 0.12
            rot = (float(t1), float(-t1), float(N.hash2(np.int64(i), np.int64(j), S0 + 701) * TAU))
        ob = bpy.data.objects.new("Berg_%d_%d_%d" % (ctx.cx, ctx.cy, n_), me)
        ob.location = (float(x - x0), float(y - y0), 0.0)
        ob.rotation_euler = rot
        ob.scale = sc
        col.objects.link(ob)
        ob.parent = root
        objs.append(ob)
    return objs


def chunk_objects(ctx):
    """Ocean plane + merged pack ice + iceberg linked duplicates, only for chunks with sea."""
    if float(np.min(ctx.H)) > 0.0:
        return []
    import bpy
    _init()
    col = ctx.collection if ctx.collection is not None else bpy.context.scene.collection
    root = ctx.root
    w_mat, si_mat, bg_mat = _mats()
    objs = []
    ob = bpy.data.objects.new("Ocean_%d_%d" % (ctx.cx, ctx.cy), _plane_mesh(w_mat))
    col.objects.link(ob)
    ob.parent = root
    objs.append(ob)
    # sea ice / bergs only where there is open sea (not just a fjord head)
    if float(np.min(ctx.H)) < -1.0:
        me = _floes(ctx, si_mat, skirts=ctx.lod <= 1, small=ctx.lod == 0)
        if me is not None:
            fo = bpy.data.objects.new("SeaIce_%d_%d" % (ctx.cx, ctx.cy), me)
            col.objects.link(fo)
            fo.parent = root
            objs.append(fo)
        objs += _bergs(ctx, bg_mat, col, root)
    return objs
