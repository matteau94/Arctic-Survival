"""Model, texture and skin the Artic-Survival human (an adult arctic survivor) on the shared 'HumanRig'.

    blender -b --python human_build.py      (writes Human_Rigged.blend + textures/Human_*.png)
    HUMAN_STAGE=geo  -> geometry + weights only (preview material, no bakes; for fast iteration)

@@DOC@@
"""
import bpy, bmesh, math, os, sys, time
import numpy as np
from mathutils import Vector as V, Matrix
from mathutils.kdtree import KDTree

DIR = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
sys.path.insert(0, DIR)
import human_rig

OUT = os.path.join(DIR, "Human_Rigged.blend")
TEX = os.path.join(DIR, "textures")
STAGE = os.environ.get("HUMAN_STAGE", "full")
RES = int(os.environ.get("HUMAN_RES", "4096"))
T0 = time.time()


def log(*a):
    print(f"[human {time.time() - T0:6.1f}s]", *a, flush=True)


# part ids (point attribute 'part'); asymmetric parts get their own (non-mirrored) UV islands
(SKIN, EYE, MOUTH, TEETH, HAIR, BEANIE, GOGGLE, LENS, PARKA, FUR, HOOD, SCARF, GLOVE, TROUSERS, GAITER,
 BOOT, SOLE, BELT, METAL, SHEATH, KNIFE, POUCH, TOGGLE, CORD, LASH) = range(25)
ASYM = {SHEATH, KNIFE, POUCH}

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
BONES = {b["name"]: b for b in human_rig.bones()}


def bh(n):
    return np.array(BONES[n]["head"], float)


def bt(n):
    return np.array(BONES[n]["tail"], float)


# ======================================================================= numeric toolkit
def A(x):
    return np.asarray(x, dtype=np.float64)


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, dtype=float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def g(x, c, w):
    return np.exp(-((x - c) / w) ** 2)


def nrm(v):
    v = np.asarray(v, float)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def hermite(keys, t):
    """Smooth interpolation through (t, value) keys (finite-difference tangents)."""
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
            return ((2*u**3 - 3*u**2 + 1) * v0 + (u**3 - 2*u**2 + u) * h * slope(i)
                    + (-2*u**3 + 3*u**2) * v1 + (u**3 - u**2) * h * slope(i + 1))


def hermite_np(keys, x, n=1500):
    xs = np.linspace(keys[0][0], keys[-1][0], n)
    return np.interp(x, xs, [hermite(keys, v) for v in xs])


def ki(keys, x):
    return np.interp(x, [k[0] for k in keys], [k[1] for k in keys])


def sd_ell(P, c, r):
    q = (P - A(c)) / A(r)
    k0 = np.linalg.norm(q, axis=-1)
    k1 = np.linalg.norm(q / A(r), axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def sd_sph(P, c, r):
    return np.linalg.norm(P - A(c), axis=-1) - r


def sd_cap(P, a, b, ra, rb=None):
    rb = ra if rb is None else rb
    a, b = A(a), A(b)
    pa, ba = P - a, b - a
    h = np.clip((pa @ ba) / (ba @ ba), 0.0, 1.0)
    return np.linalg.norm(pa - h[..., None] * ba, axis=-1) - (ra + (rb - ra) * h)


def sd_rbox(P, c, h, r):
    q = np.abs(P - A(c)) - A(h)
    return np.linalg.norm(np.maximum(q, 0.0), axis=-1) + np.minimum(np.max(q, axis=-1), 0.0) - r


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def warp(keys, lo, hi):
    """Grid positions from lo to hi whose spacing follows keys [(x, spacing)]."""
    xs = np.linspace(lo, hi, 20000)
    inv = 1.0 / ki(keys, xs)
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (inv[1:] + inv[:-1]) * np.diff(xs))])
    n = max(2, int(round(cum[-1])))
    return np.interp(np.linspace(0, cum[-1], n + 1), cum, xs)


def raycast(O, D, F, t0, t1, n=64, bis=18, chunk=30000):
    """Outermost crossing of the field F = 0 along O + t D, t in [t0, t1], searched from the outside in."""
    O = np.broadcast_to(O, D.shape).astype(np.float64)
    out = np.empty(len(D))
    ts = np.linspace(t1, t0, n)
    for c0 in range(0, len(D), chunk):
        o, d = O[c0:c0 + chunk], D[c0:c0 + chunk]
        m = len(d)
        P = o[:, None, :] + d[:, None, :] * ts[None, :, None]
        f = F(P.reshape(-1, 3)).reshape(m, n)
        inside = f < 0
        first = np.where(inside.any(axis=1), np.maximum(np.argmax(inside, axis=1), 1), n - 1)
        hi, lo = ts[first - 1].copy(), ts[first].copy()
        for _ in range(bis):
            mid = 0.5 * (hi + lo)
            ins = F(o + d * mid[:, None]) < 0
            lo = np.where(ins, mid, lo)
            hi = np.where(ins, hi, mid)
        out[c0:c0 + chunk] = 0.5 * (hi + lo)
    return out


def grad(F, P, h=2e-4):
    G = np.stack([F(P + [h, 0, 0]) - F(P - [h, 0, 0]), F(P + [0, h, 0]) - F(P - [0, h, 0]),
                  F(P + [0, 0, h]) - F(P - [0, 0, h])], -1)
    return nrm(G)


def vnoise(P, scale, seed=0):
    """Cheap smooth 3D value noise in [-1, 1] (sum of randomly oriented sines)."""
    rng = np.random.default_rng(seed)
    out = np.zeros(len(P))
    for k in range(6):
        d = nrm(rng.normal(size=3))
        f = scale * (1.0 + 0.6 * k) * rng.uniform(0.8, 1.25)
        out += np.sin(P @ d * f * 2 * np.pi + rng.uniform(0, 6.3)) / (1 + 0.5 * k)
    return out / 2.4


# ======================================================================= part registry
PARTS = []


class Part:
    def __init__(self, name, V_, F_, pid, sym="sym", seams=(), attrs=None, weights=None):
        self.name, self.V, self.F, self.sym = name, np.asarray(V_, float), [tuple(f) for f in F_], sym
        self.pid = np.full(len(self.V), float(pid)) if np.isscalar(pid) else np.asarray(pid, float)
        self.seams = list(seams)
        self.attrs = attrs or {}
        self.weights = weights            # dict bone -> array, or None (computed later from position)


def add_part(*a, **k):
    p = Part(*a, **k)
    PARTS.append(p)
    return p


