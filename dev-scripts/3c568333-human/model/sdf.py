"""Implicit-field toolkit (prototype; merged into human_build.py later)."""
import numpy as np


def A(x):
    return np.asarray(x, dtype=np.float64)


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, dtype=float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def g(x, c, w):
    return np.exp(-((x - c) / w) ** 2)


def sd_ell(P, c, r):
    """Approximate ellipsoid distance (IQ)."""
    q = (P - A(c)) / A(r)
    k0 = np.linalg.norm(q, axis=-1)
    k1 = np.linalg.norm(q / A(r), axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def sd_sph(P, c, r):
    return np.linalg.norm(P - A(c), axis=-1) - r


def sd_cap(P, a, b, ra, rb=None):
    """Capsule / round cone (linearly varying radius) from a to b."""
    rb = ra if rb is None else rb
    a, b = A(a), A(b)
    pa = P - a
    ba = b - a
    h = np.clip((pa @ ba) / (ba @ ba), 0.0, 1.0)
    return np.linalg.norm(pa - h[..., None] * ba, axis=-1) - (ra + (rb - ra) * h)


def sd_chain(P, pts, rads, k=0.004):
    d = None
    for i in range(len(pts) - 1):
        di = sd_cap(P, pts[i], pts[i + 1], rads[i], rads[i + 1])
        d = di if d is None else smin(d, di, k)
    return d


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def warp(keys, lo, hi):
    """Grid positions from lo to hi whose spacing follows keys [(x, spacing)]."""
    xs = np.linspace(lo, hi, 20000)
    sp = np.interp(xs, [k[0] for k in keys], [k[1] for k in keys])
    inv = 1.0 / sp
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (inv[1:] + inv[:-1]) * np.diff(xs))])
    n = max(2, int(round(cum[-1])))
    return np.interp(np.linspace(0, cum[-1], n + 1), cum, xs)


def raycast(O, D, F, t0, t1, n=64, bis=18, chunk=40000):
    """Outermost crossing of F = 0 along O + t D, t in [t0, t1] (searched from the outside in)."""
    O = np.broadcast_to(O, D.shape).astype(np.float64)
    out = np.empty(len(D))
    ts = np.linspace(t1, t0, n)
    for c0 in range(0, len(D), chunk):
        o, d = O[c0:c0 + chunk], D[c0:c0 + chunk]
        m = len(d)
        P = o[:, None, :] + d[:, None, :] * ts[None, :, None]
        f = F(P.reshape(-1, 3)).reshape(m, n)
        inside = f < 0
        first = np.argmax(inside, axis=1)                 # first sample inside, coming from outside
        none = ~inside.any(axis=1)
        first = np.where(none, n - 1, np.maximum(first, 1))
        hi = ts[first - 1].copy()                         # outside
        lo = ts[first].copy()                             # inside
        for _ in range(bis):
            mid = 0.5 * (hi + lo)
            fm = F(o + d * mid[:, None])
            ins = fm < 0
            lo = np.where(ins, mid, lo)
            hi = np.where(ins, hi, mid)
        out[c0:c0 + chunk] = 0.5 * (hi + lo)
    return out


def grad(F, P, h=2e-4):
    gx = F(P + [h, 0, 0]) - F(P - [h, 0, 0])
    gy = F(P + [0, h, 0]) - F(P - [0, h, 0])
    gz = F(P + [0, 0, h]) - F(P - [0, 0, h])
    G = np.stack([gx, gy, gz], -1)
    return G / np.maximum(np.linalg.norm(G, axis=-1, keepdims=True), 1e-12)


def sd_rbox(P, c, h, r):
    q = np.abs(P - A(c)) - A(h)
    return np.linalg.norm(np.maximum(q, 0.0), axis=-1) + np.minimum(np.max(q, axis=-1), 0.0) - r


def hermite(keys, t):
    n = len(keys)
    if t <= keys[0][0]:
        return keys[0][1]
    if t >= keys[-1][0]:
        return keys[-1][1]
    def slope(i):
        a, b = keys[max(i - 1, 0)], keys[min(i + 1, n - 1)]
        return (b[1] - a[1]) / (b[0] - a[0])
    for i in range(n - 1):
        (t0, v0), (t1, v1) = keys[i], keys[i + 1]
        if t <= t1:
            h = t1 - t0; u = (t - t0) / h
            return ((2*u**3 - 3*u**2 + 1) * v0 + (u**3 - 2*u**2 + u) * h * slope(i) + (-2*u**3 + 3*u**2) * v1 + (u**3 - u**2) * h * slope(i + 1))
