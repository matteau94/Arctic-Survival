"""Frozen rivers and lakes - owned by the rivers agent.

Frozen river beds follow the valley floors built by valleys.py:

  * TRUNK RIVERS on every major valley centre-line (network.py major channels, via
    valleys.valley_info()['sdist_major']). Channel 60 -> 400 m wide, growing downstream; the
    downstream proxy is ocean.coast_distance() (log scale, widest near the coast). The ice
    surface is LEVEL across the channel at  floor_major - bank  (bank 2 -> 6 m, deeper
    downstream) with a smooth bank ramp back up to the valley floor. Rivers run to the coast and
    stop in fjords / the sea (coast() runs after us and floods them; surface() puts no ice on
    anything below sea level).
  * TRIBUTARY RIVERS on the larger minor channels (near a trunk, gated by low-freq noise):
    40 -> 110 m wide, on the hanging tributary floor (floor_minor), ending at the trunk-valley lip.
  * A small meander warp (300-800 m amplitude, 1.3-4 km wavelength) shifts the centre-line inside
    the flat valley floor; the amplitude is capped so the river never leaves the floor.
  * FROZEN LAKES: sparse flat ice discs (0.5-3 km across) on trunk floors. One candidate per
    LAKE_CELL world cell (hash), projected onto the trunk centre-line, radius capped to fit the
    floor; the lake level is the lowest floor height around the disc minus a few metres, so the
    disc is exactly level. Per-cell results are memoised (pure, deterministic).

Everything is a pure vectorised function of world metres; the heavy inputs (valley_info,
coast_distance) are LRU-cached by their owners for the same grid, so carve() costs ~20-40 ms per
257^2 chunk.

chunk_objects(): the terrain grid is 100 m (LOD0) .. 400 m (LOD2), i.e. a 60-400 m river is only
0-4 vertices wide and the vertex-colour 'ice' mask alone renders as a fuzzy blue smear. So for
LOD <= RIBBON_MAX_LOD we add ONE merged "RiverIce" mesh per chunk: the terrain grid cells that
touch river/lake ice, lifted RIBBON_LIFT above the terrain faces (same quad split). Per-vertex
attributes carry the *signed* across-channel distance and half-width, which are near-linear, so
the shader reconstructs a crisp sub-cell ice outline (alpha-clipped) plus glossy blue ice,
Voronoi pressure-ridge cracks and drifted snow. Distant chunks rely on the terrain 'ice' mask.
"""
import math
import numpy as np

from . import noise as N
from .config import SEED, CHUNK_SIZE, SEA_LEVEL

# =========================================================================== tuning parameters
S0 = SEED + 12000

# trunk rivers
RIVER_HALF_W = (30.0, 200.0)          # m half-width: upstream .. at the coast  (60-400 m channel)
DOWNSTREAM_S = (8e3, 600e3)           # coast distance: full width at <= 8 km, min at >= 600 km
SOURCE_S = (1.25e6, 1.10e6)           # rivers fade in (source) between these coast distances
BANK_H = (2.0, 6.0)                   # ice surface below the valley floor: upstream .. coast
BANK_W = (25.0, 80.0)                 # horizontal width of the bank ramp
WIDTH_JITTER = 0.25                   # +-25 % low-frequency width variation
# meanders (lateral shift of the centre-line, capped to stay on the flat floor)
MEANDER_WL = (1300.0, 4200.0)          # wavelength range of the lateral wiggle (m)
MEANDER_AMP = (300.0, 800.0)          # target amplitude range (m)
MEANDER_FLOOR_FRAC = 0.55             # of (floor half-width - river half-width - bank)
# tributaries
TRIB_HALF_W = (20.0, 55.0)            # 40-110 m
TRIB_BANK_H = (1.5, 3.0)
TRIB_BANK_W = (15.0, 35.0)
TRIB_NEAR_TRUNK = (7000.0, 12000.0)   # tributary rivers only within this distance of a trunk
TRIB_GATE = (-0.05, 0.15)             # low-freq noise gate (fraction of tributaries kept ~45 %)
TRIB_MEANDER = 220.0
# lakes
LAKE_CELL = 16000.0                   # one candidate lake per cell
LAKE_PROB = 0.45
LAKE_R = (250.0, 1500.0)              # radius (disc 0.5-3 km)
LAKE_FIT = 0.85                       # r <= LAKE_FIT * trunk floor half-width
LAKE_BANK_W = 90.0
LAKE_DEPTH = 2.5                      # below the lowest floor sample around the disc
LAKE_S = (6e3, 1.1e6)                 # coast-distance range for lakes
# surface
DRIFT_WL = (300.0, 1500.0)            # snow-drift patch wavelengths (m)
DRIFT_AMOUNT = 0.35                   # max fraction of ice covered by drifted snow
ACTIVE_TOL = 1.5                      # m: ice only where the final surface is at river level
MIN_LEVEL = SEA_LEVEL + 0.6           # river ice never below this (coast() floods below)
# ribbon mesh
RIBBON_MAX_LOD = 1
RIBBON_LIFT = 0.3
RIBBON_MAT = "River_Ice"

