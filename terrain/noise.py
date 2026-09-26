"""Vectorised, deterministic 2-D noise over numpy arrays (float64 world metres).

Every function takes arrays X, Y of equal shape and returns an array of that shape. They are
pure functions of (x, y, seed) so any chunk can be generated independently and neighbouring
chunks match exactly along shared edges.
"""
import numpy as np

_PERM_CACHE = {}


def _perm(seed):
    p = _PERM_CACHE.get(seed)
    if p is None:
        rng = np.random.default_rng(seed)
        base = rng.permutation(256).astype(np.int64)
        p = np.concatenate([base, base])
        _PERM_CACHE[seed] = p
    return p


_GRAD = np.array([(np.cos(a), np.sin(a)) for a in np.linspace(0, 2 * np.pi, 16, endpoint=False)])


def _fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)


def _dfade(t):
    return 30 * t * t * (t * (t - 2) + 1)


def perlin(X, Y, seed=0, freq=1.0, with_grad=False):
    """Gradient noise in ~[-1, 1]. freq is cycles per metre (e.g. 1/5000).
    with_grad=True also returns (dn/dx, dn/dy) in per-metre units."""
    p = _perm(seed)
    x = np.asarray(X, dtype=np.float64) * freq
    y = np.asarray(Y, dtype=np.float64) * freq
    xi = np.floor(x); yi = np.floor(y)
    xf = x - xi; yf = y - yi
    xi = xi.astype(np.int64) & 255; yi = yi.astype(np.int64) & 255

    def g(ix, iy, dx, dy):
        h = p[p[ix] + iy] & 15
        gv = _GRAD[h]
        return gv[..., 0] * dx + gv[..., 1] * dy, gv[..., 0], gv[..., 1]

    n00, gx00, gy00 = g(xi, yi, xf, yf)
    n10, gx10, gy10 = g(xi + 1 & 255, yi, xf - 1, yf)
    n01, gx01, gy01 = g(xi, yi + 1 & 255, xf, yf - 1)
    n11, gx11, gy11 = g(xi + 1 & 255, yi + 1 & 255, xf - 1, yf - 1)
    u = _fade(xf); v = _fade(yf)
    nx0 = n00 + u * (n10 - n00)
    nx1 = n01 + u * (n11 - n01)
    n = (nx0 + v * (nx1 - nx0)) * 1.41421356
    if not with_grad:
        return n
    du = _dfade(xf); dv = _dfade(yf)
    # analytic derivative of bilinear-blended gradient noise
    a, b, c, d = n00, n10 - n00, n01 - n00, n11 - n10 - n01 + n00
    ga_x = gx00 + u * (gx10 - gx00); ga_x = ga_x + v * ((gx01 + u * (gx11 - gx01)) - ga_x)
    ga_y = gy00 + u * (gy10 - gy00); ga_y = ga_y + v * ((gy01 + u * (gy11 - gy01)) - ga_y)
    dndx = ga_x + du * (b + d * v)
    dndy = ga_y + dv * (c + d * u)
    s = 1.41421356 * freq
    return n, dndx * s, dndy * s


def fbm(X, Y, seed=0, freq=1.0, octaves=5, lacunarity=2.0, gain=0.5):
    """Fractal sum of perlin, normalised to ~[-1, 1]."""
    total = np.zeros(np.shape(X)); amp = 1.0; norm = 0.0; f = freq
    for o in range(octaves):
        total += amp * perlin(X, Y, seed + o * 101, f)
        norm += amp; amp *= gain; f *= lacunarity
    return total / norm


def ridged(X, Y, seed=0, freq=1.0, octaves=5, lacunarity=2.0, gain=0.5, sharpness=2.0):
    """Ridged multifractal in [0, 1]; sharp crests at 1. Good for mountain ranges."""
    total = np.zeros(np.shape(X)); amp = 1.0; norm = 0.0; f = freq
    weight = np.ones(np.shape(X))
    for o in range(octaves):
        r = (1.0 - np.abs(perlin(X, Y, seed + o * 131, f))) ** sharpness
        r *= weight
        weight = np.clip(r * 1.5, 0.0, 1.0)
        total += amp * r
        norm += amp; amp *= gain; f *= lacunarity
    return total / norm


def warp(X, Y, seed=0, freq=1.0, amount=1.0, octaves=3):
    """Domain warp: returns displaced (X', Y'). amount in metres."""
    wx = fbm(X, Y, seed + 7, freq, octaves)
    wy = fbm(X, Y, seed + 13, freq, octaves)
    return X + wx * amount, Y + wy * amount


def hash2(ix, iy, seed=0):
    """Deterministic uniform [0,1) per integer cell (arrays ok). For scattering objects."""
    ix = np.asarray(ix, dtype=np.uint64); iy = np.asarray(iy, dtype=np.uint64)
    h = (ix * np.uint64(0x9E3779B97F4A7C15)) ^ (iy * np.uint64(0xC2B2AE3D27D4EB4F)) ^ np.uint64(seed * 0x165667B19E3779F9 & 0xFFFFFFFFFFFFFFFF)
    h ^= h >> np.uint64(33); h *= np.uint64(0xFF51AFD7ED558CCD); h ^= h >> np.uint64(33)
    return (h >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)
