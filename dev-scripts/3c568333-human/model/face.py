"""Head field: landmark slices -> radial table, plus local facial features (prototype)."""
import numpy as np
from sdf import *

EYE = A((0.032, -0.072, 1.667)); RE = 0.0120; LID = 0.0016
C = A((0.0, -0.004, 1.652))
Y_AX = -0.005

# horizontal contours (x >= 0 half, front midline -> back midline), bare skin without nose / lips / eyes
SLICES = {
    1.440: [(0, -0.056), (0.040, -0.043), (0.058, -0.004), (0.052, 0.040), (0.030, 0.060), (0, 0.066)],
    1.500: [(0, -0.055), (0.040, -0.043), (0.057, -0.004), (0.052, 0.040), (0.030, 0.058), (0, 0.064)],
    1.528: [(0, -0.060), (0.040, -0.046), (0.057, -0.004), (0.052, 0.040), (0.030, 0.059), (0, 0.065)],
    1.540: [(0, -0.082), (0.020, -0.078), (0.036, -0.062), (0.050, -0.032), (0.057, -0.002), (0.052, 0.040), (0.030, 0.061), (0, 0.067)],
    1.548: [(0, -0.094), (0.013, -0.091), (0.027, -0.082), (0.042, -0.064), (0.055, -0.034), (0.060, -0.004), (0.054, 0.038), (0.031, 0.062), (0, 0.068)],
    1.556: [(0, -0.0995), (0.012, -0.097), (0.025, -0.089), (0.040, -0.073), (0.053, -0.046), (0.060, -0.016), (0.062, 0.006), (0.055, 0.036), (0.032, 0.063), (0, 0.069)],
    1.578: [(0, -0.0935), (0.014, -0.0925), (0.027, -0.086), (0.042, -0.072), (0.054, -0.048), (0.061, -0.016), (0.0630, 0.006), (0.057, 0.032), (0.036, 0.063), (0, 0.071)],
    1.600: [(0, -0.0968), (0.012, -0.0955), (0.025, -0.090), (0.038, -0.079), (0.050, -0.061), (0.059, -0.034), (0.064, -0.006), (0.064, 0.020), (0.057, 0.046), (0.036, 0.071), (0, 0.078)],
    1.620: [(0, -0.0998), (0.014, -0.0975), (0.027, -0.0915), (0.041, -0.082), (0.055, -0.065), (0.065, -0.039), (0.068, -0.010), (0.068, 0.020), (0.063, 0.051), (0.041, 0.081), (0, 0.089)],
    1.645: [(0, -0.0975), (0.014, -0.0955), (0.028, -0.089), (0.042, -0.081), (0.055, -0.067), (0.066, -0.043), (0.071, -0.015), (0.072, 0.020), (0.067, 0.056), (0.046, 0.086), (0, 0.095)],
    1.667: [(0, -0.0965), (0.012, -0.0935), (0.020, -0.085), (0.032, -0.081), (0.046, -0.077), (0.057, -0.063), (0.066, -0.043), (0.072, -0.015), (0.074, 0.020), (0.070, 0.056), (0.049, 0.088), (0, 0.098)],
    1.690: [(0, -0.0975), (0.015, -0.095), (0.030, -0.089), (0.045, -0.083), (0.057, -0.070), (0.067, -0.048), (0.073, -0.018), (0.0755, 0.020), (0.072, 0.058), (0.050, 0.090), (0, 0.100)],
    1.702: [(0, -0.1003), (0.015, -0.0990), (0.030, -0.0950), (0.044, -0.0880), (0.056, -0.0750), (0.066, -0.054), (0.073, -0.025), (0.0765, 0.015), (0.0735, 0.055), (0.052, 0.090), (0, 0.100)],
    1.725: [(0, -0.0970), (0.020, -0.0950), (0.040, -0.0870), (0.056, -0.0720), (0.068, -0.050), (0.075, -0.020), (0.077, 0.015), (0.074, 0.055), (0.052, 0.089), (0, 0.099)],
}
Z_TOP_REF, Z_TOP = 1.725, 1.790
NT = 721
TH = np.linspace(0, np.pi, NT)


def contour_r(pts):
    """Polar radius (about (0, Y_AX)) of a smooth closed contour through the landmarks, sampled at TH."""
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
    return np.interp(TH, th[sel][o], r[sel][o])


ZS = sorted(SLICES)
RS = np.array([contour_r(SLICES[z]) for z in ZS])
ZT = np.arange(1.40, Z_TOP + 0.0005, 0.0005)
RT = np.empty((len(ZT), NT))
for j in range(NT):
    keys = list(zip(ZS, RS[:, j]))
    RT[:, j] = np.array([hermite(keys, z) for z in ZT])