_CACHE = []
_CACHE_N = 4
_LAKES = {}                            # (i, j) -> (cx, cy, r, level) or None


def _ss(e0, e1, x):
    return N.smoothstep(e0, e1, x)


def _lerp(a, b, t):
    return a + (b - a) * t


_WAVES = {}


def _waves(X, Y, seed, wl_min, wl_max, n=4):
    """Cheap smooth pseudo-noise in ~[-1, 1]: sum of n plane sine waves with deterministic random
    directions, log-spaced wavelengths and phases (~1 ms per 257^2 per wave vs ~60 ms for perlin).
    Pure function of world position, so seams match."""
    w = _WAVES.get((seed, wl_min, wl_max, n))
    if w is None:
        rng = np.random.default_rng(seed)
        ang = rng.uniform(0, 2 * np.pi, n)
        wl = np.exp(np.linspace(np.log(wl_max), np.log(wl_min), n)) * rng.uniform(0.85, 1.15, n)
        amp = (wl / wl_max) ** 0.5
        amp = amp / amp.sum() * 1.6
        w = [(2 * np.pi * math.cos(a) / l, 2 * np.pi * math.sin(a) / l, rng.uniform(0, 2 * np.pi), am)
             for a, l, am in zip(ang, wl, amp)]
        _WAVES[(seed, wl_min, wl_max, n)] = w
    out = np.zeros(np.shape(X))
    if _is_meshgrid(X, Y):
        # separable: sin(a + b) = sin a cos b + cos a sin b with 1-D a(x), b(y) -> no per-point sin
        xs = X[0]; ys = Y[:, 0]
        for kx, ky, ph, am in w:
            a = xs * kx; b = ys * ky + ph
            out += np.multiply.outer(am * np.cos(b), np.sin(a))
            out += np.multiply.outer(am * np.sin(b), np.cos(a))
    else:
        for kx, ky, ph, am in w:
            out += am * np.sin(X * kx + Y * ky + ph)
    return np.clip(out, -1.0, 1.0)


def _is_meshgrid(X, Y):
    return (np.ndim(X) == 2 and X.shape[0] > 1 and X.shape[1] > 1
            and np.array_equal(X[0], X[-1]) and np.array_equal(Y[:, 0], Y[:, -1])
            and X[0, 0] == X[-1, 0] and Y[0, 0] == Y[0, -1])