def orient_out(V_, F_, center=None, axis_fn=None):
    """Flip all faces if most of them point toward the centre (parts are built with one consistent winding)."""
    Vn = np.asarray(V_)
    c = Vn.mean(0) if center is None else A(center)
    s = 0.0
    for f in F_[::max(1, len(F_) // 4000)]:
        p = Vn[list(f)]
        n_ = np.cross(p[1] - p[0], p[-1] - p[0])
        ref = (p.mean(0) - (axis_fn(p.mean(0)) if axis_fn else c))
        s += np.sign(n_ @ ref)
    return [tuple(reversed(f)) for f in F_] if s < 0 else [tuple(f) for f in F_]


def grid_faces(M, N, closed=True, off=0):
    F_ = []
    for i in range(M - 1):
        for j in range(N if closed else N - 1):
            j2 = (j + 1) % N
            F_.append((off + i * N + j, off + i * N + j2, off + (i + 1) * N + j2, off + (i + 1) * N + j))
    return F_


def loft(rings, closed=True, cap0=None, cap1=None):
    """Quad loft through rings (M, N, 3); optional pole caps. Returns V, F."""
    R = np.asarray(rings, float)
    M, N = R.shape[:2]
    V_ = list(R.reshape(-1, 3))
    F_ = grid_faces(M, N, closed)
    if cap0 is not None:
        V_.append(A(cap0)); p = len(V_) - 1
        F_ += [(p, (j + 1) % N, j) for j in range(N)]
    if cap1 is not None:
        V_.append(A(cap1)); p = len(V_) - 1; a = (M - 1) * N
        F_ += [(p, a + j, a + (j + 1) % N) for j in range(N)]
    return np.array(V_), F_


def seam_column(M, N, j, off=0):
    return [(off + i * N + j, off + (i + 1) * N + j) for i in range(M - 1)]


def frames(path, hint):
    """Parallel-transport frames along a polyline: tangent T, normal N (starting near `hint`), binormal B."""
    path = np.asarray(path, float)
    T = np.gradient(path, axis=0)
    T = nrm(T)
    N_ = np.zeros_like(path); B_ = np.zeros_like(path)
    n0 = A(hint) - T[0] * (A(hint) @ T[0])
    N_[0] = nrm(n0)
    for i in range(1, len(path)):
        n_ = N_[i - 1] - T[i] * (N_[i - 1] @ T[i])
        N_[i] = nrm(n_)
    B_ = np.cross(T, N_)
    return T, N_, B_


def resample(pts, n):
    pts = np.asarray(pts, float)
    d = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    s = np.linspace(0, d[-1], n)
    return np.stack([np.interp(s, d, pts[:, k]) for k in range(3)], -1), s


def catmull(pts, per=12):
    pts = np.asarray(pts, float)
    full = np.concatenate([[2 * pts[0] - pts[1]], pts, [2 * pts[-1] - pts[-2]]])
    out = []
    for i in range(1, len(full) - 2):
        p0, p1, p2, p3 = full[i - 1], full[i], full[i + 1], full[i + 2]
        for t in np.linspace(0, 1, per, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return np.array(out)


def mirror_part(p, name):
    """Mirror a left-side part to the right side (x -> -x), bone names .L -> .R."""
    Vm = p.V * [-1, 1, 1]
    Fm = [tuple(reversed(f)) for f in p.F]
    w = None
    if p.weights is not None:
        w = {(k[:-2] + ".R" if k.endswith(".L") else k): v.copy() for k, v in p.weights.items()}
    q = Part(name, Vm, Fm, 0, sym="pair", seams=p.seams, attrs={k: v.copy() for k, v in p.attrs.items()}, weights=w)
    q.pid = p.pid.copy()
    p.sym = "pair"
    PARTS.append(q)
    return q


# ======================================================================= 1. head
# The skin of the head is a star-shaped field around C: horizontal landmark contours (bare skull + soft
# tissue, no nose / lips / eyes) interpolated into a radial table, plus local facial features as radial
# offsets.  A spherical ray grid (dense at the eyes, nose and mouth) finds the surface.
EYEC = A(BONES["eye.L"]["head"]); RE = 0.0120; LID = 0.0016
C = A((0.0, -0.004, 1.652))
Y_AX = -0.005
SLICES = {
    1.440: [(0, -0.056), (0.040, -0.043), (0.058, -0.004), (0.052, 0.040), (0.030, 0.060), (0, 0.066)],
    1.500: [(0, -0.055), (0.040, -0.043), (0.057, -0.004), (0.052, 0.040), (0.030, 0.058), (0, 0.064)],
    1.528: [(0, -0.060), (0.040, -0.046), (0.057, -0.004), (0.052, 0.040), (0.030, 0.059), (0, 0.065)],
    1.540: [(0, -0.082), (0.020, -0.078), (0.036, -0.062), (0.050, -0.032), (0.057, -0.002), (0.052, 0.040), (0.030, 0.061), (0, 0.067)],
    1.548: [(0, -0.094), (0.013, -0.091), (0.027, -0.082), (0.042, -0.064), (0.055, -0.034), (0.060, -0.004), (0.054, 0.038), (0.031, 0.062), (0, 0.068)],
    1.556: [(0, -0.0995), (0.013, -0.097), (0.026, -0.089), (0.041, -0.073), (0.053, -0.046), (0.060, -0.016), (0.062, 0.006), (0.055, 0.036), (0.032, 0.063), (0, 0.069)],
    1.578: [(0, -0.0935), (0.014, -0.0925), (0.027, -0.086), (0.042, -0.072), (0.054, -0.048), (0.061, -0.016), (0.0630, 0.006), (0.057, 0.032), (0.036, 0.063), (0, 0.071)],
    1.600: [(0, -0.0968), (0.012, -0.0955), (0.025, -0.090), (0.038, -0.080), (0.051, -0.062), (0.060, -0.034), (0.065, -0.006), (0.064, 0.020), (0.057, 0.046), (0.036, 0.071), (0, 0.078)],
    1.620: [(0, -0.0998), (0.014, -0.0975), (0.027, -0.0918), (0.041, -0.0835), (0.055, -0.066), (0.065, -0.039), (0.069, -0.010), (0.068, 0.020), (0.063, 0.051), (0.041, 0.081), (0, 0.089)],
    1.645: [(0, -0.0975), (0.014, -0.0955), (0.028, -0.089), (0.042, -0.081), (0.055, -0.067), (0.066, -0.043), (0.071, -0.015), (0.072, 0.020), (0.067, 0.056), (0.046, 0.086), (0, 0.095)],
    1.667: [(0, -0.0965), (0.012, -0.0935), (0.020, -0.085), (0.032, -0.081), (0.046, -0.077), (0.057, -0.063), (0.066, -0.043), (0.072, -0.015), (0.074, 0.020), (0.070, 0.056), (0.049, 0.088), (0, 0.098)],
    1.690: [(0, -0.0975), (0.015, -0.095), (0.030, -0.089), (0.045, -0.083), (0.057, -0.070), (0.067, -0.048), (0.073, -0.018), (0.0755, 0.020), (0.072, 0.058), (0.050, 0.090), (0, 0.100)],
    1.702: [(0, -0.1003), (0.015, -0.0990), (0.030, -0.0950), (0.044, -0.0880), (0.056, -0.0750), (0.066, -0.054), (0.073, -0.025), (0.0765, 0.015), (0.0735, 0.055), (0.052, 0.090), (0, 0.100)],
    1.725: [(0, -0.0970), (0.020, -0.0950), (0.040, -0.0870), (0.056, -0.0720), (0.068, -0.050), (0.075, -0.020), (0.077, 0.015), (0.074, 0.055), (0.052, 0.089), (0, 0.099)],
}
Z_TOP_REF, Z_TOP = 1.725, 1.790
NTH = 721
THS = np.linspace(0, np.pi, NTH)


def contour_r(pts):
    """Polar radius (about (0, Y_AX)) of a smooth closed contour through the landmarks, sampled at THS."""
    pts = np.array(pts, float)
    full = np.concatenate([(pts * [-1, 1])[::-1][:-1], pts, (pts * [-1, 1])[::-1][1:]])
    dense = []
    for i in range(1, len(full) - 2):
        p0, p1, p2, p3 = full[i - 1], full[i], full[i + 1], full[i + 2]
        for t in np.linspace(0, 1, 40, endpoint=False):
            t2, t3 = t * t, t * t * t
            dense.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    dense = np.array(dense)
    th = np.arctan2(dense[:, 0], -(dense[:, 1] - Y_AX))
    r = np.hypot(dense[:, 0], dense[:, 1] - Y_AX)
    sel = th >= -1e-6
    o = np.argsort(th[sel])
    return np.interp(THS, th[sel][o], r[sel][o])


_ZS = sorted(SLICES)
_RS = np.array([contour_r(SLICES[z]) for z in _ZS])
ZT = np.arange(1.40, Z_TOP + 0.0005, 0.0005)
RT = np.empty((len(ZT), NTH))
for _j in range(NTH):
    RT[:, _j] = hermite_np(list(zip(_ZS, _RS[:, _j])), ZT, 700)
_ref = _RS[_ZS.index(Z_TOP_REF)]
for _i, _z in enumerate(ZT):
    if _z > Z_TOP_REF:
        RT[_i] = _ref * (np.sqrt(max(1 - ((_z - 1.700) / (Z_TOP - 1.700)) ** 2, 0))
                         / np.sqrt(1 - ((Z_TOP_REF - 1.700) / (Z_TOP - 1.700)) ** 2))


def r_base(th, z):
    zi = np.clip((z - ZT[0]) / 0.0005, 0, len(ZT) - 1.001)
    ti = np.clip(th / np.pi * (NTH - 1), 0, NTH - 1.001)
    z0 = zi.astype(int); t0 = ti.astype(int)
    fz, ft = zi - z0, ti - t0
    a = RT[z0, t0] * (1 - ft) + RT[z0, t0 + 1] * ft
    b = RT[z0 + 1, t0] * (1 - ft) + RT[z0 + 1, t0 + 1] * ft
    return a * (1 - fz) + b * fz


NOSE_P = [(1.612, 0.0), (1.6165, 0.004), (1.620, 0.0175), (1.6235, 0.0255), (1.6285, 0.0300), (1.634, 0.0292),
          (1.642, 0.0240), (1.652, 0.0175), (1.662, 0.0105), (1.671, 0.0050), (1.678, 0.0018), (1.685, 0.0)]
NOSE_W = [(1.612, 0.006), (1.620, 0.0105), (1.628, 0.0145), (1.636, 0.0125), (1.650, 0.0100), (1.668, 0.0095),
          (1.685, 0.0105), (1.692, 0.012)]
MW = 0.0240                         # half mouth width
Z_ST = 1.5982                       # stomion (design space)
ZMAP_A = [1.30, 1.553, 1.601, 1.622, 1.665, 1.90]     # actual z  <->  design z (lower face proportions)
ZMAP_D = [1.30, 1.543, 1.5982, 1.617, 1.665, 1.90]


def zdes(z):
    return np.interp(z, ZMAP_A, ZMAP_D)


def zact(zd):
    return np.interp(zd, ZMAP_D, ZMAP_A)


def ell2(ax, z, cx, cz, rx, rz):
    return ((ax - cx) / rx) ** 2 + ((z - cz) / rz) ** 2


def lip_lines(ax):
    xm = np.clip(ax / MW, 0, 1)
    zst = Z_ST - 0.0003 * xm ** 2
    up_h = 0.0090 * np.clip(1 - xm ** 1.7, 0, 1) ** 0.55 - 0.0006 * g(xm, 0, 0.10)
    lo_h = 0.0112 * np.clip(1 - xm ** 2.0, 0, 1) ** 0.60
    return zst, zst + up_h, zst - lo_h


def features(ax, z):
    """Outward offsets (m) of the facial features over the base slices, as a function of (|x|, z)."""
    D = np.zeros_like(ax)
    D += 0.0025 * g(z, 1.700, 0.007) * smoothstep(0.060, 0.030, ax) * (0.5 + 0.5 * g(ax, 0.030, 0.018))   # brow ridge
    D -= 0.0020 * g(z, 1.689, 0.004) * g(ax, 0.031, 0.011)                                                   # lid crease hollow
    D += 0.0030 * np.exp(-ell2(ax, z, 0.053, 1.645, 0.016, 0.011))                                           # cheekbone
    D -= 0.0010 * np.exp(-ell2(ax, z, 0.050, 1.622, 0.012, 0.010))                                           # sub-malar
    D += 0.0016 * np.exp(-ell2(ax, z, 0.038, 1.622, 0.013, 0.014))                                           # cheek fat
    D -= 0.0010 * g(z - 1.652 + 0.35 * (ax - 0.02), 0.0, 0.003) * smoothstep(0.012, 0.02, ax) * smoothstep(0.05, 0.035, ax)
    along = smoothstep(0.018, 0.022, ax) * smoothstep(0.040, 0.032, ax) * smoothstep(1.584, 1.596, z) * smoothstep(1.634, 1.626, z)
    side = np.clip((ax - (0.021 + (1.626 - z) / 1.9)) / 0.004, -1, 1)
    D += 0.0020 * along * smoothstep(-0.2, 1.0, side)                                                       # cheek pad
    D -= 0.0010 * along * g(side, 0.0, 0.35)                                                                 # nasolabial crease
    zst, zvb, zlb = lip_lines(ax)
    xm = np.clip(ax / MW, 0, 1.5)
    tap = np.clip(1 - xm ** 2, 0, 1)
    tu = (z - zst) / np.maximum(zvb - zst, 1e-4)
    tl = (zst - z) / np.maximum(zst - zlb, 1e-4)
    up = np.interp(tu, [-0.01, 0.0, 0.18, 0.5, 0.85, 1.0, 1.25], [0, 0.30, 0.78, 1.0, 0.88, 0.62, 0.0])
    lo = np.interp(tl, [-0.01, 0.0, 0.18, 0.5, 0.85, 1.0, 1.3], [0, 0.32, 0.82, 1.0, 0.80, 0.45, 0.0])
    D += 0.0034 * tap ** 0.6 * up * (z >= zst - 1e-5)
    D += 0.0046 * tap ** 0.6 * lo * (z < zst + 1e-5)
    D -= 0.0015 * np.exp(-ell2(ax, z, 0.0265, 1.5985, 0.004, 0.005))                                        # modiolus
    D -= 0.0006 * g(ax, 0.0, 0.0025) * smoothstep(1.607, 1.609, z) * smoothstep(1.618, 1.614, z)            # philtrum
    D += 0.0005 * g(ax, 0.0055, 0.0018) * smoothstep(1.606, 1.609, z) * smoothstep(1.618, 1.614, z)
    D += 0.0007 * g(ax, 0.0062, 0.003) * g(z, 1.6075, 0.0012)
    D += 0.0018 * np.exp(-ell2(ax, z, 0.0, 1.557, 0.017, 0.010))                                            # chin pad
    D -= 0.0005 * g(ax, 0.0, 0.003) * g(z, 1.557, 0.008)
    npz = ki(NOSE_P, z)
    nw = ki(NOSE_W, z)
    u = ax / nw
    nose = npz * np.clip(1 - u * u, 0, 1) ** 1.25
    nose += 0.0012 * g(ax, 0.0045, 0.004) * g(z, 1.630, 0.004)
    nose -= 0.0006 * g(z, 1.640, 0.003) * g(ax, 0.0, 0.006)
    ea = ell2(ax, z, 0.0125, 1.6235, 0.0080, 0.0070)
    ala = 0.0088 * np.clip(1 - ea, 0, 1) ** 0.75
    groove = 0.0016 * g(np.sqrt(ea), 1.05, 0.18) * (z > 1.618)
    nose = smax(nose, ala, 0.0025) - groove
    nose = smax(nose, 0.005 * np.clip(1 - (ax / 0.021) ** 2, 0, 1) ** 1.5 * g(z, 1.650, 0.022), 0.003)
    D += nose
    return D


def F_head(P):
    ax = np.abs(P[:, 0]); y = P[:, 1]; z = zdes(P[:, 2])
    th = np.arctan2(ax, -(y - Y_AX))
    rho = np.hypot(ax, y - Y_AX)
    front = np.clip(np.cos(th), 0.25, 1.0)
    d = rho - (r_base(th, z) + features(ax, z) / front * smoothstep(1.1, 0.8, th))
    return smin(d, sd_sph(np.stack([ax, y, P[:, 2]], -1), EYEC, RE + LID), 0.0025)


U_KEYS = [(0, 1.3), (10, 1.1), (14, 0.8), (34, 0.8), (40, 1.3), (55, 1.8), (70, 2.8), (110, 2.8), (125, 6.0), (180, 6.5)]
V_KEYS = [(-86, 6.0), (-50, 3.5), (-42, 1.4), (-36, 0.8), (-24, 0.8), (-20, 1.05), (0, 1.05), (3, 0.75), (16, 0.75), (22, 1.3),
          (35, 2.5), (50, 5.5), (86, 9.0)]
JAW_HINGE = bh("jaw")


def aperture(P, side):
    """Distances (m) to the upper / lower lid margins of eye `side` (+ = inside the palpebral fissure)."""
    e = EYEC * [side, 1, 1]
    dx = (P[:, 0] - e[0]) * side
    dz = P[:, 2] - e[2]
    dm, dl = -0.0150, 0.0142
    zm, zl = -0.0006, 0.0021
    tt = np.clip((dx - dm) / (dl - dm), 0, 1)
    z0 = zm + (zl - zm) * tt
    zu = z0 + 0.0058 * np.sin(np.pi * tt ** 0.80)
    zlo = z0 - 0.0040 * np.sin(np.pi * tt ** 1.25)
    su, sl = zu - dz, dz - zlo
    s = np.minimum(np.minimum(su, sl), np.minimum(dx - dm, dl - dx) * 0.6)
    front = (P[:, 1] - e[1]) < -0.004
    return np.where(front, s, -1.0), su, sl, dz > z0, front, dx


def build_head():
    uh = warp(U_KEYS, 0.0, 180.0)
    us = np.concatenate([uh[:-1], [180.0], -uh[1:-1][::-1]])
    vs = warp(V_KEYS, -86.0, 86.0)
    NU, NV = len(us), len(vs)
    uu, vv = np.meshgrid(np.radians(us), np.radians(vs))
    D = np.stack([np.sin(uu) * np.cos(vv), -np.cos(uu) * np.cos(vv), np.sin(vv)], -1).reshape(-1, 3)
    P = C + D * raycast(C, D, F_head, 0.02, 0.22, n=100)[:, None]
    n0 = len(P)
    wlu, wll, lidm = np.zeros(n0), np.zeros(n0), np.zeros(n0)
    # ---- eyelids: margin fold diving into the eyeball, pretarsal roll, upper-lid crease
    for side in (1, -1):
        e = EYEC * [side, 1, 1]
        s, su, sl, upper, front, dx = aperture(P, side)
        dv = P - e
        r = np.linalg.norm(dv, axis=1)
        dn = dv / r[:, None]
        R_out = RE + LID
        rr = np.interp(s, [-0.0024, -0.0012, -0.0003, 0.0004, 0.0012, 0.003],
                       [R_out, RE + 0.0022, RE + 0.0018, RE + 0.0002, RE - 0.0030, RE - 0.0040])
        prox = smoothstep(0.0035, 0.0010, np.abs(r - R_out))
        w = np.where(s > 0, 1.0, smoothstep(-0.0024, -0.0012, s) * prox)
        newr = r * (1 - w) + rr * w
        cz, cl = -su, -sl
        nearu = front & upper & (s < 0) & (np.abs(dx) < 0.020)
        crease = (-0.0009 * g(cz, 0.0058, 0.0012) + 0.0005 * g(cz, 0.0082, 0.0020) + 0.0002 * g(cz, 0.0022, 0.0012))
        crease *= smoothstep(0.019, 0.012, np.abs(dx + 0.001))
        nearl = front & ~upper & (s < 0) & (np.abs(dx) < 0.020)
        lower = (0.00025 * g(cl, 0.0020, 0.0012) - 0.0004 * g(cl, 0.0065, 0.0020)) * smoothstep(0.018, 0.010, np.abs(dx))
        newr = newr + np.where(nearu, crease, 0.0) + np.where(nearl, lower, 0.0)
        sel = (s > -0.012) & front & (r < 0.03)
        P = np.where(sel[:, None], e + dn * newr[:, None], P)
        wu = np.where(s > 0, 1.0, smoothstep(0.0095, 0.0015, cz)) * upper * front
        wlo = np.where(s > 0, 1.0, smoothstep(0.0075, 0.0012, cl)) * (~upper) * front
        wu *= smoothstep(0.022, 0.016, np.abs(dx)); wlo *= smoothstep(0.020, 0.014, np.abs(dx))
        mine = (np.sign(P[:, 0]) == side) & (r < 0.03)
        wlu = np.where(mine, wu, wlu)
        wll = np.where(mine, wlo, wll)
        lidm = np.where(mine & (s > -0.0006), 1.0, lidm)          # lid margin / dived (painted wet pink)
    # ---- nostrils: dive the underside of the nose up into the nasal vestibule
    Nn = grad(F_head, P)
    for side in (1, -1):
        c = A((0.0080 * side, -0.1110, zact(1.6225)))
        dxy = P[:, :2] - c[:2]
        ang = np.radians(-28 * side)
        a_ = dxy[:, 0] * np.cos(ang) - dxy[:, 1] * np.sin(ang)
        b_ = dxy[:, 0] * np.sin(ang) + dxy[:, 1] * np.cos(ang)
        q = np.sqrt((a_ / 0.0030) ** 2 + (b_ / 0.0052) ** 2)
        under = (Nn[:, 2] < -0.55) & (P[:, 2] < c[2] + 0.006) & (P[:, 2] > c[2] - 0.008) & (np.abs(P[:, 0]) < 0.02) & (P[:, 1] < -0.100)
        k_ = smoothstep(1.15, 0.55, q) * under
        P[:, 2] += 0.0050 * k_
        P[:, 0] -= 0.0012 * side * k_
    # ---- lips: split row along the stomion, snapped to the lip line and dived into the mouth
    G = P.reshape(NV, NU, 3)
    zst_c = float(zact(Z_ST))
    vst = np.degrees(np.arctan2(zst_c - C[2], -(-0.100 - C[1])))
    jm = int(np.argmin(np.abs(vs - vst)))
    row = G[jm]
    Dn = row - C
    Dn[:, 2] = zact(lip_lines(np.abs(row[:, 0]))[0]) - C[2]
    Dn = nrm(Dn)
    newrow = C + Dn * raycast(C, Dn, F_head, 0.02, 0.22, n=100)[:, None]
    inside = (np.abs(newrow[:, 0]) < MW - 0.0006) & (newrow[:, 1] < -0.06)
    corner = (np.abs(newrow[:, 0]) < MW + 0.0025) & (newrow[:, 1] < -0.06)
    G[jm] = np.where(corner[:, None], newrow, G[jm])
    split_cols = np.nonzero(inside)[0]
    xm = np.clip(np.abs(G[jm, split_cols, 0]) / MW, 0, 1)
    depth = 0.0072 * np.sqrt(np.clip(1 - xm ** 2, 0, 1))
    G[jm, split_cols] -= nrm(G[jm, split_cols] - C) * depth[:, None]
    P = G.reshape(-1, 3)
    verts = list(P)
    lower_copy = {}
    for j in split_cols:
        lower_copy[j] = len(verts)
        verts.append(P[jm * NU + j].copy())
    F_ = []
    for i in range(NV - 1):
        for j in range(NU):
            j2 = (j + 1) % NU
            a, b = i * NU + j, i * NU + j2
            c_, d_ = (i + 1) * NU + j2, (i + 1) * NU + j
            if i + 1 == jm:
                c_ = lower_copy.get(j2, c_)
                d_ = lower_copy.get(j, d_)
            F_.append((a, d_, c_, b))
    verts.append(C + A((0, 0, -1)) * raycast(C, A([[0, 0, -1.0]]), F_head, 0.02, 0.3)[0]); pb = len(verts) - 1
    verts.append(C + A((0, 0, 1)) * raycast(C, A([[0, 0, 1.0]]), F_head, 0.02, 0.3)[0]); pt = len(verts) - 1
    for j in range(NU):
        j2 = (j + 1) % NU
        F_.append((pb, j2, j))
        F_.append((pt, (NV - 1) * NU + j, (NV - 1) * NU + j2))
    V_ = np.array(verts)
    n = len(V_)
    ext = lambda a: np.concatenate([a, np.zeros(n - len(a))])
    wlu, wll, lidm = ext(wlu), ext(wll), ext(lidm)
    # jaw weight: lower lip, chin and lower cheek, blending toward the hinge and the neck
    x, y, z = np.abs(V_[:, 0]), V_[:, 1], V_[:, 2]
    zl = zact(lip_lines(np.minimum(x, MW))[0])
    t_ = np.clip((x - MW) / (0.060 - MW), 0, 1)
    zb = np.where(x < MW, zl, zst_c + 0.0015 + t_ * (1.628 - zst_c))
    band = np.where(x < MW, 0.0012, 0.004 + 0.012 * t_)
    wj = smoothstep(zb + band, zb - band, z) * smoothstep(0.035, -0.005, y) * smoothstep(1.525, 1.575, z)
    wj = np.clip(wj, 0, 1)
    lipm = np.zeros(n)
    for j in split_cols:
        wj[jm * NU + j] = 0.0
        wj[lower_copy[j]] = 1.0
        wlu[lower_copy[j]] = wll[lower_copy[j]] = 0.0
    seams = [(k * NU + NU // 2, (k + 1) * NU + NU // 2) for k in range(NV - 1)]   # back-of-head midline
    global HEAD_GRID
    HEAD_GRID = (NU, NV, jm, set(int(c) for c in split_cols))
    return V_, F_, dict(wjaw=wj, wlu=wlu, wll=wll, lidm=lidm), seams


log("head field ready")
Vh, Fh, HW, hseams = build_head()
head_part = add_part("head", Vh, Fh, SKIN, seams=hseams, attrs=HW)
log("head skin", len(Vh))


# ----------------------------------------------------------------------- eyes
def build_eye(side):
    e = EYEC * [side, 1, 1]
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=24, radius=RE)
    bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(math.radians(90), 3, 'X'))
    for v in bm.verts:
        c = -v.co.y / RE
        if c > 0.80:                                                # corneal bulge
            v.co.y -= 0.0013 * ((c - 0.80) / 0.2) ** 0.7
    V_ = np.array([tuple(v.co) for v in bm.verts]) + e
    F_ = [tuple(v.index for v in f.verts) for f in bm.faces]
    seams = [(ed.verts[0].index, ed.verts[1].index) for ed in bm.edges
             if abs(ed.verts[0].co.x) < 1e-6 and abs(ed.verts[1].co.x) < 1e-6 and ed.verts[0].co.z > -1e-6 and ed.verts[1].co.z > -1e-6
             and ed.verts[0].co.y > -0.004]
    bm.free()
    return V_, orient_out(V_, F_, e), seams


Ve, Fe, se = build_eye(1)
eyeL = add_part("eye.L", Ve, Fe, EYE, seams=se, weights={"eye.L": np.ones(len(Ve))})
mirror_part(eyeL, "eye.R")


# ----------------------------------------------------------------------- mouth interior + teeth
# A tube running back from just inside the lips to the throat: upper half = gums / vaulted palate
# (head), lower half = gums / floor / tongue (jaw).  Its front ring is buried in the lip flesh, so with
# the jaw closed nothing shows; the dived lip edges sit inside its opening.
def build_mouth():
    NS, NA = 16, 28
    zc0 = zact(Z_ST) + 0.0002
    rings = []
    wj, depth = [], []
    for i in range(NS):
        s = i / (NS - 1)
        y0 = -0.0945 + 0.0545 * s ** 1.1
        w = 0.0235 + 0.009 * s ** 0.7 - 0.006 * s ** 3
        h = 0.0085 + 0.004 * smoothstep(0, 0.35, s) + 0.001 * s
        ring = []
        for k in range(NA):
            th = 2 * np.pi * k / NA
            cz, sz = np.cos(th), np.sin(th)
            x = w * sz
            z = zc0 + h * cz
            if cz > 0:
                z += 0.0065 * cz ** 3 * float(smoothstep(0.1, 0.35, s) * (1 - smoothstep(0.85, 1.0, s)))     # palate vault
            else:
                z += 0.0085 * (-cz) ** 2.5 * float(smoothstep(0.12, 0.45, s) * (1 - smoothstep(0.9, 1.0, s)))  # tongue
            yy = y0 + 0.013 * (x / 0.0235) ** 2 * (1 - s) ** 1.5
            ring.append((x, yy, z))
            wj.append(float(smoothstep(0.25, -0.25, cz)) * (1 - 0.5 * float(smoothstep(0.7, 1.0, s))))
            depth.append(s)
        rings.append(ring)
    V_, F_ = loft(rings, cap1=(0, -0.040, zc0))
    wj.append(0.3); depth.append(1.0)
    F_ = orient_out(V_, F_, (0, -0.07, zc0))
    F_ = [tuple(reversed(f)) for f in F_]                     # we look at it from the inside
    return V_, F_, np.array(wj), np.array(depth), seam_column(NS, NA, 0)


Vm_, Fm_, wjm, dm_, sm_ = build_mouth()
add_part("mouth", Vm_, Fm_, MOUTH, seams=sm_, attrs=dict(wjaw=wjm, mdepth=dm_))

TEETH_UP = [  # x, y (labial face centre), mesiodistal width, crown height, thickness, edge z offset
    (0.0045, -0.0880, 0.0085, 0.0100, 0.0068, 0.0000), (0.0125, -0.0862, 0.0066, 0.0090, 0.0060, 0.0006),
    (0.0190, -0.0825, 0.0076, 0.0098, 0.0080, 0.0002), (0.0226, -0.0770, 0.0070, 0.0082, 0.0090, 0.0010),
    (0.0246, -0.0702, 0.0068, 0.0075, 0.0092, 0.0014), (0.0262, -0.0615, 0.0100, 0.0068, 0.0100, 0.0018)]
TEETH_LO = [
    (0.0028, -0.0858, 0.0054, 0.0090, 0.0058, 0.0000), (0.0085, -0.0848, 0.0060, 0.0090, 0.0060, 0.0004),
    (0.0146, -0.0818, 0.0070, 0.0095, 0.0075, 0.0004), (0.0200, -0.0768, 0.0070, 0.0080, 0.0085, 0.0012),
    (0.0228, -0.0698, 0.0070, 0.0075, 0.0090, 0.0016), (0.0250, -0.0612, 0.0105, 0.0068, 0.0100, 0.0020)]


def build_tooth(x, y, wd, ht, th, eoff, upper):
    """Rounded-box tooth: labial face toward the lips, crown tapering to the incisal edge / cusps."""
    zst_c = float(zact(Z_ST))
    sg = 1 if upper else -1
    edge = zst_c + sg * (0.0003 + eoff)
    root = edge + sg * (ht + 0.004)
    ctr = A((x, y + th * 0.5, 0))
    tang = nrm(A((1.0, 2.2 * x / 0.026 * 0.9, 0)))         # along the arch
    out_ = nrm(A((tang[1], -tang[0], 0)))                    # labial (toward the lips)
    if out_[1] > 0:
        out_ = -out_
    rings = []
    NR = 12
    for t in (0.0, 0.25, 0.55, 0.8, 0.93, 1.0):
        z = root + (edge - root) * t
        taper = 1.0 - 0.18 * max(0.0, (t - 0.55) / 0.45) ** 1.5
        thk = th * (0.75 + 0.25 * np.sin(np.pi * min(t * 1.2, 1.0))) * (1 - 0.35 * max(0.0, (t - 0.6) / 0.4))
        ring = []
        for k in range(NR):
            a = 2 * np.pi * k / NR
            ca, sa = np.cos(a), np.sin(a)
            px = 0.5 * wd * taper * np.sign(ca) * abs(ca) ** 0.45
            py = 0.5 * thk * np.sign(sa) * abs(sa) ** 0.6
            ring.append(ctr + tang * px - out_ * py + A((0, 0, z)))
        rings.append(ring)
    V_, F_ = loft(rings, cap1=A((ctr[0], ctr[1], edge + sg * 0.0003)))
    return V_, orient_out(V_, F_, A((ctr[0], ctr[1], (root + edge) / 2)))


for upper, table in ((True, TEETH_UP), (False, TEETH_LO)):
    for sd in (1, -1):
        for (x, y, wd, ht, th, eo) in table:
            Vt, Ft = build_tooth(x, y, wd, ht, th, eo, upper)
            if sd < 0:
                Vt = Vt * [-1, 1, 1]; Ft = [tuple(reversed(f)) for f in Ft]
            add_part("tooth", Vt, Ft, TEETH if upper else TEETH + 0.5, attrs=dict(wjaw=np.full(len(Vt), 0.0 if upper else 1.0)))


# ----------------------------------------------------------------------- ears
# Polar-grid relief (helix rim, scapha, antihelix, concha bowl, tragus, lobe) whose rim rolls over
# into a smooth back surface that sinks into the head.
def build_ear():
    O = A((0.0745, 0.010, 1.658))
    n_ = nrm(A((1.0, -0.20, 0.02)))
    up = nrm(A((0, 0.27, 1.0)) - n_ * (A((0, 0.27, 1.0)) @ n_))
    fw = np.cross(up, n_)                                   # points forward (-y) for the left ear
    if fw[1] > 0:
        fw = -fw
    NF, NRF, NRB = 44, 13, 6
    PH = np.linspace(0, 2 * np.pi, NF, endpoint=False)      # 0 = front (toward the face), pi/2 = up
    Rk = [(0, 0.011), (0.6, 0.020), (1.2, 0.030), (1.6, 0.0335), (2.1, 0.030), (2.7, 0.022), (3.2, 0.019),
          (3.8, 0.021), (4.4, 0.028), (4.75, 0.030), (5.3, 0.020), (5.9, 0.012), (6.2832, 0.011)]
    R = hermite_np(Rk, PH)
    rows = []
    lobe = g(PH, 4.7, 0.55)
    tragus = g(np.angle(np.exp(1j * PH)), 0.0, 0.35)
    for i in range(NRF):
        rho = i / (NRF - 1)
        # relief: canal / concha bowl, antihelix ridge, scapha groove, rolled helix rim
        h = (-0.0060 * g(rho, 0.0, 0.30) + 0.0040 * g(rho, 0.60, 0.13) + 0.0012 * g(rho, 0.80, 0.07)
             + 0.0055 * g(rho, 0.93, 0.07))
        h = h * (1 - lobe) + (0.0035 * g(rho, 0.55, 0.35)) * lobe + 0.0040 * tragus * g(rho, 0.75, 0.15)
        a = R * rho * np.cos(PH)
        b = R * rho * np.sin(PH)
        prot = np.maximum(0.0, -a) * 0.42 * (0.4 + 0.6 * rho)          # the back half stands out from the head
        roll = -0.0022 * g(rho, 1.0, 0.05) * (1 - lobe)                  # rim curls forward
        pts = O + a[:, None] * fw + b[:, None] * up + (h + prot)[:, None] * n_ + roll[:, None] * (np.cos(PH)[:, None] * fw + np.sin(PH)[:, None] * up)
        rows.append(pts)
    for k in range(1, NRB + 1):
        q = k / NRB
        a = R * np.cos(PH) * (1 - 0.40 * q)
        b = R * np.sin(PH) * (1 - 0.40 * q)
        prot = np.maximum(0.0, -a) * 0.42 * (1 - q) ** 1.2
        pts = O + a[:, None] * fw + b[:, None] * up + (prot + 0.0015 * np.sin(np.pi * q) - 0.009 * q ** 1.5)[:, None] * n_
        rows.append(pts)
    V_, F_ = loft(rows, cap0=O - 0.008 * n_)
    return V_, orient_out(V_, F_, O - 0.02 * n_), seam_column(NRF + NRB, NF, NF // 2)


Ve_, Fe_, se_ = build_ear()
earL = add_part("ear.L", Ve_, Fe_, SKIN, seams=se_, weights={"head": np.ones(len(Ve_))})
earL.attrs["ear"] = np.ones(len(Ve_))
mirror_part(earL, "ear.R")
log("head parts done")

# ======================================================================= 2. parka
# Torso shell: a smooth union of chest / belly / hips / shoulder / upper-back / collar volumes found
# with a ray grid (horizontal rays up the body, rays tilting up over the shoulders, horizontal rays
# again around the standing collar).  Quilted baffles, the drawcord cinch, the storm-flap placket,
# the bellows pockets, the hem band and fabric folds are radial offsets on top of it.
S_L, E_L, W_L = bh("upper_arm.L"), bh("forearm.L"), bh("hand.L")
ARM_D = nrm(W_L - S_L)
Z_HEM, Z_CORD = 0.800, 1.075


def F_parka(P):
    Q = P.copy(); Q[:, 0] = np.abs(Q[:, 0])
    d = sd_ell(Q, (0, 0.000, 1.300), (0.188, 0.134, 0.230))
    d = smin(d, sd_ell(Q, (0, -0.004, 1.080), (0.172, 0.130, 0.210)), 0.06)
    d = smin(d, sd_ell(Q, (0, 0.006, 0.905), (0.186, 0.137, 0.190)), 0.06)
    d = smin(d, sd_cap(Q, (0.05, 0.018, 1.452), (0.172, 0.018, 1.438), 0.062), 0.05)
    d = smin(d, sd_ell(Q, (0, 0.045, 1.40), (0.13, 0.10, 0.10)), 0.04)
    d = smin(d, sd_cap(Q, (0, 0.012, 1.40), (0, 0.006, 1.575), 0.079), 0.03)
    return d


def pocket_box(x, z, x0, x1, z0, z1, soft=0.004):
    return (smoothstep(x0 - soft, x0 + soft, x) * smoothstep(x1 + soft, x1 - soft, x)
            * smoothstep(z0 - soft, z0 + soft, z) * smoothstep(z1 + soft, z1 - soft, z))


def build_parka_torso():
    th_h = warp([(0, 2.8), (40, 3.2), (100, 4.2), (180, 4.6)], 0, 180)
    TH = np.radians(np.concatenate([th_h[:-1], [180.0], -th_h[1:-1][::-1]]))
    NTc = len(TH)
    zs = np.concatenate([[Z_HEM], np.arange(Z_HEM + 0.008, 1.395, 0.0105)])
    betas = np.radians(np.arange(4, 55, 3.2))
    zc = np.arange(1.51, 1.572, 0.0105)
    O, Dr = [], []
    for z in zs:
        for t in TH:
            O.append((0, 0.008, z)); Dr.append((np.sin(t), -np.cos(t), 0))
    for b in betas:
        for t in TH:
            O.append((0, 0.012, 1.40)); Dr.append((np.sin(t) * np.cos(b), -np.cos(t) * np.cos(b), np.sin(b)))
    for k, z in enumerate(zc):
        for t in TH:
            zz = 1.505 + (z - 1.505) * (0.35 + 0.65 * (0.5 - 0.5 * np.cos(t)))
            O.append((0, 0.007, zz)); Dr.append((np.sin(t), -np.cos(t), 0))
    O, Dr = A(O), A(Dr)
    P = O + Dr * raycast(O, Dr, F_parka, 0.02, 0.40, n=90)[:, None]
    M = len(zs) + len(betas) + len(zc)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    ax = np.abs(x)
    th = np.tile(TH, M)
    front = y < 0
    off = np.zeros(len(P))
    # quilted baffles (horizontal channels), not on the placket / pockets
    frac = ((z - Z_HEM) / 0.078) % 1.0
    quilt = 0.0055 * np.sin(np.pi * frac) ** 0.55 - 0.0015
    placket = front * smoothstep(0.034, 0.028, ax)
    front2 = smoothstep(-0.03, -0.08, y)
    cpock = front2 * pocket_box(ax, z, 0.048, 0.142, 1.262, 1.392, 0.005)
    hpock = front2 * pocket_box(ax, z, 0.058, 0.165, 0.838, 0.978, 0.006)
    body = (1 - placket) * (1 - cpock) * (1 - hpock) * smoothstep(Z_HEM + 0.02, Z_HEM + 0.05, z) * smoothstep(1.53, 1.49, z)
    off += quilt * body
    # drawcord cinch with gathers
    cinch = g(z, Z_CORD, 0.013)
    off += -0.011 * cinch + 0.004 * g(z, Z_CORD + 0.028, 0.014) + 0.003 * g(z, Z_CORD - 0.026, 0.012)
    off += 0.0035 * np.sin(th * 23.0 + 1.3) * g(z, Z_CORD, 0.035) * (1 - placket)
    # storm flap placket (raised, with a hard edge) and the pockets (bellows + flaps)
    off += 0.0065 * placket
    off += 0.0080 * cpock + 0.0035 * front2 * pocket_box(ax, z, 0.044, 0.146, 1.360, 1.402, 0.004)
    off += 0.0110 * hpock + 0.0040 * front2 * pocket_box(ax, z, 0.054, 0.169, 0.945, 0.984, 0.004)
    # hem band (thicker, drawcord channel)
    off += 0.0045 * smoothstep(Z_HEM + 0.045, Z_HEM + 0.030, z)
    # fabric folds: under the arms, over the lower back, soft random wrinkles
    side = smoothstep(0.12, 0.17, ax) * g(z, 1.33, 0.07)
    off += 0.0045 * side * np.sin(z * 90 + ax * 60 + np.sign(x) * 0.5)
    off += 0.0035 * (~front) * g(z, 1.14, 0.05) * np.sin(th * 14.0)
    off += 0.0030 * vnoise(P * [1, 1, 0.5], 7, 3) * smoothstep(1.50, 1.45, z)
    P = P + Dr * off[:, None]
    # hem turn-up (inner lining ring) so the edge has thickness
    ring0 = P[:NTc].copy()
    inner = ring0 - Dr[:NTc] * 0.010 + A((0, 0, 0.012))
    Pall = np.concatenate([inner, P])
    # collar top: roll over and back down inside
    top = P[-NTc:]
    cdir = nrm(top - A((0, 0.007, top[0, 2])) * [0, 1, 0] - A((0, 0, 1)) * top[:, 2:3] * 0 - (top * [0, 0, 1]))
    radial = nrm((top - A((0, 0.007, 0))) * [1, 1, 0])
    roll = top + A((0, 0, 0.006)) - radial * 0.006
    inside = top - radial * 0.012 - A((0, 0, 0.004))
    Pall = np.concatenate([Pall, roll, inside])
    MM = M + 3
    V_, F_ = loft(Pall.reshape(MM, NTc, 3))
    F_ = orient_out(V_, F_, axis_fn=lambda p: A((0, 0.008, p[2])))
    attrs = dict(pock=np.concatenate([np.zeros(NTc), cpock + 2 * hpock, np.zeros(2 * NTc)]),
                 plk=np.concatenate([np.zeros(NTc), placket, np.zeros(2 * NTc)]))
    return V_, F_, attrs


Vp, Fp, ap = build_parka_torso()
parka_torso = add_part("parka", Vp, Fp, PARKA, attrs=ap)
log("parka torso", len(Vp))


def tube(path, n_around, rad_fn, hint):
    """Tube along a polyline.  rad_fn(s (M,1), th (1,N)) -> radius (M,N); th = 0 along `hint`."""
    path = np.asarray(path, float)
    T, N_, B_ = frames(path, hint)
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
    th = 2 * np.pi * np.arange(n_around) / n_around
    R = rad_fn(s[:, None], th[None, :])
    dirs = N_[:, None, :] * np.cos(th)[None, :, None] + B_[:, None, :] * np.sin(th)[None, :, None]
    rings = path[:, None, :] + dirs * R[..., None]
    return rings, s, th, (T, N_, B_)


def build_sleeve():
    start = S_L - ARM_D * 0.035 + A((0, 0, 0.004))
    end = W_L - ARM_D * 0.012
    path = catmull([start, S_L + ARM_D * 0.08, E_L, (E_L + W_L) / 2, end], 10)
    path, _ = resample(path, 46)
    L = np.linalg.norm(np.diff(path, axis=0), axis=1).sum()
    s_elb = np.linalg.norm(E_L - start)

    def rad(s, th):
        r = hermite_np([(0, 0.050), (0.045, 0.071), (0.12, 0.073), (s_elb - 0.05, 0.066), (s_elb + 0.04, 0.062),
                        (L - 0.07, 0.057), (L - 0.035, 0.055), (L, 0.056)], s)
        r = r * (1 + 0.06 * np.cos(2 * th))                                    # slightly oval section
        frac = (s / 0.072) % 1.0
        r = r + (0.0048 * np.sin(np.pi * frac) ** 0.55 - 0.0013) * smoothstep(0.04, 0.08, s) * smoothstep(L - 0.04, L - 0.07, s)
        # elbow compression folds on the inner (front) side, bunching above the cuff
        inner = np.clip(np.cos(th), 0, 1) ** 1.5
        r = r + 0.0050 * inner * g(s, s_elb, 0.05) * np.sin((s - s_elb) * 150)
        r = r + 0.0040 * g(s, L - 0.09, 0.035) * np.sin(th * 5 + s * 90)
        r = r + 0.0025 * np.sin(th * 3 + s * 31) * np.sin(s * 17)                  # soft random wrinkles
        r = r + 0.0035 * smoothstep(L - 0.03, L - 0.015, s)                        # cuff band
        return r
    rings, s, th, fr = tube(path, 36, rad, (0, -1, 0))
    # cuff turn-in
    T = fr[0][-1]
    last = rings[-1]
    inner = path[-1] + (last - path[-1]) * 0.80 - T * 0.012
    rings = np.concatenate([rings, [last + T * 0.003 - (last - path[-1]) * 0.08, inner]])
    V_, F_ = loft(rings)
    F_ = orient_out(V_, F_, axis_fn=lambda p: path[np.argmin(np.linalg.norm(path - p, axis=1))])
    return V_, F_, seam_column(len(rings), 36, 9)


Vs_, Fs_, ss_ = build_sleeve()
sleeveL = add_part("sleeve.L", Vs_, Fs_, PARKA, seams=ss_)
mirror_part(sleeveL, "sleeve.R")
log("sleeves", len(Vs_))


# ======================================================================= 3. legs: trousers, gaiters, boots
HIP_L, KNEE_L, ANK_L, BALL_L, TIP_L = bh("thigh.L"), bh("shin.L"), bh("foot.L"), bh("toe.L"), bt("toe.L")


def build_trouser_leg():
    top = HIP_L + A((0.000, 0.0, 0.030))
    path = catmull([top, HIP_L, (HIP_L + KNEE_L) / 2, KNEE_L, KNEE_L + (ANK_L - KNEE_L) * 0.45,
                    KNEE_L + (ANK_L - KNEE_L) * 0.78], 10)
    path, _ = resample(path, 52)
    L = np.linalg.norm(np.diff(path, axis=0), axis=1).sum()
    sk = np.linalg.norm(KNEE_L - top) + 0.0

    def rad(s, th):
        r = hermite_np([(0, 0.080), (0.07, 0.090), (0.20, 0.087), (0.36, 0.076), (sk - 0.03, 0.069), (sk + 0.02, 0.068),
                        (sk + 0.14, 0.066), (sk + 0.25, 0.060), (L, 0.058)], s)
        # inner thigh flatter where the legs meet, seat fuller at the back
        r = r * (1 - 0.10 * np.clip(np.sin(th), 0, 1) ** 2 * smoothstep(0.3, 0.05, s))
        r = r * (1 + 0.06 * np.clip(-np.cos(th), 0, 1) ** 2 * smoothstep(0.3, 0.0, s))
        # knee patch (front) + folds behind the knee, bunching above the gaiter, big soft wrinkles
        front = np.clip(np.cos(th), 0, 1)
        patch = smoothstep(0.55, 0.62, front) * smoothstep(sk - 0.11, sk - 0.09, s) * smoothstep(sk + 0.11, sk + 0.09, s)
        r = r + 0.0045 * patch + 0.0035 * front ** 2 * g(s, sk, 0.05)
        r = r + 0.0045 * np.clip(-np.cos(th), 0, 1) * g(s, sk, 0.04) * np.sin((s - sk) * 170)
        r = r + 0.0040 * g(s, L - 0.06, 0.04) * np.sin(th * 4 + s * 120)
        r = r + 0.0035 * np.sin(th * 2 + s * 21 + 1) * np.sin(s * 13 + th)
        return r
    rings, s, th, fr = tube(path, 34, rad, (0, -1, 0))
    V_, F_ = loft(rings)
    F_ = orient_out(V_, F_, axis_fn=lambda p: path[np.argmin(np.linalg.norm(path - p, axis=1))])
    patch = np.zeros(len(V_))
    front = np.clip(np.cos(th), 0, 1)[None, :] * np.ones((len(s), 1))
    patch[:] = (smoothstep(0.55, 0.62, front) * smoothstep(np.linalg.norm(KNEE_L - top) - 0.11, np.linalg.norm(KNEE_L - top) - 0.09, s[:, None])
                * smoothstep(np.linalg.norm(KNEE_L - top) + 0.11, np.linalg.norm(KNEE_L - top) + 0.09, s[:, None])).ravel()
    return V_, F_, seam_column(len(rings), 34, 25), patch


Vt_, Ft_, st_, kp_ = build_trouser_leg()
legL = add_part("trouser.L", Vt_, Ft_, TROUSERS, seams=st_, attrs=dict(pock=kp_ * 3))
mirror_part(legL, "trouser.R")
log("trousers", len(Vt_))


def build_gaiter():
    a = KNEE_L + (ANK_L - KNEE_L) * 0.20
    b = KNEE_L + (ANK_L - KNEE_L) * 0.84
    path, _ = resample(np.array([a, b]), 22)
    L = np.linalg.norm(b - a)

    def rad(s, th):
        r = hermite_np([(0, 0.071), (0.02, 0.074), (0.05, 0.070), (L * 0.5, 0.068), (L - 0.05, 0.070), (L, 0.076)], s)
        r = r * (1 + 0.05 * np.cos(th) ** 2)
        r = r + 0.0030 * np.sin(th * 3 + s * 60) * g(s, L * 0.6, 0.10) + 0.0035 * g(s, 0.012, 0.008)
        return r
    rings, s, th, fr = tube(path, 32, rad, (0, -1, 0))
    T = fr[0]
    rings = np.concatenate([[path[0] + (rings[0] - path[0]) * 0.86 + T[0] * 0.010], rings,
                            [path[-1] + (rings[-1] - path[-1]) * 0.9 + T[-1] * 0.004]])
    V_, F_ = loft(rings)
    F_ = orient_out(V_, F_, axis_fn=lambda p: path[np.argmin(np.linalg.norm(path - p, axis=1))])
    return V_, F_, seam_column(len(rings), 32, 16)


Vg_, Fg_, sg_ = build_gaiter()
gaiterL = add_part("gaiter.L", Vg_, Fg_, GAITER, seams=sg_)
mirror_part(gaiterL, "gaiter.R")

BOOT_X = 0.113


def F_boot(P):
    d = sd_rbox(P, (BOOT_X, -0.058, 0.057), (0.030, 0.100, 0.008), 0.022)
    d = smin(d, sd_ell(P, (BOOT_X + 0.002, -0.150, 0.058), (0.051, 0.048, 0.033)), 0.02)
    d = smin(d, sd_cap(P, (0.110, -0.045, 0.072), (0.106, 0.018, 0.120), 0.049), 0.03)
    d = smin(d, sd_cap(P, (0.106, 0.022, 0.10), (0.104, 0.020, 0.235), 0.053), 0.02)
    d = smin(d, sd_ell(P, (0.107, 0.042, 0.066), (0.046, 0.036, 0.040)), 0.02)
    d = smax(d, 0.028 - P[:, 2], 0.004)                         # flat bottom on the sole
    return d


def build_boot():
    axis = catmull([(BOOT_X, -0.190, 0.058), (BOOT_X, -0.110, 0.060), (0.110, -0.030, 0.075), (0.106, 0.018, 0.110),
                    (0.104, 0.018, 0.160), (0.104, 0.018, 0.232)], 8)
    axis, _ = resample(axis, 44)
    T, N_, B_ = frames(axis, (0, 0, 1))
    NA = 40
    th = 2 * np.pi * np.arange(NA) / NA
    O = np.repeat(axis, NA, 0)
    Dr = (N_[:, None, :] * np.cos(th)[None, :, None] + B_[:, None, :] * np.sin(th)[None, :, None]).reshape(-1, 3)
    P = O + Dr * raycast(O, Dr, F_boot, 0.0, 0.11, n=70)[:, None]
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    # stitched toe cap welt, lacing ridge + tongue on the instep, padded collar, heel counter seam
    lace = g(x - BOOT_X, 0.0, 0.016) * smoothstep(-0.08, -0.06, y) * (z > 0.07) * smoothstep(0.22, 0.20, z)
    off = 0.0030 * lace * (0.5 + 0.5 * np.sin((z + y * 0.6) * 260) ** 2)
    off += 0.0018 * g(np.hypot((y + 0.150) / 0.055, (z - 0.058) / 0.040), 1.0, 0.06)
    off += 0.0040 * g(z, 0.232, 0.010) + 0.0025 * vnoise(P, 18, 5) * smoothstep(0.08, 0.14, z)
    off -= 0.0015 * g(z, 0.036, 0.004)                                          # welt seam above the sole
    P = P + Dr * off[:, None]
    rings = P.reshape(len(axis), NA, 3)
    Tt = T[-1]
    rings = np.concatenate([rings, [axis[-1] + (rings[-1] - axis[-1]) * 0.85 + Tt * 0.004]])
    V_, F_ = loft(rings, cap0=A((BOOT_X, -0.205, 0.052)))
    F_ = orient_out(V_, F_, axis_fn=lambda p: axis[np.argmin(np.linalg.norm(axis - p, axis=1))])
    return V_, F_, seam_column(len(rings), NA, NA // 2)


Vb_, Fb_, sb_ = build_boot()
bootL = add_part("boot.L", Vb_, Fb_, BOOT, seams=sb_)
mirror_part(bootL, "boot.R")


def build_sole():
    """Thick lugged sole: rounded-rectangle sections along the foot, lug blocks on the tread."""
    ys = np.arange(0.086, -0.212, -0.0045)
    NA = 36

    def half_w(y):
        return ki(sorted([(0.086, 0.030), (0.070, 0.050), (0.040, 0.057), (0.0, 0.054), (-0.040, 0.055), (-0.090, 0.062),
                          (-0.140, 0.062), (-0.175, 0.054), (-0.198, 0.038), (-0.212, 0.014)]), y)
    rings = []
    tread = []
    for y in ys:
        w = half_w(y)
        top = 0.031 if y > -0.18 else 0.031 + (y + 0.18) * 0.25
        arch = 0.0065 * smoothstep(0.035, 0.015, y) * smoothstep(-0.075, -0.050, y)
        ring = []
        for k in range(NA):
            a = 2 * np.pi * k / NA
            ca, sa = np.cos(a), np.sin(a)
            px = w * np.sign(ca) * abs(ca) ** 0.35
            pz = 0.5 * (top + 0.0) + 0.5 * top * np.sign(sa) * abs(sa) ** 0.30
            if sa < 0:
                # lugs: chevron blocks on the tread, deeper grooves between
                lug = (np.sin((y + 0.5 * abs(px)) * 2 * np.pi / 0.022) > -0.2) & (abs(np.sin(px * 2 * np.pi / 0.030)) > 0.15)
                pz = pz + (0.0 if lug else 0.0045) * min(1.0, (-sa) ** 2 * 3) + arch
                tread.append(0.0 if lug else 1.0)
            else:
                tread.append(0.0)
            ring.append((BOOT_X + px, y, pz))
        rings.append(ring)
    V_, F_ = loft(rings, cap0=A((BOOT_X, 0.088, 0.016)), cap1=A((BOOT_X, -0.214, 0.018)))
    tread += [0.0, 0.0]
    F_ = orient_out(V_, F_, axis_fn=lambda p: A((BOOT_X, p[1], 0.016)))
    return V_, F_, seam_column(len(ys), NA, 0), np.array(tread)


Vso, Fso, sso, tr_ = build_sole()
soleL = add_part("sole.L", Vso, Fso, SOLE, seams=sso, attrs=dict(tread=tr_))
mirror_part(soleL, "sole.R")
log("legs + boots done")

# ======================================================================= 4. beanie + goggles
# The knit beanie follows the skull: the same rays from C, starting at the cuff edge and running up to
# the crown, offset by the knit thickness (a folded double-layer rib cuff, a slouch at the crown).
def z_edge(u):
    """Beanie cuff bottom edge height by azimuth (deg, 0 = front)."""
    return ki([(0, 1.729), (30, 1.726), (60, 1.716), (85, 1.706), (105, 1.700), (130, 1.680), (155, 1.664), (180, 1.658)], np.abs(u))


CUFF_H = 0.042
BEANIE_U = np.concatenate([np.arange(0, 180, 3.0), np.arange(-180, 0, 3.0)])
BEANIE_U = np.concatenate([np.arange(0, 180, 3.0), [180.0], -np.arange(177, 0, -3.0)])


def head_dir(u, v):
    u, v = np.radians(u), np.radians(v)
    return np.stack([np.sin(u) * np.cos(v), -np.cos(u) * np.cos(v), np.sin(v)], -1)


def head_hit(u, v):
    D = head_dir(u, v).reshape(-1, 3)
    return C + D * raycast(C, D, F_head, 0.02, 0.22, n=80)[:, None]


def elev_at(u_arr, zt):
    vs = np.arange(-10, 80, 0.4)
    uu, vv = np.meshgrid(u_arr, vs)
    Z = head_hit(uu.ravel(), vv.ravel())[:, 2].reshape(len(vs), len(u_arr))
    out = []
    for j in range(len(u_arr)):
        out.append(np.interp(zt[j], Z[:, j], vs))
    return np.array(out)


def beanie_surface(u, frac_rows, extra=0.0):
    """Points on the beanie outer surface for azimuths u and row fractions (0 = cuff edge, 1 = crown)."""
    ve = elev_at(u, z_edge(u))
    NVr = len(frac_rows)
    out = np.zeros((NVr, len(u), 3))
    for i, f in enumerate(frac_rows):
        v = ve + (89.0 - ve) * f
        Dd = head_dir(u, v)
        r = raycast(C, Dd, F_head, 0.02, 0.22, n=80)
        zrel = C[2] + r * np.sin(np.radians(v)) - z_edge(u)
        cuff = smoothstep(CUFF_H + 0.004, CUFF_H - 0.002, zrel)
        thick = 0.0075 + 0.0065 * cuff + 0.0025 * smoothstep(CUFF_H, CUFF_H + 0.01, zrel) * (1 - cuff)
        slouch = 0.016 * smoothstep(0.35, 1.0, f) ** 1.5 * (0.75 + 0.25 * np.cos(np.radians(u)) * -1 + 0.25)
        rib = 0.0013 * np.abs(np.sin(np.radians(u) * 52)) ** 0.6 * cuff
        knit = 0.0006 * np.abs(np.sin(np.radians(u) * 70)) * (1 - cuff)
        out[i] = C + Dd * (r + thick + slouch + rib + knit + extra)[:, None]
    return out, ve


def build_beanie():
    fr = np.concatenate([np.linspace(0, 0.30, 12), np.linspace(0.33, 0.97, 15)])
    S, ve = beanie_surface(BEANIE_U, fr)
    NU_ = len(BEANIE_U)
    # folded bottom edge: roll under and back up inside
    edge = S[0]
    radial = nrm(edge - C)
    under = edge - A((0, 0, 0.004)) - radial * 0.006
    inside = edge + A((0, 0, 0.010)) - radial * 0.012
    rings = np.concatenate([[inside, under], S])
    V_, F_ = loft(rings, cap1=C + A((0, 0.012, 0.155)))
    F_ = orient_out(V_, F_, C)
    z = V_[:, 2]
    cuffm = np.concatenate([np.ones(2 * NU_), np.repeat((fr < 0.30).astype(float), NU_), [0.0]])
    return V_, F_, seam_column(len(rings), NU_, NU_ // 2), cuffm


Vbn, Fbn, sbn, cfm = build_beanie()
add_part("beanie", Vbn, Fbn, BEANIE, seams=sbn, attrs=dict(cuff=cfm))
log("beanie", len(Vbn))


def build_goggles():
    """Ski-style goggles pushed up onto the beanie: a curved frame with a single lens + a strap."""
    us = np.linspace(-58, 58, 47)
    fr_lo, fr_hi = 0.07, 0.33
    S, _ = beanie_surface(us, [fr_lo, (fr_lo + fr_hi) / 2, fr_hi], extra=0.001)
    bot, mid, top = S[0], S[1], S[2]
    ev = nrm(top - bot)
    out_ = nrm(np.cross(ev, nrm(np.gradient(mid, axis=0))))
    if out_[len(us) // 2] @ (mid[len(us) // 2] - C) < 0:
        out_ = -out_
    PROF = []
    NPR = 20
    for k in range(NPR):                                    # rounded rectangle, counter-clockwise
        a = 2 * np.pi * (k + 0.5) / NPR
        PROF.append((np.cos(a), np.sin(a)))
    rings, pid = [], []
    for i, u in enumerate(us):
        cu = abs(u) / 58.0
        h = 0.023 * (1 - 0.22 * cu ** 2)
        dep = 0.019 * (1 - 0.35 * cu ** 2)
        notch = 0.010 * g(u, 0, 9.0)
        ring = []
        for (ca, sa) in PROF:
            px = np.sign(ca) * abs(ca) ** 0.30
            py = np.sign(sa) * abs(sa) ** 0.30
            vv = py * h + (notch * 0.5 if py < 0 else 0) * (1 + py) + 0.0
            if py < 0:
                vv = max(vv, -h + notch)
            dd = 0.002 + (px * 0.5 + 0.5) * dep
            ring.append(mid[i] + ev[i] * vv + out_[i] * dd)
            lens = (px > 0.6) and (abs(py) < 0.80) and cu < 0.93
            pid.append(LENS if lens else GOGGLE)
        rings.append(ring)
    V_, F_ = loft(rings, cap0=np.mean(rings[0], 0), cap1=np.mean(rings[-1], 0))
    pid += [GOGGLE, GOGGLE]
    F_ = orient_out(V_, F_, axis_fn=lambda p: mid[np.argmin(np.linalg.norm(mid - p, axis=1))] - out_[0] * 0)
    return V_, F_, np.array(pid, float), seam_column(len(us), NPR, NPR // 2)


Vgo, Fgo, pgo, sgo = build_goggles()
add_part("goggles", Vgo, Fgo, pgo, seams=sgo)


def build_strap():
    us = np.concatenate([np.linspace(55, 180, 30), np.linspace(-180, -55, 30)[1:]])
    S, _ = beanie_surface(us, [0.09, 0.31], extra=0.0028)
    bot, top = S[0], S[1]
    rad = nrm((bot + top) / 2 - C)
    rings = []
    for i in range(len(us)):
        rings.append([bot[i] - rad[i] * 0.0015, bot[i] + rad[i] * 0.0012, top[i] + rad[i] * 0.0012, top[i] - rad[i] * 0.0015])
    V_, F_ = loft(rings, closed=True)
    F_ = orient_out(V_, F_, C)
    return V_, F_


Vst, Fst = build_strap()
add_part("strap", Vst, Fst, GOGGLE)


# ======================================================================= 5. hood (down) + fur ruff, scarf
def parka_proj(pts, out=0.0):
    """Project points radially (from the spine axis) onto the parka torso surface, plus an offset."""
    pts = np.asarray(pts, float)
    O = np.stack([np.zeros(len(pts)), np.full(len(pts), 0.01), pts[:, 2] - 0.05], -1)
    D = nrm(pts - O)
    t = raycast(O, D, F_parka, 0.01, 0.45, n=90)
    return O + D * (t + out)[:, None]


HOOD_RIM = [(0.0, 0.20, 1.345), (0.075, 0.19, 1.362), (0.130, 0.150, 1.410), (0.152, 0.100, 1.465),
            (0.130, 0.050, 1.510), (0.092, 0.012, 1.540)]
HOOD_ATT = [(0.0, 0.080, 1.500), (0.045, 0.072, 1.505), (0.075, 0.052, 1.515), (0.088, 0.030, 1.525),
            (0.088, 0.018, 1.535), (0.086, 0.010, 1.545)]


def half_to_full(pts):
    pts = np.asarray(pts, float)
    return np.concatenate([(pts * [-1, 1, 1])[::-1][:-1], pts])


def build_hood():
    rim = catmull(half_to_full(HOOD_RIM), 8)
    att = catmull(half_to_full(HOOD_ATT), 8)
    rim, _ = resample(rim, 61)
    att, _ = resample(att, 61)
    rim = parka_proj(rim, 0.022)
    NB = 14
    bs = np.linspace(0, 1, NB)
    outer, inner = [], []
    for b in bs:
        base = rim * (1 - b) + att * b
        onback = parka_proj(base, 0.003)
        a_ = np.linspace(-1, 1, len(rim))
        thick = (0.075 * np.sin(np.pi * min(b * 1.05, 1.0)) ** 0.6 * (1 - 0.30 * np.abs(a_))) + 0.022 * (1 - b)
        folds = 0.006 * np.sin(a_ * 9 + b * 5) * np.sin(np.pi * b) + 0.004 * np.sin(a_ * 23 - b * 3) * np.sin(np.pi * b)
        nb = nrm(onback - np.stack([np.zeros(len(onback)), np.full(len(onback), 0.01), onback[:, 2] - 0.05], -1))
        outer.append(onback + nb * (thick + folds)[:, None])
        inner.append(onback)
    # closed pillow: outer rows rim -> attachment, then inner rows attachment -> rim
    rows = outer + inner[::-1]
    R = np.array(rows)                                      # (2NB, 61, 3)
    V_, F_ = loft(R, closed=False)
    # close the two open ends (a = -1 / +1) with fans
    M, N = R.shape[:2]
    for j, cap in ((0, R[:, 0].mean(0)), (N - 1, R[:, -1].mean(0))):
        V_ = np.concatenate([V_, [cap]]); p = len(V_) - 1
        for i in range(M - 1):
            F_.append((p, i * N + j, (i + 1) * N + j) if j == 0 else (p, (i + 1) * N + j, i * N + j))
    F_ = orient_out(V_, F_, A((0, 0.10, 1.40)))
    return V_, F_, rim, seam_column(M, N, 0)


Vho, Fho, RIM, sho = build_hood()
add_part("hood", Vho, Fho, HOOD)


def build_ruff(rim):
    path, _ = resample(catmull(rim[::3], 6), 124)
    rng = np.random.default_rng(7)
    ph = rng.uniform(0, 6.3, 8)

    def rad(s, th):
        L = s[-1, 0]
        tuft = (0.60 * np.sin(s * 95 + th * 2 + ph[0]) + 0.40 * np.sin(s * 190 - th * 3 + ph[1])
                + 0.22 * np.sin(s * 330 + th * 5 + ph[2]) + 0.25 * np.sin(th * 6 + s * 60 + ph[3]))
        tuft = np.sign(tuft) * np.abs(tuft) ** 0.8
        r = 0.041 + 0.0105 * np.clip(tuft, -0.8, 1.2)
        r = r * (1 + 0.25 * np.clip(np.cos(th), 0, 1))           # fuller on the outside of the rim
        end = smoothstep(0.0, 0.03, s) * smoothstep(L, L - 0.03, s)
        return r * (0.35 + 0.65 * end)
    rings, s, th, fr = tube(path, 32, rad, (0, 0.6, 1.0))
    V_, F_ = loft(rings, cap0=path[0], cap1=path[-1])
    F_ = orient_out(V_, F_, axis_fn=lambda p: path[np.argmin(np.linalg.norm(path - p, axis=1))])
    lu = np.concatenate([np.repeat(s, len(th)), [0.0, s[-1]]])
    lv = np.concatenate([np.tile(th / (2 * np.pi), len(s)), [0.0, 0.0]])
    return V_, F_, seam_column(len(rings), 32, 16), lu, lv


Vru, Fru, sru, luru, lvru = build_ruff(RIM)
add_part("ruff", Vru, Fru, FUR, seams=sru, attrs=dict(lu=luru, lv=lvru))
log("hood + ruff", len(Vho), len(Vru))


def build_scarf_loop(zf, zb, rr, tr, seed):
    NPth = 72
    t = np.linspace(0, 2 * np.pi, NPth, endpoint=False)
    zc = (zf + zb) / 2 + (zf - zb) / 2 * np.cos(t)
    path = np.stack([rr * np.sin(t), 0.010 - rr * np.cos(t) * 1.02, zc], -1)
    path = np.concatenate([path, path[:1]])
    NA = 24
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6.3, 6)
    T, N_, B_ = frames(path, (0, 0, 1))
    rings = []
    for i in range(NPth):
        s = t[i]
        ring = []
        for k in range(NA):
            a = 2 * np.pi * k / NA
            twist = a + 0.9 * np.sin(s * 2 + ph[0])
            ex, ey = tr * 1.25, tr * 0.80
            ribs = 0.0018 * np.abs(np.sin(s * 70)) ** 0.7 + 0.0012 * np.abs(np.sin(a * 6 + s * 3))
            lump = 0.004 * np.sin(s * 5 + ph[1]) * np.sin(a * 2 + s + ph[2])
            ring.append(path[i] + N_[i] * (np.cos(twist) * (ey + ribs + lump)) + B_[i] * (np.sin(twist) * (ex + ribs + lump)))
        rings.append(ring)
    rings = np.array(rings)
    # make it exactly symmetric in x (mirror the x > 0 half)
    V_, F_ = loft(np.concatenate([rings, rings[:1]]), closed=True)
    V_ = V_[:-NA]
    F_ = [tuple(i % (NPth * NA) for i in f) for f in F_]
    F_ = orient_out(V_, F_, axis_fn=lambda p: path[np.argmin(np.linalg.norm(path[:-1] - p, axis=1))])
    lu = np.repeat(t * rr, NA)
    lv = np.tile(np.arange(NA) / NA, NPth)
    return V_, F_, seam_column(NPth, NA, 0), lu, lv


def symmetrize(V_):
    """Snap a symmetric part to exact mirror symmetry (average each vertex with its mirror twin)."""
    kd = KDTree(len(V_))
    for i, v in enumerate(V_):
        kd.insert(v, i)
    kd.balance()
    W_ = V_.copy()
    for i, v in enumerate(V_):
        j = kd.find((-v[0], v[1], v[2]))[1]
        W_[i] = 0.5 * (V_[i] + V_[j] * [-1, 1, 1])
    return W_


for (zf, zb, rr, tr, sd) in ((1.492, 1.520, 0.101, 0.024, 3), (1.527, 1.566, 0.097, 0.022, 4)):
    Vsc, Fsc, ssc, lusc, lvsc = build_scarf_loop(zf, zb, rr, tr, sd)
    add_part("scarf", Vsc, Fsc, SCARF, seams=ssc, attrs=dict(lu=lusc, lv=lvsc))


def build_scarf_tail():
    """Loose end hanging down the front-left of the chest, with a fringe."""
    top = parka_proj([(0.050, -0.10, 1.47)], 0.010)[0]
    pts = [top, (0.062, -0.150, 1.40), (0.070, -0.160, 1.32), (0.076, -0.158, 1.245)]
    path, _ = resample(catmull(pts, 10), 34)
    path = np.array([parka_proj([p], 0.014)[0] if p[2] < 1.45 else p for p in path])
    T, N_, B_ = frames(path, (0, -1, 0))
    NA = 20
    rings = []
    for i, p in enumerate(path):
        s = i / (len(path) - 1)
        w = 0.058 + 0.008 * s
        tk = 0.0065
        ring = []
        for k in range(NA):
            a = 2 * np.pi * k / NA
            ca, sa = np.cos(a), np.sin(a)
            px = w * np.sign(sa) * abs(sa) ** 0.25
            py = tk * np.sign(ca) * abs(ca) ** 0.4 + 0.003 * np.sin(px * 90 + s * 6)
            ring.append(p + B_[i] * px + N_[i] * py)
        rings.append(ring)
    V_, F_ = loft(rings)
    F_ = orient_out(V_, F_, axis_fn=lambda q: path[np.argmin(np.linalg.norm(path - q, axis=1))])
    # fringe: 9 tassels hanging from the end
    end, Te, Be = path[-1], T[-1], B_[-1]
    for k in range(9):
        c0 = end + Be * (-0.052 + 0.013 * k) + Te * 0.002
        tpath = np.array([c0 + Te * (0.012 * q) + A((0, -0.002, 0)) * q for q in range(5)])
        rs, _, _, _ = tube(tpath, 6, lambda s, th: 0.0028 * (1 - 0.5 * s / 0.05) + 0 * th, (0, -1, 0))
        v2, f2 = loft(rs, cap1=tpath[-1] + Te * 0.003)
        F_ += [tuple(i + len(V_) for i in f) for f in orient_out(v2, f2, axis_fn=lambda q: tpath[np.argmin(np.linalg.norm(tpath - q, axis=1))])]
        V_ = np.concatenate([V_, v2])
    return V_, F_, seam_column(len(path), NA, 0)


Vtl, Ftl, stl = build_scarf_tail()
add_part("scarf_tail", Vtl, Ftl, SCARF, sym="asym", seams=stl)
log("scarf done")


# ======================================================================= 6. hair: brows, beard, tufts (shells over the skin), lashes
def vertex_normals(V_, F_):
    Nv = np.zeros_like(V_)
    for f in F_:
        p = V_[list(f)]
        n_ = np.cross(p[1] - p[0], p[-1] - p[0]) if len(f) == 4 else np.cross(p[1] - p[0], p[2] - p[0])
        for i in f:
            Nv[i] += n_
    return nrm(Nv)


HN = grad(F_head, Vh)


def hair_masks(P):
    x, y, z = np.abs(P[:, 0]), P[:, 1], P[:, 2]
    zd = zdes(z)
    zst, zvb, zlb = lip_lines(np.minimum(x, MW))
    frontf = (y < -0.02)
    # eyebrows: a band above each orbit, thick at the head, tapering out to the tail
    bx = np.clip((x - 0.010) / 0.046, 0, 1)
    bz = 1.6915 + 0.0060 * np.sin(np.pi * bx ** 0.8) - 0.002 * bx
    bw = 0.0052 * (1 - 0.55 * bx) + 0.0012
    brow = smoothstep(bw, bw * 0.55, np.abs(z - bz)) * smoothstep(0.008, 0.013, x) * smoothstep(0.060, 0.054, x) * frontf
    # beard: cheeks below a line from the sideburn to the nasolabial fold, mustache, chin, jaw, neck front
    cheek_line = ki([(0.020, 1.618), (0.030, 1.628), (0.045, 1.640), (0.060, 1.655), (0.070, 1.668), (0.080, 1.690)], x)
    beard = smoothstep(cheek_line + 0.004, cheek_line - 0.012, z) * smoothstep(1.530, 1.548, z)
    beard *= smoothstep(0.012, -0.004, y)                           # stops behind the jaw angle
    lipsx = x < MW + 0.002
    upper_lip_skin = (zd > zvb + 0.0008)
    lower_ok = (zd < zlb - 0.0015)
    mouth_zone = lipsx & ~upper_lip_skin & ~lower_ok
    beard = beard * (~mouth_zone) * (1 - smoothstep(0.0215, 0.013, x) * (zd > zvb) * (zd < 1.609) * 0.35)
    beard *= 1 - smoothstep(1.614, 1.619, zd) * smoothstep(0.024, 0.018, x)     # clear of the nostrils
    # sideburns / temple tufts / nape (below the beanie edge)
    u = np.degrees(np.arctan2(x, -(y - C[1])))
    ze = z_edge(u)
    below_cap = smoothstep(ze + 0.004, ze - 0.002, z)
    sideburn = smoothstep(0.064, 0.070, x) * smoothstep(-0.040, -0.030, y) * smoothstep(0.018, 0.008, y) * smoothstep(1.625, 1.640, z)
    nape = smoothstep(0.040, 0.060, y) * smoothstep(1.600, 1.615, z)
    around_ear = smoothstep(0.066, 0.072, x) * smoothstep(1.680, 1.690, z) * smoothstep(-0.03, -0.02, y)
    scalp = np.maximum.reduce([sideburn, nape, around_ear]) * below_cap
    return brow, np.clip(beard, 0, 1), scalp


def coarse_faces(step):
    """Faces of the head grid subsampled by `step` (skipping the split lip row)."""
    NU, NV, jm, sc = HEAD_GRID
    F_ = []
    for i in range(0, NV - step, step):
        for j in range(0, NU, step):
            j2 = (j + step) % NU
            if i <= jm <= i + step and (j in sc or j2 in sc or any(((j + k) % NU) in sc for k in range(step))):
                continue
            F_.append((i * NU + j, i * NU + j2, (i + step) * NU + j2, (i + step) * NU + j))
    return F_


def build_shell(mask, thick, name, clump_scale, seed, pidv=HAIR, thr=0.04, droop=0.0, step=1):
    Pm = mask
    FF = Fh if step == 1 else coarse_faces(step)
    sel_f = [f for f in FF if max(Pm[list(f)]) > thr and min(Pm[list(f)]) > thr * 0.25]
    used = sorted({i for f in sel_f for i in f})
    idx = {v: k for k, v in enumerate(used)}
    src = np.array(used)
    P = Vh[src]
    m = Pm[src]
    rng = np.random.default_rng(seed)
    cl = vnoise(P, clump_scale, seed) * 0.5 + 0.5
    fine = vnoise(P, clump_scale * 3.1, seed + 1) * 0.5 + 0.5
    t = thick * smoothstep(thr, 0.85, m) ** 1.2 * (0.60 + 0.40 * cl) * (0.85 + 0.15 * fine) + 0.00012
    Vn = P + HN[src] * t[:, None] + A((0, 0, -droop)) * smoothstep(thr, 1.0, m)[:, None]
    F_ = [tuple(idx[i] for i in f) for f in sel_f]
    return Vn, F_, src


brow_m, beard_m, scalp_m = hair_masks(Vh)
HAIR_SRC = []
for m_, th_, nm_, sc_, sd_, dr_ in ((brow_m, 0.0009, "brows", 160, 11, 0.0002), (beard_m, 0.0034, "beard", 70, 12, 0.0),
                                    (scalp_m, 0.0028, "tufts", 60, 13, 0.0)):
    Vsh, Fsh, src = build_shell(m_, th_, nm_, sc_, sd_, droop=dr_, step=1 if nm_ == "brows" else 2)
    hp = add_part(nm_, Vsh, Fsh, HAIR, attrs=dict(srcidx=src.astype(float), hkind=np.full(len(Vsh), {"brows": 1.0, "beard": 2.0, "tufts": 3.0}[nm_])))
    log(nm_, len(Vsh))


def build_lashes(side):
    e = EYEC * [side, 1, 1]
    dxs = np.linspace(-0.0125, 0.0128, 18)
    rows = []
    for dx in dxs:
        dm, dl = -0.0150, 0.0142
        tt = np.clip((dx - dm) / (dl - dm), 0, 1)
        z0 = -0.0006 + 0.0027 * tt
        zu = z0 + 0.0058 * np.sin(np.pi * tt ** 0.80)
        base = e + A((dx * side, 0, zu))
        base[1] = e[1] - np.sqrt(max((RE + 0.0019) ** 2 - dx ** 2 - zu ** 2, 1e-8))
        ln = 0.0065 * np.sin(np.pi * (0.15 + 0.7 * tt)) + 0.002
        dirn = nrm(A((dx * side * 0.4, -1.0, 0.55)))
        up = A((0, 0.25, 1.0))
        mid = base + dirn * ln * 0.55 + up * ln * 0.10
        tip = base + dirn * ln * 0.80 + up * ln * 0.55
        k = 0.00035
        rows.append([base + up * k, mid + up * k, tip, mid - up * k, base - up * k])
    R = np.array(rows)
    V_, F_ = loft(R, closed=True)
    F_ = orient_out(V_, F_, e)
    return V_, F_


for sd in (1, -1):
    Vl, Fl = build_lashes(sd)
    if sd < 0:
        Fl = [tuple(reversed(f)) for f in Fl]
        Fl = orient_out(Vl, Fl, EYEC * [-1, 1, 1])
    add_part("lashes." + ("L" if sd > 0 else "R"), Vl, Fl, LASH, sym="pair",
             weights={("lid_upper.L" if sd > 0 else "lid_upper.R"): np.ones(len(Vl))})

# ======================================================================= 7. gloves
# Insulated work gloves: a raycast palm / back shell in the hand frame, one tube per finger that
# follows the finger bones (knuckle bulges, flexion creases on the palm side, rounded tips) and a
# gauntlet cuff that goes over the parka sleeve with a drawcord band.
H_DIR = nrm(bt("hand.L") - W_L)
H_ACR = nrm(A((0, -1, 0)) - H_DIR * (H_DIR @ A((0, -1, 0))))
H_PN = nrm(np.cross(H_DIR, H_ACR))


def hand_local(P):
    d = P - W_L
    return np.stack([d @ H_DIR, d @ H_ACR, d @ H_PN], -1)


def F_hand(P):
    L_ = hand_local(P)
    d = sd_rbox(L_, (0.047, 0.004, 0.001), (0.036, 0.031, 0.005), 0.012)
    d = smin(d, sd_ell(L_, (0.030, 0.026, 0.010), (0.028, 0.018, 0.015)), 0.010)      # thenar mound
    d = smin(d, sd_ell(L_, (0.004, 0.0, 0.0), (0.030, 0.036, 0.022)), 0.012)          # wrist
    return d


def build_glove_body():
    NA = 30
    ss = np.linspace(-0.012, 0.098, 26)
    th = 2 * np.pi * np.arange(NA) / NA
    O, Dr = [], []
    for s in ss:
        for t in th:
            O.append(W_L + H_DIR * s + H_ACR * 0.004)
            Dr.append(H_ACR * np.cos(t) + H_PN * np.sin(t))
    O, Dr = A(O), A(Dr)
    P = O + Dr * raycast(O, Dr, F_hand, 0.0, 0.08, n=50)[:, None]
    Lc = hand_local(P)
    # stitched back seams + palm creases
    off = 0.0007 * np.sin(Lc[:, 1] * 2 * np.pi / 0.021) * (Lc[:, 2] < 0) * smoothstep(0.02, 0.05, Lc[:, 0])
    off += -0.0010 * g(Lc[:, 0], 0.062, 0.003) * (Lc[:, 2] > 0) - 0.0008 * g(Lc[:, 0] - 0.4 * Lc[:, 1], 0.040, 0.003) * (Lc[:, 2] > 0)
    P = P + Dr * off[:, None]
    rings = P.reshape(len(ss), NA, 3)
    V_, F_ = loft(rings, cap0=W_L + H_DIR * (ss[0] - 0.004) + H_ACR * 0.004, cap1=W_L + H_DIR * (ss[-1] + 0.012) + H_ACR * 0.004)
    F_ = orient_out(V_, F_, axis_fn=lambda p: W_L + H_DIR * ((p - W_L) @ H_DIR) + H_ACR * 0.004)
    return V_, F_, seam_column(len(ss), NA, NA * 3 // 4)


FINGER_R = {"thumb": 0.0128, "index": 0.0114, "middle": 0.0118, "ring": 0.0112, "pinky": 0.0100}


def build_finger(name):
    heads = [bh(f"{name}_0{k}.L") for k in (1, 2, 3)]
    tip = bt(f"{name}_03.L")
    d0 = nrm(heads[1] - heads[0])
    dt = nrm(tip - heads[2])
    start = heads[0] - d0 * (0.020 if name != "thumb" else 0.010)
    pts = [start, heads[0], heads[1], heads[2], tip]
    path = catmull(pts, 8)
    path, _ = resample(path, 21)
    joints = [np.linalg.norm(np.diff(np.concatenate([[start], [h]]), axis=0)) for h in heads]
    s_j = []
    acc = 0
    seg = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
    for h in heads[1:] + [tip]:
        s_j.append(seg[np.argmin(np.linalg.norm(path - h, axis=1))])
    s_k = seg[np.argmin(np.linalg.norm(path - heads[0], axis=1))]
    L_ = seg[-1]
    R0 = FINGER_R[name]

    def rad(s, th):
        r = R0 * (1.0 - 0.14 * s / L_)
        for sj in [s_k] + s_j[:2]:
            r = r + 0.0011 * g(s, sj, 0.006)                                    # knuckle
        palm = np.clip(np.cos(th), 0, 1)                                        # th = 0 toward the palm
        for sj in s_j[:2]:
            r = r - 0.0012 * palm * g(s, sj, 0.0025) + 0.0006 * palm * g(s, sj + 0.004, 0.002)
        r = r * (1 - 0.10 * np.abs(np.sin(th)) ** 2)                              # a bit flatter side to side
        tipc = np.sqrt(np.clip(1 - ((s - (L_ - R0 * 0.9)) / (R0 * 0.95)) ** 2, 0, 1))
        r = np.where(s > L_ - R0 * 0.9, r * np.maximum(tipc, 0.05), r)
        return r
    rings, s, th, fr = tube(path, 14, rad, H_PN)
    V_, F_ = loft(rings, cap1=path[-1] + dt * 0.0005)
    F_ = orient_out(V_, F_, axis_fn=lambda p: path[np.argmin(np.linalg.norm(path - p, axis=1))])
    return V_, F_, seam_column(len(rings), 14, 7)


def build_gauntlet():
    a = W_L - ARM_D * 0.004
    b = W_L - ARM_D * 0.095
    path, _ = resample(np.array([a, b]), 16)
    L_ = np.linalg.norm(b - a)

    def rad(s, th):
        r = hermite_np([(0, 0.046), (0.012, 0.050), (0.03, 0.061), (0.07, 0.068), (L_ - 0.012, 0.072), (L_, 0.074)], s)
        r = r * (1 + 0.08 * np.cos(2 * th))
        r = r + 0.0030 * g(s, L_ - 0.010, 0.005) + 0.0025 * np.sin(th * 7 + s * 40) * g(s, 0.05, 0.03)
        return r
    rings, s, th, fr = tube(path, 30, rad, (0, -1, 0))
    T = fr[0]
    rings = np.concatenate([[a + (rings[0] - a) * 0.9 + T[0] * 0.004], rings,
                            [b + (rings[-1] - b) * 0.86 - T[-1] * 0.010]])
    V_, F_ = loft(rings)
    F_ = orient_out(V_, F_, axis_fn=lambda p: path[np.argmin(np.linalg.norm(path - p, axis=1))])
    return V_, F_, seam_column(len(rings), 30, 7)


def glove_part():
    Vs, Fs, Ss, fid = [], [], [], []
    off = 0
    for k, (v, f, sm) in enumerate([build_glove_body(), build_gauntlet()] + [build_finger(n) for n in FINGER_R]):
        Vs.append(v); Fs += [tuple(i + off for i in ff) for ff in f]; Ss += [(a + off, b + off) for a, b in sm]
        fid.append(np.full(len(v), float(k)))
        off += len(v)
    V_ = np.concatenate(Vs)
    palm = (hand_local(V_)[:, 2] > 0.004).astype(float)
    return V_, Fs, Ss, np.concatenate(fid), palm


Vgl, Fgl, sgl, fidgl, palmgl = glove_part()
gloveL = add_part("glove.L", Vgl, Fgl, GLOVE, seams=sgl, attrs=dict(gpiece=fidgl, palm=palmgl))
mirror_part(gloveL, "glove.R")
log("gloves", len(Vgl))


# ======================================================================= 8. belt, knife + sheath, pouch, toggles, drawcords
Z_BELT = 1.013


def build_belt():
    th = np.radians(np.concatenate([np.arange(0, 180, 3.0), [180.0], -np.arange(177, 0, -3.0)]))
    O = np.stack([np.zeros_like(th), np.full_like(th, 0.008), np.full_like(th, Z_BELT)], -1)
    Dd = np.stack([np.sin(th), -np.cos(th), np.zeros_like(th)], -1)
    r = raycast(O, Dd, F_parka, 0.05, 0.4, n=80) + 0.0015
    N_ = len(th)
    prof = [(-0.021, -0.0030), (-0.021, 0.0045), (-0.0195, 0.0058), (0.0195, 0.0058), (0.021, 0.0045), (0.021, -0.0030)]
    rings = []
    for (dz, dr) in prof:
        rings.append(O + A((0, 0, dz)) + Dd * (r + dr)[:, None])
    R = np.array(rings)
    V_, F_ = loft(R, closed=True)
    F_ = [tuple(f) for f in F_]
    # close the band into a solid loop: connect last profile row back to the first
    F_ += [((len(prof) - 1) * N_ + j, (len(prof) - 1) * N_ + (j + 1) % N_, (j + 1) % N_, j) for j in range(N_)]
    F_ = orient_out(V_, F_, axis_fn=lambda p: A((0, 0.008, p[2])))
    front = O[0] + Dd[0] * (r[0] + 0.0055)
    return V_, F_, front


Vbe, Fbe, BELT_FRONT = build_belt()
add_part("belt", Vbe, Fbe, BELT)


def rect_ring(center, ax_u, ax_v, ax_n, w, h, bar, thick, n=36):
    """A rectangular frame (buckle) as a loft of a small square section along a rounded rectangle."""
    pts = []
    for k in range(n):
        a = 2 * np.pi * k / n
        ca, sa = np.cos(a), np.sin(a)
        pts.append(center + ax_u * (w / 2 * np.sign(ca) * abs(ca) ** 0.25) + ax_v * (h / 2 * np.sign(sa) * abs(sa) ** 0.25))
    pts = np.array(pts)
    rings = []
    T = nrm(np.roll(pts, -1, 0) - np.roll(pts, 1, 0))
    for p, t in zip(pts, T):
        side = nrm(np.cross(t, ax_n))
        rings.append([p + side * bar / 2, p + ax_n * thick, p - side * bar / 2, p - ax_n * thick * 0.2])
    R = np.array(rings)
    V_, F_ = loft(np.concatenate([R, R[:1]]), closed=True)
    V_ = V_[:-4]
    F_ = [tuple(i % (n * 4) for i in f) for f in F_]
    return V_, orient_out(V_, F_, center - ax_n * 0.01)


bf = BELT_FRONT
Vbk, Fbk = rect_ring(bf + A((0, -0.001, 0)), A((1, 0, 0)), A((0, 0, 1)), A((0, -1, 0)), 0.056, 0.054, 0.0060, 0.0035)
add_part("buckle", Vbk, Fbk, METAL)


def box_part(center, ax_u, ax_v, ax_n, hu, hv, hn, rnd, n_u=10, n_v=10, pid=POUCH, flap=None, sym="asym"):
    """Rounded box found by rays from its centre (pouch body / flap / sheath loop)."""
    def F(P):
        d = P - center
        L_ = np.stack([d @ ax_u, d @ ax_v, d @ ax_n], -1)
        return sd_rbox(L_, (0, 0, 0), (hu, hv, hn), rnd)
    uu, vv = np.meshgrid(np.linspace(-np.pi / 2 + 0.05, np.pi / 2 - 0.05, n_v), np.linspace(0, 2 * np.pi, 4 * n_u, endpoint=False), indexing="ij")
    D = (ax_n[None, None] * (np.cos(uu) * np.cos(vv))[..., None] + ax_u[None, None] * (np.cos(uu) * np.sin(vv))[..., None]
         + ax_v[None, None] * np.sin(uu)[..., None]).reshape(-1, 3)
    P = center + D * raycast(center, D, F, 0.0, 0.3, n=60)[:, None]
    V_, F_ = loft(P.reshape(n_v, 4 * n_u, 3), cap0=center - ax_v * (hv + rnd), cap1=center + ax_v * (hv + rnd))
    return V_, orient_out(V_, F_, center)


def surf_frame(p):
    """Point on the parka at p (radial projection) and a local frame (u horizontal, v up, n outward)."""
    q = parka_proj([p], 0.0)[0]
    n_ = grad(F_parka, q[None])[0]
    v_ = nrm(A((0, 0, 1)) - n_ * n_[2])
    u_ = np.cross(v_, n_)
    return q, u_, v_, n_


# knife sheath on the right hip, hanging from the belt, knife handle above it
q, u_, v_, n_ = surf_frame((-0.20, 0.010, 0.93))
tilt = nrm(v_ + u_ * 0.12)
sheath_path = [q + n_ * 0.016 + tilt * 0.095, q + n_ * 0.018, q + n_ * 0.019 - tilt * 0.080, q + n_ * 0.018 - tilt * 0.130]
sp, _ = resample(catmull(sheath_path, 8), 26)


def sheath_rad(s, th):
    L_ = s[-1, 0]
    w = hermite_np([(0, 0.022), (0.05, 0.023), (L_ * 0.7, 0.018), (L_, 0.006)], s)
    t = hermite_np([(0, 0.010), (L_ * 0.6, 0.008), (L_, 0.004)], s)
    ct, st = np.cos(th), np.sin(th)
    r = 1.0 / np.sqrt((ct / t) ** 2 + (st / w) ** 2)
    return r + 0.0007 * g(np.abs(st), 0.97, 0.03)                         # stitched welt along the edges


rings, s_, th_, fr_ = tube(sp, 20, sheath_rad, n_)
Vsh, Fsh = loft(rings, cap0=sp[0] + tilt * 0.002, cap1=sp[-1] - tilt * 0.004)
Fsh = orient_out(Vsh, Fsh, axis_fn=lambda p: sp[np.argmin(np.linalg.norm(sp - p, axis=1))])
add_part("sheath", Vsh, Fsh, SHEATH, sym="asym", seams=seam_column(len(rings), 20, 10))
Vlp, Flp = box_part(q + n_ * 0.010 + tilt * 0.082, u_, tilt, n_, 0.016, 0.022, 0.004, 0.003, 6, 6, pid=SHEATH)
add_part("sheath_loop", Vlp, Flp, SHEATH, sym="asym")
kbase = sp[0] + tilt * 0.004
kp, _ = resample(np.array([kbase, kbase + tilt * 0.108 + n_ * 0.004]), 18)


def handle_rad(s, th):
    r = hermite_np([(0, 0.0125), (0.006, 0.0135), (0.012, 0.0105), (0.03, 0.0112), (0.06, 0.0118), (0.09, 0.0108),
                    (0.098, 0.0128), (0.108, 0.0060)], s)
    r = r * (1 + 0.18 * np.cos(2 * th)) + 0.0006 * np.sin(s * 900) * smoothstep(0.015, 0.02, s) * smoothstep(0.09, 0.085, s)
    return r


rings, s_, th_, fr_ = tube(kp, 16, handle_rad, n_)
Vkn, Fkn = loft(rings, cap0=kp[0], cap1=kp[-1])
Fkn = orient_out(Vkn, Fkn, axis_fn=lambda p: kp[np.argmin(np.linalg.norm(kp - p, axis=1))])
kpid = np.where((s_[:, None] < 0.012) | (s_[:, None] > 0.093), float(METAL), float(KNIFE)) * np.ones((1, 16))
add_part("knife", Vkn, Fkn, np.concatenate([kpid.ravel(), [METAL, METAL]]), sym="asym", seams=seam_column(len(rings), 16, 8))

# pouch on the left hip, a little behind the side seam
q, u_, v_, n_ = surf_frame((0.185, 0.050, 0.955))
Vpo, Fpo = box_part(q + n_ * 0.027 - v_ * 0.012, u_, v_, n_, 0.036, 0.042, 0.014, 0.010, 10, 10)
add_part("pouch", Vpo, Fpo, POUCH, sym="asym")
Vpf, Fpf = box_part(q + n_ * 0.044 + v_ * 0.020, u_, nrm(v_ - n_ * 0.35), nrm(n_ + v_ * 0.35), 0.039, 0.022, 0.0035, 0.004, 10, 6)
add_part("pouch_flap", Vpf, Fpf, POUCH, sym="asym")
Vps, Fps = box_part(q + n_ * 0.049 + v_ * 0.004, u_, v_, n_, 0.004, 0.004, 0.002, 0.003, 4, 4)
add_part("pouch_snap", Vps, Fps, METAL, sym="asym")


def cyl(a, b, r, n=10, pid=TOGGLE, sym="sym", taper=1.0):
    path, _ = resample(np.array([a, b]), 6)
    hint = np.cross(nrm(b - a), A((0.3, 0.2, 1.0)))
    rings, s_, th_, fr_ = tube(path, n, lambda s, th: r * (1 - (1 - taper) * s / s[-1, 0]) * (1 + 0.0 * th)
                               * (0.8 + 0.2 * np.sqrt(np.clip(np.sin(np.pi * np.clip(s / s[-1, 0], 0.02, 0.98)), 0, 1))), hint)
    V_, F_ = loft(rings, cap0=a, cap1=b)
    return V_, orient_out(V_, F_, axis_fn=lambda p: path[np.argmin(np.linalg.norm(path - p, axis=1))])


# horn toggles down the storm flap
for zt in (1.415, 1.300, 1.185, 0.930):
    q = parka_proj([(0.0, -0.2, zt)], 0.0078)[0]
    Vt, Ft = cyl(q + A((-0.016, 0.001, 0.003)), q + A((0.016, 0.001, 0.003)), 0.0052, 12)
    add_part("toggle", symmetrize(Vt), Ft, TOGGLE)
    Vt, Ft = cyl(q + A((0, 0.002, 0.012)), q + A((0, -0.001, -0.004)), 0.0016, 6, pid=CORD)
    add_part("toggle_loop", Vt, Ft, CORD)
# drawcord ends + cord locks hanging from the waist channel
for sd in (1,):
    q = parka_proj([(0.040 * sd, -0.2, Z_CORD)], 0.0)[0]
    a = q + A((0, -0.004, 0))
    b = a + A((0.004 * sd, -0.008, -0.075))
    Vc, Fc = cyl(a, b, 0.0022, 8, pid=CORD)
    cordL = add_part("cord.L", Vc, Fc, CORD)
    Vl, Fl = cyl(b + A((0, 0, 0.016)), b - A((0, 0, 0.004)), 0.0055, 10, pid=TOGGLE, taper=0.8)
    lockL = add_part("cordlock.L", Vl, Fl, TOGGLE)
    mirror_part(cordL, "cord.R"); mirror_part(lockL, "cordlock.R")
# zipper pull at the collar
q = parka_proj([(0.0, -0.2, 1.50)], 0.009)[0]
Vz, Fz = box_part(q - A((0, 0, 0.012)), A((1, 0, 0)), A((0, 0, 1)), A((0, -1, 0)), 0.004, 0.009, 0.0012, 0.0015, 4, 5, pid=METAL, sym="sym")
add_part("zip_pull", symmetrize(Vz), Fz, METAL)
log("accessories done")

# ======================================================================= armature + weights
arm = human_rig.build_armature()
DEFORM = [b.name for b in arm.data.bones if b.use_deform]

# @@WEIGHTS@@


# ======================================================================= join into one object
def assemble():
    Vs, Fs, pid, names = [], [], [], []
    seams = []
    off = 0
    attr_names = sorted({k for p in PARTS for k in p.attrs})
    attrs = {k: [] for k in attr_names}
    W = {}
    sym = []
    for p in PARTS:
        n = len(p.V)
        Vs.append(p.V); pid.append(p.pid)
        Fs += [tuple(i + off for i in f) for f in p.F]
        seams += [(a + off, b + off) for a, b in p.seams]
        for k in attr_names:
            attrs[k].append(p.attrs.get(k, np.zeros(n)))
        for bn, w in (p.weights or {}).items():
            W.setdefault(bn, []).append((off, w))
        sym.append(np.full(n, {"sym": 0.0, "pair": 1.0, "asym": 2.0}[p.sym]))
        p.off = off
        off += n
    Vall = np.concatenate(Vs)
    for p in PARTS:
        if len(p.pid) != len(p.V): log("PID MISMATCH", p.name, len(p.pid), len(p.V))
    me = bpy.data.meshes.new("Human")
    me.from_pydata([tuple(v) for v in Vall], [], Fs)
    me.validate(clean_customdata=False)
    ob = bpy.data.objects.new("Human", me)
    scene.collection.objects.link(ob)
    for nm_, vals in [("part", np.concatenate(pid)), ("symm", np.concatenate(sym))] + [(k, np.concatenate(v)) for k, v in attrs.items()]:
        a = me.attributes.new(nm_, 'FLOAT', 'POINT')
        if len(vals) != len(me.vertices):
            log("ATTR LEN MISMATCH", nm_, len(vals), len(me.vertices))
        a.data.foreach_set("value", vals.astype(np.float32))
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    bm = bmesh.new(); bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    ns = 0
    for a, b in seams:
        e = bm.edges.get((bm.verts[a], bm.verts[b]))
        if e:
            e.seam = True; ns += 1
    bm.to_mesh(me); bm.free()
    log("joined", len(me.vertices), "verts", len(me.polygons), "faces", ns, "seam edges")
    return ob, W


human, WPARTS = assemble()
me = human.data
NV = len(me.vertices)
CO = np.zeros(NV * 3, np.float32); me.vertices.foreach_get("co", CO); CO = CO.reshape(-1, 3).astype(np.float64)
PID = np.zeros(NV, np.float32); me.attributes["part"].data.foreach_get("value", PID)

# ======================================================================= skin weights
# Weights are smooth functions of the rest position, evaluated per garment region, so that stacked
# layers (sleeve over torso, gaiter over trousers over boot, scarf over collar, beard over skin) get the
# same weights where they overlap and move together.  Limited to 4 influences, normalised.
BIDX = {n: i for i, n in enumerate(DEFORM)}
WM = np.zeros((NV, len(DEFORM)), np.float32)


def put(idx, wd):
    for bn, w in wd.items():
        WM[idx, BIDX[bn]] += np.asarray(w, np.float32) * np.ones(len(idx), np.float32)


def chain(t, keys):
    """Blend along a chain: keys = [(bone, centre)], smoothstep between consecutive centres."""
    out = {k[0]: np.zeros_like(t) for k in keys}
    out[keys[0][0]] += (t <= keys[0][1])
    out[keys[-1][0]] += (t > keys[-1][1])
    for (a, ta), (b, tb) in zip(keys, keys[1:]):
        m = (t > ta) & (t <= tb)
        u = smoothstep(ta, tb, t)
        out[a] += np.where(m, 1 - u, 0)
        out[b] += np.where(m, u, 0)
    return out


def scale(wd, f):
    return {k: v * f for k, v in wd.items()}


def addw(*ws):
    out = {}
    for w in ws:
        for k, v in w.items():
            out[k] = out.get(k, 0) + v
    return out


SPINE_KEYS = [("pelvis", 1.00), ("spine_01", 1.165), ("spine_02", 1.295), ("spine_03", 1.42), ("neck", 1.56), ("head", 1.63)]


def torso_w(P):
    """Trunk chain by height, hips blending into the thighs below the pelvis."""
    x, z = P[:, 0], P[:, 2]
    w = chain(z, SPINE_KEYS)
    legf = smoothstep(0.93, 0.80, z) * 0.45
    left = smoothstep(-0.05, 0.05, x)
    w = scale(w, 1 - legf)
    w["thigh.L"] = legf * left
    w["thigh.R"] = legf * (1 - left)
    return w


def arm_param(P, side):
    S_ = S_L * [side, 1, 1]
    D_ = ARM_D * [side, 1, 1]
    return (P - S_) @ D_


S_ELB = float(np.linalg.norm(E_L - S_L))
S_WR = float(np.linalg.norm(W_L - S_L))


def arm_w(P, side):
    sfx = ".L" if side > 0 else ".R"
    s = arm_param(P, side)
    w = chain(s, [("clavicle" + sfx, -0.045), ("upper_arm" + sfx, 0.045), ("upper_arm" + sfx, S_ELB - 0.045),
                  ("forearm" + sfx, S_ELB + 0.040), ("forearm" + sfx, S_WR - 0.055), ("hand" + sfx, S_WR + 0.010)])
    return w


def arm_perp(P, side):
    S_ = S_L * [side, 1, 1]
    D_ = ARM_D * [side, 1, 1]
    d = P - S_
    return np.linalg.norm(d - np.outer(d @ D_, D_), axis=1)


def shoulder_mix(P, base, sleeve=False):
    """Blend trunk weights into the arm chain around the shoulder.  The sleeve goes fully onto the arm
    past the armhole; the torso shell's shoulder cap takes at most ~half of it (the sleeve covers the rest)."""
    out = dict(base)
    for side in (1, -1):
        s = arm_param(P, side)
        lat = smoothstep(0.05, 0.12, P[:, 0] * side)
        near = smoothstep(0.15, 0.10, arm_perp(P, side))
        if sleeve:
            f = smoothstep(-0.07, 0.04, s) * lat
        else:
            f = 0.55 * smoothstep(-0.10, 0.06, s) * lat * near
        clav = 0.55 * smoothstep(0.07, 0.15, P[:, 0] * side) * smoothstep(1.38, 1.46, P[:, 2]) * (1 - f)
        out = scale(out, (1 - f) * (1 - clav))
        out = addw(out, scale(arm_w(P, side), f))
        k = "clavicle" + (".L" if side > 0 else ".R")
        out[k] = out.get(k, 0) + clav
    return out


def leg_w(P, side):
    sfx = ".L" if side > 0 else ".R"
    H_, K_, A_ = HIP_L * [side, 1, 1], KNEE_L * [side, 1, 1], ANK_L * [side, 1, 1]
    dth = nrm(K_ - H_); lth = np.linalg.norm(K_ - H_)
    dsh = nrm(A_ - K_); lsh = np.linalg.norm(A_ - K_)
    t1 = (P - H_) @ dth
    t2 = (P - K_) @ dsh
    s = np.where(t1 < lth, t1, lth + t2)
    w = chain(s, [("pelvis", -0.07), ("thigh" + sfx, 0.035), ("thigh" + sfx, lth - 0.05), ("shin" + sfx, lth + 0.045),
                  ("shin" + sfx, lth + lsh - 0.085), ("foot" + sfx, lth + lsh - 0.005)])
    return w


def foot_w(P, side):
    sfx = ".L" if side > 0 else ".R"
    y, z = P[:, 1], P[:, 2]
    toe = smoothstep(-0.092, -0.128, y)
    shin = smoothstep(0.125, 0.215, z) * 0.85
    return {"foot" + sfx: (1 - toe) * (1 - shin), "toe" + sfx: toe * (1 - shin), "shin" + sfx: shin}


def head_region_w(P, part_attrs, idx):
    """Skin / beanie / goggles: neck -> head by height, jaw, lids and brows from the build attributes."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    zz = z + 0.03 * smoothstep(-0.02, -0.08, y)          # the face sits higher on the chain than the nape
    w = chain(zz, [("spine_03", 1.47), ("neck", 1.535), ("head", 1.605)])
    wj = part_attrs.get("wjaw", np.zeros(len(P)))[idx]
    wh = w["head"] + w["neck"] * 0.3
    jaw = np.minimum(wj, 1.0) * np.clip(wh + w["neck"], 0, 1)
    w = scale(w, 1 - wj)
    w["jaw"] = jaw
    for nm_ in ("wlu", "wll"):
        a = part_attrs.get(nm_, np.zeros(len(P)))[idx]
        bone = "lid_upper" if nm_ == "wlu" else "lid_lower"
        for side, sfx in ((1, ".L"), (-1, ".R")):
            m = a * (np.sign(x) == side)
            w = scale(w, 1 - m)
            w[bone + sfx] = w.get(bone + sfx, 0) + m
    for side, sfx in ((1, ".L"), (-1, ".R")):
        bc = bh("brow" + sfx)
        d = np.sqrt(((x - bc[0]) / 0.021) ** 2 + ((z - bc[2] - 0.001) / 0.013) ** 2)
        m = 0.85 * smoothstep(1.0, 0.25, d) * smoothstep(-0.06, -0.075, y) * (np.sign(x) == side)
        m = m * (1 - part_attrs.get("wlu", np.zeros(len(P)))[idx])
        w = scale(w, 1 - m)
        w["brow" + sfx] = w.get("brow" + sfx, 0) + m
    return w


PART_BY = {}
for p in PARTS:
    PART_BY.setdefault(p.name, []).append(p)
ATTR = {k: np.zeros(NV) for k in ("wjaw", "wlu", "wll", "srcidx", "gpiece")}
for k in ATTR:
    if k in me.attributes:
        a = np.zeros(NV, np.float32); me.attributes[k].data.foreach_get("value", a); ATTR[k] = a.astype(np.float64)

for p in PARTS:
    idx = np.arange(p.off, p.off + len(p.V))
    P = CO[idx]
    nm = p.name
    side = 1 if nm.endswith(".L") else (-1 if nm.endswith(".R") else 0)
    if p.weights is not None:
        put(idx, p.weights)
        continue
    if nm in ("head", "beanie", "goggles", "strap", "mouth", "tooth"):
        w = head_region_w(P, ATTR, idx)
        if nm in ("beanie", "goggles", "strap"):
            w = {"head": np.ones(len(P))}
        elif nm == "tooth":
            w = {"jaw": ATTR["wjaw"][idx], "head": 1 - ATTR["wjaw"][idx]}
        elif nm == "mouth":
            wj = ATTR["wjaw"][idx]
            w = {"jaw": wj, "head": (1 - wj)}
        put(idx, w)
    elif nm in ("brows", "beard", "tufts"):
        pass                                             # copied from the skin below
    elif nm in ("parka", "belt", "buckle", "toggle", "toggle_loop", "cord.L", "cord.R", "cordlock.L", "cordlock.R", "zip_pull"):
        w = shoulder_mix(P, torso_w(P))
        if nm == "parka":                                # standing collar follows the neck a little
            cz = smoothstep(1.49, 1.57, P[:, 2]) * 0.45 * smoothstep(0.10, 0.07, np.hypot(P[:, 0], P[:, 1] - 0.008))
            w = scale(w, 1 - cz); w["neck"] = w.get("neck", 0) + cz
        put(idx, w)
    elif nm.startswith("sleeve"):
        base = torso_w(P)
        put(idx, shoulder_mix(P, base, sleeve=True))
    elif nm.startswith("glove"):
        gp = ATTR["gpiece"][idx]
        sfx = ".L" if side > 0 else ".R"
        w = arm_w(P, side)
        s = arm_param(P, side)
        # gauntlet: forearm -> hand over the wrist; body: hand; fingers: their own chain
        wg = {"forearm" + sfx: smoothstep(S_WR + 0.005, S_WR - 0.07, s), "hand" + sfx: smoothstep(S_WR - 0.07, S_WR + 0.005, s)}
        out = {k: np.zeros(len(P)) for k in list(w) + list(wg)}
        body = (gp == 0)
        for k, v in wg.items():
            out[k] = out.get(k, 0) + np.where(gp == 1, v, 0)
        out["hand" + sfx] = out.get("hand" + sfx, 0) + np.where(body, 1.0, 0)
        for fi, fname in enumerate(FINGER_R):
            m = gp == fi + 2
            if not m.any():
                continue
            hs = [bh(f"{fname}_0{k}{'.L'}") * [side, 1, 1] for k in (1, 2, 3)]
            tip = bt(f"{fname}_03.L") * [side, 1, 1]
            pts = hs + [tip]
            L0 = np.linalg.norm(pts[1] - pts[0]); L1 = np.linalg.norm(pts[2] - pts[1])
            d0 = nrm(pts[1] - pts[0]); d1 = nrm(pts[2] - pts[1]); d2 = nrm(pts[3] - pts[2])
            t0 = (P - pts[0]) @ d0
            t1 = (P - pts[1]) @ d1
            t2 = (P - pts[2]) @ d2
            s_ = np.where(t1 < 0, t0, np.where(t2 < 0, L0 + t1, L0 + L1 + t2))
            cw = chain(s_, [("hand" + sfx, -0.012), (f"{fname}_01{sfx}", 0.006), (f"{fname}_01{sfx}", L0 - 0.004),
                            (f"{fname}_02{sfx}", L0 + 0.005), (f"{fname}_02{sfx}", L0 + L1 - 0.004), (f"{fname}_03{sfx}", L0 + L1 + 0.004)])
            for k, v in cw.items():
                out[k] = out.get(k, 0) + np.where(m, v, 0)
        put(idx, out)
    elif nm.startswith("trouser"):
        put(idx, leg_w(P, side))
    elif nm.startswith("gaiter"):
        w = leg_w(P, side)
        f = smoothstep(0.20, 0.15, P[:, 2]) * 0.3
        w = scale(w, 1 - f); sfx = ".L" if side > 0 else ".R"
        w["foot" + sfx] = w.get("foot" + sfx, 0) + f
        put(idx, w)
    elif nm.startswith("boot") or nm.startswith("sole"):
        put(idx, foot_w(P, side))
    elif nm in ("hood", "ruff"):
        z = P[:, 2]
        w = chain(z, [("hood_02", 1.36), ("hood_01", 1.46)])
        att = smoothstep(1.47, 1.53, z) * smoothstep(0.11, 0.06, np.hypot(P[:, 0], P[:, 1] - 0.01)) * 0.8
        w = scale(w, 1 - att); w["spine_03"] = att * 0.6; w["neck"] = att * 0.4
        put(idx, w)
    elif nm in ("scarf", "scarf_tail"):
        z = P[:, 2]
        w = chain(z, [("spine_02", 1.28), ("spine_03", 1.44), ("neck", 1.575)])
        put(idx, w)
    elif nm in ("sheath", "sheath_loop", "knife"):
        z = P[:, 2]
        f = smoothstep(0.96, 0.82, z) * 0.35
        put(idx, {"pelvis": 1 - f, "thigh.R": f})
    elif nm in ("pouch", "pouch_flap", "pouch_snap"):
        put(idx, {"pelvis": np.full(len(P), 0.85), "thigh.L": np.full(len(P), 0.15)})
    else:
        put(idx, torso_w(P))

# hair shells copy the weights of the skin vertex they grew from
for nm in ("brows", "beard", "tufts"):
    for p in PART_BY.get(nm, []):
        idx = np.arange(p.off, p.off + len(p.V))
        src = ATTR["srcidx"][idx].astype(int) + head_part.off
        WM[idx] = WM[src]

# limit to 4 influences, normalise, write the vertex groups
WM = np.maximum(WM, 0)
order = np.argsort(-WM, axis=1)
keep = np.zeros_like(WM, bool)
np.put_along_axis(keep, order[:, :4], True, axis=1)
WM = np.where(keep & (WM > 0.004), WM, 0)
tot = WM.sum(1, keepdims=True)
bad = (tot[:, 0] <= 1e-6)
if bad.any():
    log("WARNING unweighted verts:", int(bad.sum()))
    WM[bad, BIDX["spine_02"]] = 1.0
    tot = WM.sum(1, keepdims=True)
WM = WM / tot
for bn in DEFORM:
    vg = human.vertex_groups.new(name=bn)
    col = WM[:, BIDX[bn]]
    nz = np.nonzero(col > 0)[0]
    if len(nz) == 0:
        continue
    q = np.round(col[nz] * 1000).astype(int)
    for val in np.unique(q):
        vg.add(nz[q == val].tolist(), float(val) / 1000.0, 'REPLACE')
human.parent = arm
human.matrix_parent_inverse = Matrix()
mod = human.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
log("weights: max influences", int((WM > 0).sum(1).max()), "bones used", int((WM.sum(0) > 0).sum()), "/", len(DEFORM))

# ======================================================================= UVs: mirrored halves
# Only the x > 0 half of the symmetric parts (and all of the asymmetric knife / sheath / pouch / scarf
# end) is unwrapped: organic parts angle-based along the seams laid out by their builders, small hard
# parts by smart projection.  Islands are scale-averaged, then weighted (face, eyes and gloves get more
# texels, the hidden mouth less), packed, and every x < 0 face takes the UVs of its mirror image.
SMALL = {"buckle", "strap", "goggles", "lashes.L", "lashes.R", "tooth", "toggle", "toggle_loop", "cord.L", "cord.R",
         "cordlock.L", "cordlock.R", "zip_pull", "sheath", "sheath_loop", "knife", "pouch", "pouch_flap", "pouch_snap", "belt"}
UV_SCALE = {"head": 1.9, "ear.L": 1.5, "ear.R": 1.5, "eye.L": 2.6, "eye.R": 2.6, "mouth": 0.5, "tooth": 0.7, "brows": 1.9,
            "beard": 1.5, "tufts": 1.3, "lashes.L": 1.5, "lashes.R": 1.5, "glove.L": 1.25, "glove.R": 1.25, "sole.L": 0.8,
            "sole.R": 0.8, "goggles": 1.3, "knife": 1.4, "buckle": 1.4}
PART_OF = np.zeros(NV, np.int32)
for k, p in enumerate(PARTS):
    PART_OF[p.off:p.off + len(p.V)] = k
SYMM = np.zeros(NV, np.float32); me.attributes["symm"].data.foreach_get("value", SYMM)
nf = len(me.polygons)
fc = np.zeros(nf * 3, np.float32); me.polygons.foreach_get("center", fc); fc = fc.reshape(-1, 3)
lstart = np.zeros(nf, np.int32); me.polygons.foreach_get("loop_start", lstart)
lverts = np.zeros(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lverts)
fpart = PART_OF[lverts[lstart]]
fsymm = SYMM[lverts[lstart]]
is_small = np.array([PARTS[k].name in SMALL for k in range(len(PARTS))])[fpart]
unwrap_f = (fsymm > 1.5) | (fc[:, 0] > 0)
me.uv_layers.new(name="UVMap")


def select_faces(mask):
    me.polygons.foreach_set("select", mask.tolist())
    me.update()


for o in bpy.context.view_layer.objects:
    o.select_set(o == human)
bpy.context.view_layer.objects.active = human
scene.tool_settings.use_uv_select_sync = True
select_faces(unwrap_f & is_small)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0, correct_aspect=True, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')
select_faces(unwrap_f & ~is_small)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
bpy.ops.object.mode_set(mode='OBJECT')
select_faces(unwrap_f)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.uv.average_islands_scale()
bpy.ops.object.mode_set(mode='OBJECT')
uv = np.zeros(len(me.loops) * 2, np.float32); me.uv_layers[0].data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
fl_part = np.repeat(fpart, np.diff(np.append(lstart, len(me.loops))))
fl_unw = np.repeat(unwrap_f, np.diff(np.append(lstart, len(me.loops))))
for k, p in enumerate(PARTS):
    f_ = UV_SCALE.get(p.name, 1.0)
    if f_ == 1.0:
        continue
    m = (fl_part == k) & fl_unw
    if m.any():
        c = uv[m].mean(0)
        uv[m] = c + (uv[m] - c) * f_
me.uv_layers[0].data.foreach_set("uv", uv.ravel())
select_faces(unwrap_f)
bpy.ops.object.mode_set(mode='EDIT')
try:
    bpy.ops.uv.pack_islands(rotate=True, margin=0.0011, shape_method='CONCAVE')
except TypeError:
    bpy.ops.uv.pack_islands(rotate=True, margin=0.0011)
bpy.ops.object.mode_set(mode='OBJECT')
log("uv: unwrapped + packed", int(unwrap_f.sum()), "faces")

# mirror the x > 0 UVs onto the x < 0 faces of the symmetric parts
uv = np.zeros(len(me.loops) * 2, np.float32); me.uv_layers[0].data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
src_f = np.nonzero(unwrap_f & (fsymm < 1.5))[0]
kd = KDTree(len(src_f))
for i_, f in enumerate(src_f):
    kd.insert(fc[f], i_)
kd.balance()
lend = np.append(lstart[1:], len(me.loops))
nm_ = 0
for f in np.nonzero(~unwrap_f)[0]:
    c = fc[f]
    g_ = src_f[kd.find((-c[0], c[1], c[2]))[1]]
    gl = np.arange(lstart[g_], lend[g_])
    gv = CO[lverts[gl]]
    for l_ in range(lstart[f], lend[f]):
        pm = CO[lverts[l_]] * [-1, 1, 1]
        uv[l_] = uv[gl[np.argmin(((gv - pm) ** 2).sum(1))]]
    nm_ += 1
me.uv_layers[0].data.foreach_set("uv", uv.ravel())
log("uv: mirrored", nm_, "faces")


# ======================================================================= preview material (geo stage)
PART_COLORS = {SKIN: (0.62, 0.42, 0.34), EYE: (0.9, 0.9, 0.9), MOUTH: (0.5, 0.15, 0.15), TEETH: (0.9, 0.88, 0.8),
               HAIR: (0.18, 0.12, 0.08), BEANIE: (0.15, 0.2, 0.18), GOGGLE: (0.05, 0.05, 0.05), LENS: (0.8, 0.45, 0.1),
               PARKA: (0.45, 0.07, 0.05), FUR: (0.45, 0.38, 0.30), HOOD: (0.42, 0.07, 0.05), SCARF: (0.75, 0.70, 0.60),
               GLOVE: (0.10, 0.09, 0.08), TROUSERS: (0.16, 0.17, 0.18), GAITER: (0.07, 0.07, 0.08), BOOT: (0.30, 0.18, 0.10),
               SOLE: (0.04, 0.04, 0.04), BELT: (0.25, 0.14, 0.07), METAL: (0.6, 0.6, 0.62), SHEATH: (0.40, 0.26, 0.14),
               KNIFE: (0.30, 0.22, 0.14), POUCH: (0.30, 0.30, 0.22), TOGGLE: (0.35, 0.25, 0.15), CORD: (0.1, 0.1, 0.1),
               LASH: (0.05, 0.03, 0.02)}


def preview_material():
    mat = bpy.data.materials.new("Human_Outfit")
    nt = mat.node_tree
    bs = nt.nodes["Principled BSDF"]
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "part"
    mp = nt.nodes.new("ShaderNodeMath"); mp.operation = 'DIVIDE'; mp.inputs[1].default_value = 32.0
    nt.links.new(at.outputs["Fac"], mp.inputs[0])
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = 'CONSTANT'
    el = cr.color_ramp.elements
    keys = sorted(PART_COLORS)
    el[0].position = 0.0; el[0].color = (*PART_COLORS[keys[0]], 1)
    el[1].position = (keys[1] - 0.25) / 32; el[1].color = (*PART_COLORS[keys[1]], 1)
    for k in keys[2:]:
        e = el.new((k - 0.25) / 32); e.color = (*PART_COLORS[k], 1)
    nt.links.new(mp.outputs[0], cr.inputs[0])
    nt.links.new(cr.outputs[0], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.6
    return mat


if STAGE == "geo":
    me.materials.append(preview_material())
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.environ.get("HUMAN_SCRATCH", DIR), "Human_geo.blend"))
    log("geo stage saved")
    sys.exit(0) if bpy.app.background else None

# @@TEXTURES@@

# @@FINAL@@