_ref = RS[ZS.index(Z_TOP_REF)]
for i, z in enumerate(ZT):
    if z > Z_TOP_REF:
        f = np.sqrt(max(1 - ((z - 1.700) / (Z_TOP - 1.700)) ** 2, 0)) / np.sqrt(1 - ((Z_TOP_REF - 1.700) / (Z_TOP - 1.700)) ** 2)
        RT[i] = _ref * f


def r_base(th, z):
    zi = np.clip((z - ZT[0]) / 0.0005, 0, len(ZT) - 1.001)
    ti = np.clip(th / np.pi * (NT - 1), 0, NT - 1.001)
    z0 = zi.astype(int); t0 = ti.astype(int)
    fz, ft = zi - z0, ti - t0
    a = RT[z0, t0] * (1 - ft) + RT[z0, t0 + 1] * ft
    b = RT[z0 + 1, t0] * (1 - ft) + RT[z0 + 1, t0 + 1] * ft
    return a * (1 - fz) + b * fz


NOSE_P = [(1.612, 0.0), (1.6165, 0.004), (1.620, 0.0175), (1.6235, 0.0255), (1.6285, 0.0300), (1.634, 0.0292),
          (1.642, 0.0240), (1.652, 0.0175), (1.662, 0.0105), (1.671, 0.0050), (1.678, 0.0018), (1.685, 0.0)]
NOSE_W = [(1.612, 0.006), (1.620, 0.0105), (1.628, 0.0145), (1.636, 0.0125), (1.650, 0.0100), (1.668, 0.0095),
          (1.685, 0.0105), (1.692, 0.012)]
MW = 0.0240
Z_ST = 1.5982


def ki(keys, x):
    return np.interp(x, [k[0] for k in keys], [k[1] for k in keys])


def ell2(ax, z, cx, cz, rx, rz):
    return ((ax - cx) / rx) ** 2 + ((z - cz) / rz) ** 2


def lip_lines(ax):
    xm = np.clip(ax / MW, 0, 1)
    zst = Z_ST + 0.0014 * xm ** 2
    up_h = 0.0090 * np.clip(1 - xm ** 1.7, 0, 1) ** 0.55 - 0.0006 * g(xm, 0, 0.10)
    lo_h = 0.0112 * np.clip(1 - xm ** 2.0, 0, 1) ** 0.60
    return zst, zst + up_h, zst - lo_h


def features(ax, z):
    """Outward offsets (m) of the facial features over the base slices, as a function of (|x|, z)."""
    D = np.zeros_like(ax)
    D += 0.0025 * g(z, 1.700, 0.007) * smoothstep(0.060, 0.030, ax) * (0.5 + 0.5 * g(ax, 0.030, 0.018))   # brow ridge
    D -= 0.0020 * g(z, 1.689, 0.004) * g(ax, 0.031, 0.011)                                                   # lid crease hollow
    D += 0.0030 * np.exp(-ell2(ax, z, 0.053, 1.645, 0.016, 0.011))                                           # cheekbone
    D -= 0.0012 * np.exp(-ell2(ax, z, 0.050, 1.622, 0.012, 0.010))                                           # sub-malar
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
    D += 0.0036 * tap ** 0.6 * up * (z >= zst - 1e-5)
    D += 0.0050 * tap ** 0.6 * lo * (z < zst + 1e-5)
    D -= 0.0015 * np.exp(-ell2(ax, z, 0.0265, 1.5995, 0.004, 0.005))                                        # modiolus
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


ZMAP_A = [1.30, 1.553, 1.601, 1.622, 1.665, 1.90]
ZMAP_D = [1.30, 1.543, 1.5982, 1.617, 1.665, 1.90]


def zdes(z):
    return np.interp(z, ZMAP_A, ZMAP_D)


def zact(zd):
    return np.interp(zd, ZMAP_D, ZMAP_A)


def F_head(P):
    ax = np.abs(P[:, 0]); y = P[:, 1]; z = zdes(P[:, 2])
    th = np.arctan2(ax, -(y - Y_AX))
    rho = np.hypot(ax, y - Y_AX)
    front = np.clip(np.cos(th), 0.25, 1.0)
    r = r_base(th, z) + features(ax, z) / front * smoothstep(1.1, 0.8, th)
    d = rho - r
    Q = np.stack([ax, y, P[:, 2]], -1)
    d = smin(d, sd_sph(Q, EYE, RE + LID), 0.0025)
    return d