def _key(X, Y):
    xf = X.reshape(-1); yf = Y.reshape(-1); n = xf.size
    return (X.shape, float(xf[0]), float(xf[-1]), float(yf[0]), float(yf[-1]),
            float(xf[n // 2]), float(yf[n // 3]), float(xf[::97].sum()), float(yf[::89].sum()))


# =========================================================================== lakes
def _lake_cell(i, j):
    k = (i, j)
    if k in _LAKES:
        return _LAKES[k]
    from . import network as NW, valleys, ocean
    res = None
    ii = np.array([i]); jj = np.array([j])
    if N.hash2(ii, jj, S0 + 1)[0] < LAKE_PROB:
        x = (i + 0.2 + 0.6 * N.hash2(ii, jj, S0 + 2)[0]) * LAKE_CELL
        y = (j + 0.2 + 0.6 * N.hash2(ii, jj, S0 + 3)[0]) * LAKE_CELL
        # Newton-project onto the trunk centre-line (zero line of the network noise)
        e = 25.0
        for _ in range(6):
            n = NW.major_distance(np.array([x, x + e, x]), np.array([y, y, y + e]))[1]
            gx, gy = (n[1] - n[0]) / e, (n[2] - n[0]) / e
            g2 = gx * gx + gy * gy + 1e-30
            dx, dy = -n[0] * gx / g2, -n[0] * gy / g2
            step = math.hypot(dx, dy)
            if step > 4000.0:
                dx, dy = dx * 4000.0 / step, dy * 4000.0 / step
            x += dx; y += dy
            if step < 1.0:
                break
        cx0, cy0 = (i + 0.5) * LAKE_CELL, (j + 0.5) * LAKE_CELL
        if abs(x - cx0) < 0.5 * LAKE_CELL and abs(y - cy0) < 0.5 * LAKE_CELL:
            r = LAKE_R[0] + (LAKE_R[1] - LAKE_R[0]) * N.hash2(ii, jj, S0 + 4)[0] ** 1.6
            px = np.array([x, x + r, x - r, x, x, x + 0.7 * r, x - 0.7 * r, x + 0.7 * r, x - 0.7 * r])
            py = np.array([y, y, y, y + r, y - r, y + 0.7 * r, y - 0.7 * r, y - 0.7 * r, y + 0.7 * r])
            # don't let these 9-point queries evict the chunk grid from the owners' tiny LRUs
            saved_v, saved_o = list(valleys._CACHE), list(ocean._CACHE)
            try:
                v = valleys.valley_info(px, py)
                s = ocean.coast_distance(px, py)
            finally:
                valleys._CACHE[:] = saved_v
                ocean._CACHE[:] = saved_o
            r = min(r, LAKE_FIT * float(v['width_major'][0]) - abs(float(v['sdist_major'][0])))
            if r >= LAKE_R[0] * 0.8 and abs(float(v['sdist_major'][0])) < 200.0 \
                    and LAKE_S[0] < s.min() and s.max() < LAKE_S[1] \
                    and v['carve_fade'].min() > 0.99:
                level = float(v['floor_major'].min()) - LAKE_DEPTH
                if level > MIN_LEVEL + 2.0:
                    res = (x, y, r, level)
    _LAKES[k] = res
    return res


def _lakes_in(x0, x1, y0, y1):
    pad = LAKE_R[1] * 1.3 + LAKE_BANK_W
    i0 = int(math.floor((x0 - pad) / LAKE_CELL)); i1 = int(math.floor((x1 + pad) / LAKE_CELL))
    j0 = int(math.floor((y0 - pad) / LAKE_CELL)); j1 = int(math.floor((y1 + pad) / LAKE_CELL))
    out = []
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            L = _lake_cell(i, j)
            if L is not None:
                cx, cy, r, lv = L
                if x0 - pad < cx < x1 + pad and y0 - pad < cy < y1 + pad:
                    out.append(L)
    return out


# =========================================================================== core fields
def _fields(X, Y, land=None):
    """All river/lake fields on the points (shape of X). Cached by grid."""
    X = np.asarray(X, np.float64); Y = np.asarray(Y, np.float64)
    k = _key(X, Y)
    for kk, v in _CACHE:
        if kk == k:
            return v
    from . import valleys, ocean
    v = valleys.valley_info(X, Y, None, land)
    s = ocean.coast_distance(X, Y)
    onland = _ss(0.0, 300.0, s) * v['carve_fade']

    # ---- trunk river
    ls = np.log(np.clip(s, DOWNSTREAM_S[0], DOWNSTREAM_S[1]))
    down = (math.log(DOWNSTREAM_S[1]) - ls) / (math.log(DOWNSTREAM_S[1]) - math.log(DOWNSTREAM_S[0]))
    down = down * down * (3 - 2 * down)                       # 0 upstream .. 1 at the coast
    src = _ss(SOURCE_S[0], SOURCE_S[1], s)
    jit = 1.0 + WIDTH_JITTER * _waves(X, Y, S0 + 10, 12000.0, 40000.0, 3)
    hw = _lerp(RIVER_HALF_W[0], RIVER_HALF_W[1], down) * jit * src
    bh = _lerp(BANK_H[0], BANK_H[1], down) * (0.3 + 0.7 * src)
    bw = _lerp(BANK_W[0], BANK_W[1], down)
    m = _waves(X, Y, S0 + 20, MEANDER_WL[0], MEANDER_WL[1], 5)
    amp_t = _lerp(MEANDER_AMP[0], MEANDER_AMP[1], 0.5 + 0.5 * _waves(X, Y, S0 + 22, 15000.0, 35000.0, 2))
    amp = np.clip(MEANDER_FLOOR_FRAC * (v['width_major'] - hw - bw), 0.0, amp_t)
    sd = v['sdist_major'] - amp * m
    lvl = np.maximum(v['floor_major'] - bh, MIN_LEVEL)
    on_r = onland * _ss(0.0, 5.0, hw)

    # ---- tributaries
    gate = _ss(TRIB_GATE[0], TRIB_GATE[1], _waves(X, Y, S0 + 30, 9000.0, 25000.0, 3))
    near = 1.0 - _ss(TRIB_NEAR_TRUNK[0], TRIB_NEAR_TRUNK[1], v['dist_major'])
    tw = _lerp(TRIB_HALF_W[0], TRIB_HALF_W[1], down) * gate * near * src \
        * _ss(0.5, 0.9, v['minor_strength'])
    tbh = _lerp(TRIB_BANK_H[0], TRIB_BANK_H[1], down)
    tbw = _lerp(TRIB_BANK_W[0], TRIB_BANK_W[1], down)
    tamp = np.clip(0.5 * (v['width_minor'] - tw - tbw), 0.0, TRIB_MEANDER)
    tsd = v['sdist_minor'] - tamp * _waves(X, Y, S0 + 31, 900.0, 2200.0, 3)
    tlvl = np.maximum(v['floor_minor'] - tbh, MIN_LEVEL)
    on_t = onland * _ss(0.0, 5.0, tw)

    # ---- lakes
    lakes = _lakes_in(X.min(), X.max(), Y.min(), Y.max())
    lf = np.full(X.shape, 1e9); llv = np.zeros(X.shape)
    if lakes:
        wob = _waves(X, Y, S0 + 40, 700.0, 2500.0, 4)
        for cx, cy, r, lv in lakes:
            f = np.hypot(X - cx, Y - cy) - r * (1.0 + 0.15 * wob)
            sel = f < lf
            lf = np.where(sel, f, lf); llv = np.where(sel, lv, llv)
    F = dict(sd=sd, hw=hw * on_r, bh=bh, bw=bw, lvl=lvl, on_r=on_r,
             tsd=tsd, tw=tw * on_t, tbw=tbw, tlvl=tlvl, on_t=on_t,
             lf=lf, llv=llv, onland=onland, lakes=lakes)
    _CACHE.insert(0, (k, F))
    del _CACHE[_CACHE_N:]
    return F


def _profiles(F):
    """Bed-blend weights (1 on the level ice, smooth 0 across the bank)."""
    pr = (1.0 - _ss(F['hw'], F['hw'] + F['bw'], np.abs(F['sd']))) * F['on_r']
    pt = (1.0 - _ss(F['tw'], F['tw'] + F['tbw'], np.abs(F['tsd']))) * F['on_t']
    pl = (1.0 - _ss(0.0, LAKE_BANK_W, F['lf'])) * F['onland']
    return pr, pt, pl


# =========================================================================== public API
def carve(X, Y, h, land):
    h = np.asarray(h, np.float64)
    F = _fields(X, Y, land)
    pr, pt, pl = _profiles(F)
    out = h
    out = out + (np.minimum(out, F['tlvl']) - out) * pt
    out = out + (np.minimum(out, F['lvl']) - out) * pr
    if F['lakes']:
        out = out + (np.minimum(out, F['llv']) - out) * pl
    return out


def _coverage(F, H, spacing):
    """0..1 ice coverage per vertex (anti-aliased over ~half a grid cell), only where the final
    surface actually sits at the river / lake level (not over walls, lips, fjords or sea)."""
    a = 0.5 * spacing
    cr = (1.0 - _ss(-a, a, np.abs(F['sd']) - F['hw'])) * _ss(0.0, 1.0, F['hw'])
    cr *= 1.0 - _ss(ACTIVE_TOL, 2 * ACTIVE_TOL, np.abs(H - F['lvl']))
    ct = (1.0 - _ss(-a, a, np.abs(F['tsd']) - F['tw'])) * _ss(0.0, 1.0, F['tw'])
    ct *= 1.0 - _ss(ACTIVE_TOL, 2 * ACTIVE_TOL, np.abs(H - F['tlvl']))
    cov = np.maximum(cr, ct)
    if F['lakes']:
        cl = (1.0 - _ss(-a, a, F['lf'])) * (1.0 - _ss(ACTIVE_TOL, 2 * ACTIVE_TOL, np.abs(H - F['llv'])))
        cov = np.maximum(cov, cl)
    return cov * F['onland'] * _ss(SEA_LEVEL + 0.3, SEA_LEVEL + 0.8, H)


def surface(X, Y, H, land, masks):
    X = np.asarray(X, np.float64); Y = np.asarray(Y, np.float64); H = np.asarray(H, np.float64)
    F = _fields(X, Y, land)
    sp = abs(float(X.reshape(-1)[1] - X.reshape(-1)[0])) if X.ndim == 2 and X.shape[1] > 1 else 50.0
    cov = _coverage(F, H, max(sp, 20.0))
    masks['river'] = cov                    # extra (unused by the terrain shader)
    if not cov.any():
        return
    drift = _waves(X, Y, S0 + 50, DRIFT_WL[0], DRIFT_WL[1], 7)
    drift = DRIFT_AMOUNT * _ss(-0.15, 0.45, drift)
    ice = cov * (1.0 - drift)
    ice = ice * (1.0 - np.asarray(masks.get('water', 0.0)))
    old_ice = masks['ice']
    new_ice = np.maximum(old_ice, ice)
    rock = masks['rock'] * (1.0 - cov)                 # banks/bed are snow or ice, not rock
    # weight moves rock -> snow, then snow -> ice (sum preserved)
    masks['snow'] = np.clip(masks['snow'] + (masks['rock'] - rock) - (new_ice - old_ice), 0.0, 1.0)
    masks['rock'] = rock
    masks['ice'] = new_ice


# =========================================================================== chunk ribbon mesh
def _ribbon_fields(ctx):
    """River fields cropped to ctx's grid. Reuses the padded-grid cache from carve()/surface()."""
    X, Y = ctx.X, ctx.Y
    r = X.shape[0]
    for kk, v in _CACHE:
        shp = kk[0]
        if shp == (r + 2, r + 2):
            sd = v['sd']
            # padded grid starts one sample before the chunk
            if abs(kk[1] + (X[0, 1] - X[0, 0]) - X[0, 0]) < 1e-6 and \
                    abs(kk[3] + (Y[1, 0] - Y[0, 0]) - Y[0, 0]) < 1e-6:
                s = (slice(1, -1), slice(1, -1))
                return {k: (a[s] if isinstance(a, np.ndarray) and a.shape == sd.shape else a)
                        for k, a in v.items()}
    return _fields(X, Y, ctx.land)


def _build_material(mat):
    from . import materials as M
    nt = mat.node_tree
    nt.nodes.clear()
    L = nt.links.new
    n = M._n
    out = n(nt, 'ShaderNodeOutputMaterial', (1700, 0))
    bsdf = n(nt, 'ShaderNodeBsdfPrincipled', (1100, 100))

    def attr(name, loc):
        a = n(nt, 'ShaderNodeAttribute', loc, attribute_name=name)
        a.attribute_type = 'GEOMETRY'
        return a

    def math_(op, loc, a=None, b=None):
        m = n(nt, 'ShaderNodeMath', loc, operation=op)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                L(v, m.inputs[i])
        return m.outputs[0]

    # --- ice outline: min(|sd|-hw, |tsd|-tw, lake_f) < 0
    ra = attr('rv_a', (-1500, 500))          # (sd, hw, tsd, tw)
    rb = attr('rv_b', (-1500, 250))          # (lake_f, drift, -, -)
    sa = n(nt, 'ShaderNodeSeparateColor', (-1300, 500)); L(ra.outputs['Color'], sa.inputs[0])
    sb = n(nt, 'ShaderNodeSeparateColor', (-1300, 250)); L(rb.outputs['Color'], sb.inputs[0])
    fr = math_('SUBTRACT', (-1100, 600), math_('ABSOLUTE', (-1200, 650), sa.outputs[0]), sa.outputs[1])
    ft = math_('SUBTRACT', (-1100, 450), math_('ABSOLUTE', (-1200, 450), sa.outputs[2]), ra.outputs['Alpha'])
    f = math_('MINIMUM', (-950, 500), fr, ft)
    f = math_('MINIMUM', (-800, 450), f, sb.outputs[0])
    alpha = math_('LESS_THAN', (-650, 450), f, 0.0)

    # --- texture space: object coords + per-object world offset (continuous across chunks)
    tc = n(nt, 'ShaderNodeTexCoord', (-1500, -200))
    off = n(nt, 'ShaderNodeAttribute', (-1500, -400), attribute_name='ice_offset')
    off.attribute_type = 'OBJECT'
    P = n(nt, 'ShaderNodeVectorMath', (-1300, -250), operation='ADD')
    L(tc.outputs['Object'], P.inputs[0]); L(off.outputs['Vector'], P.inputs[1])
    P = P.outputs[0]
    # pressure ridges: warped large Voronoi edges; fine cracks: small Voronoi edges
    wn = n(nt, 'ShaderNodeTexNoise', (-1100, -150)); wn.inputs['Scale'].default_value = 0.02
    wn.inputs['Detail'].default_value = 2.0
    L(P, wn.inputs['Vector'])
    wv = n(nt, 'ShaderNodeVectorMath', (-900, -200), operation='SCALE')
    wv.inputs['Scale'].default_value = 25.0
    L(wn.outputs['Color'], wv.inputs[0])
    P2 = n(nt, 'ShaderNodeVectorMath', (-750, -250), operation='ADD')
    L(P, P2.inputs[0]); L(wv.outputs[0], P2.inputs[1])
    P2 = P2.outputs[0]
    v1 = n(nt, 'ShaderNodeTexVoronoi', (-550, -150), feature='DISTANCE_TO_EDGE')
    v1.inputs['Scale'].default_value = 1.0 / 45.0
    L(P2, v1.inputs['Vector'])
    v2 = n(nt, 'ShaderNodeTexVoronoi', (-550, -400), feature='DISTANCE_TO_EDGE')
    v2.inputs['Scale'].default_value = 1.0 / 7.0
    L(P2, v2.inputs['Vector'])
    ridge = n(nt, 'ShaderNodeMapRange', (-350, -150))
    ridge.inputs['From Min'].default_value = 0.0; ridge.inputs['From Max'].default_value = 0.035
    ridge.inputs['To Min'].default_value = 1.0; ridge.inputs['To Max'].default_value = 0.0
    L(v1.outputs['Distance'], ridge.inputs['Value'])
    crack = n(nt, 'ShaderNodeMapRange', (-350, -400))
    crack.inputs['From Min'].default_value = 0.0; crack.inputs['From Max'].default_value = 0.03
    crack.inputs['To Min'].default_value = 0.5; crack.inputs['To Max'].default_value = 0.0
    L(v2.outputs['Distance'], crack.inputs['Value'])
    cr = math_('MAXIMUM', (-150, -250), ridge.outputs[0], crack.outputs[0])

    # --- ice colour: deep blue clear ice with lighter mottling; cracks whiter (fractured)
    nc = n(nt, 'ShaderNodeTexNoise', (-550, 250)); nc.inputs['Scale'].default_value = 1.0 / 60.0
    nc.inputs['Detail'].default_value = 4.0
    L(P, nc.inputs['Vector'])
    ramp = n(nt, 'ShaderNodeValToRGB', (-350, 250))
    ramp.color_ramp.elements[0].color = (0.03, 0.17, 0.36, 1)
    ramp.color_ramp.elements[1].color = (0.20, 0.48, 0.70, 1)
    ramp.color_ramp.elements[0].position = 0.3; ramp.color_ramp.elements[1].position = 0.75
    L(nc.outputs['Fac'], ramp.inputs[0])
    mc = M._mix(nt, (0, 150)); fc, ac, bc, oc = M._mix_io(mc)
    L(cr, fc); L(ramp.outputs[0], ac); bc.default_value = (0.80, 0.90, 0.97, 1)
    # drifted snow patches (drift attribute modulated by fine noise)
    ns = n(nt, 'ShaderNodeTexNoise', (-550, 0)); ns.inputs['Scale'].default_value = 1.0 / 12.0
    ns.inputs['Detail'].default_value = 5.0
    L(P, ns.inputs['Vector'])
    dsum = math_('ADD', (-350, 0), ns.outputs['Fac'], sb.outputs[1])
    dmask = n(nt, 'ShaderNodeMapRange', (-150, 0))
    dmask.inputs['From Min'].default_value = 0.68; dmask.inputs['From Max'].default_value = 0.88
    L(dsum, dmask.inputs['Value'])
    ms = M._mix(nt, (200, 150)); fs, as_, bs, os_ = M._mix_io(ms)
    L(dmask.outputs[0], fs); L(oc, as_); bs.default_value = (0.90, 0.94, 1.0, 1)
    L(os_, bsdf.inputs['Base Color'])
    rg = M._mix(nt, (200, -100), 'FLOAT'); fr_, ar_, br_, or_ = M._mix_io(rg)
    L(dmask.outputs[0], fr_); ar_.default_value = 0.14; br_.default_value = 0.7
    rg2 = math_('ADD', (400, -150), or_, math_('MULTIPLY', (300, -250), cr, 0.25))
    L(rg2, bsdf.inputs['Roughness'])
    bump = n(nt, 'ShaderNodeBump', (800, -300))
    bump.inputs['Strength'].default_value = 0.35; bump.inputs['Distance'].default_value = 0.05
    inv = math_('SUBTRACT', (600, -300), 1.0, cr)
    L(inv, bump.inputs['Height'])
    L(bump.outputs['Normal'], bsdf.inputs['Normal'])
    try:
        bsdf.inputs['Specular IOR Level'].default_value = 0.35
        bsdf.inputs['IOR'].default_value = 1.31
        bsdf.inputs['Coat Weight'].default_value = 0.15
        bsdf.inputs['Coat Roughness'].default_value = 0.03
        bsdf.inputs['Emission Color'].default_value = (0.2, 0.45, 0.7, 1)
        bsdf.inputs['Emission Strength'].default_value = 0.0
    except KeyError:
        pass
    tr = n(nt, 'ShaderNodeBsdfTransparent', (1100, 350))
    mix = n(nt, 'ShaderNodeMixShader', (1400, 200))
    L(alpha, mix.inputs[0]); L(tr.outputs[0], mix.inputs[1]); L(bsdf.outputs[0], mix.inputs[2])
    L(mix.outputs[0], out.inputs['Surface'])
    M.add_distance_fog(mat, mix.outputs[0])
    try:
        mat.surface_render_method = 'DITHERED'
    except Exception:
        pass
    try:
        mat.use_transparency_overlap = False
    except Exception:
        pass


def material():
    from . import materials as M
    return M.get_or_create(RIBBON_MAT, _build_material)


def chunk_objects(ctx):
    if ctx.lod > RIBBON_MAX_LOD:
        return []
    import bpy
    F = _ribbon_fields(ctx)
    H = ctx.H
    res = ctx.res
    sp = ctx.size / (res - 1)
    cov = _coverage(F, H, 2.0 * sp)             # generous: which vertices touch ice
    if not (cov > 0.01).any():
        return []
    # cells whose 4 corners have any coverage (plus 1-cell dilation for the sub-cell outline)
    c = cov > 0.01
    cell = c[:-1, :-1] | c[1:, :-1] | c[:-1, 1:] | c[1:, 1:]
    d = cell.copy()
    d[1:, :] |= cell[:-1, :]; d[:-1, :] |= cell[1:, :]
    d[:, 1:] |= cell[:, :-1]; d[:, :-1] |= cell[:, 1:]
    cell = d
    rr, cc = np.nonzero(cell)
    if not len(rr):
        return []
    i0 = rr * res + cc
    quads = np.stack([i0, i0 + 1, i0 + res + 1, i0 + res], axis=1)
    used, inv = np.unique(quads.ravel(), return_inverse=True)
    loops = inv.astype(np.int32)
    t = np.arange(res, dtype=np.float64) * sp
    ly, lx = np.divmod(used, res)
    co = np.empty((len(used), 3), np.float32)
    co[:, 0] = t[lx]; co[:, 1] = t[ly]; co[:, 2] = H.ravel()[used] + RIBBON_LIFT

    # per-vertex outline fields; inactive river parts get a huge negative half-width -> no ice
    act_r = (np.abs(H - F['lvl']) < 2 * ACTIVE_TOL) & (H > SEA_LEVEL + 0.5)
    act_t = (np.abs(H - F['tlvl']) < 2 * ACTIVE_TOL) & (H > SEA_LEVEL + 0.5)
    act_l = (np.abs(H - F['llv']) < 2 * ACTIVE_TOL) & (H > SEA_LEVEL + 0.5)
    hw = np.where(act_r, F['hw'], -60.0)
    tw = np.where(act_t, F['tw'], -60.0)
    lf = np.where(act_l, F['lf'], 60.0 + np.maximum(F['lf'], 0.0))
    drift = _waves(ctx.X, ctx.Y, S0 + 50, DRIFT_WL[0], DRIFT_WL[1], 7)
    A = np.stack([F['sd'], hw, F['tsd'], tw], -1).reshape(-1, 4)[used].astype(np.float32)
    B = np.stack([np.clip(lf, -1e4, 1e4), 0.3 * drift, np.zeros_like(lf), np.ones_like(lf)],
                 -1).reshape(-1, 4)[used].astype(np.float32)

    name = f"RiverIce_{ctx.cx}_{ctx.cy}"
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(used))
    me.attributes['position'].data.foreach_set('vector', co.ravel())
    me.loops.add(len(loops))
    me.attributes['.corner_vert'].data.foreach_set('value', loops)
    me.polygons.add(len(quads))
    me.polygons.foreach_set('loop_start', np.arange(0, 4 * len(quads), 4, dtype=np.int32))
    me.update(calc_edges=True)
    for nm, arr in (('rv_a', A), ('rv_b', B)):
        a = me.attributes.new(nm, 'FLOAT_COLOR', 'POINT')
        a.data.foreach_set('color', arr.ravel())
    me.shade_smooth()
    me.materials.append(material())
    ob = bpy.data.objects.new(name, me)
    ox = math.fmod(ctx.origin[0], 8 * CHUNK_SIZE); oy = math.fmod(ctx.origin[1], 8 * CHUNK_SIZE)
    ob["ice_offset"] = (ox, oy, 0.0)
    try:
        ob.visible_shadow = False
    except Exception:
        pass
    if ctx.collection is not None:
        ctx.collection.objects.link(ob)
    ob.parent = ctx.root
    return [ob]
