# Crisp lip crease: the upper and lower lips each roll into the seam with a small rounded rim,
# and the seam itself is cut in as a narrow V, so the mouth reads as two surfaces meeting at a
# clean edge instead of one blurry shaded fold.  Geometry only (the dark lip colour is separate).
CR_G_UP = 0.075      # upper-lip seam edge pushed inward, cm
CR_G_LO = 0.090      # lower-lip seam edge pushed inward (slightly sharper crease), cm
CR_B_UP = 0.008      # upper-lip rim bulge (kept tiny: the upper lip must not overhang)
CR_B_LO = 0.022      # lower-lip rim bulge
CR_RIM = 0.045       # rim row distance from the seam, cm
CR_RIM_W = 0.035     # rim bulge half-width
CR_CORNER = 0.014    # half-width of the seam band that takes the inward cut
CR_PULL = 0.7        # how strongly the first wall row is drawn toward the seam (0 = off)
CR_PLATEAU = 0.08     # seam-sheet depth that moves rigidly with the cut (no folding)
CR_SNAP_SIG = 0.045
CR_GROOVE = 0.030


def _crease_line(g):
    g["SNAP_SIG"] = CR_SNAP_SIG
    g["GROOVE_DEPTH"] = CR_GROOVE


def _crease_normals(g, Q):
    np = g["np"]; me = g["me"]; inv = g["inv"]
    if "_CR_FACES" not in g:
        lp = np.zeros(len(me.data.loops), dtype=np.int64); me.data.loops.foreach_get("vertex_index", lp)
        ls = np.zeros(len(me.data.polygons), dtype=np.int64); me.data.polygons.foreach_get("loop_start", ls)
        lt = np.zeros(len(me.data.polygons), dtype=np.int64); me.data.polygons.foreach_get("loop_total", lt)
        lp = inv[lp]
        tris = []
        for s, t in zip(ls, lt):
            for k in range(1, t - 1):
                tris.append((lp[s], lp[s + k], lp[s + k + 1]))
        g["_CR_FACES"] = np.array(tris, dtype=np.int64)
    F = g["_CR_FACES"]
    fn = np.cross(Q[F[:, 1]] - Q[F[:, 0]], Q[F[:, 2]] - Q[F[:, 0]])
    N = np.zeros_like(Q)
    for k in range(3):
        np.add.at(N, F[:, k], fn)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


def _crease_shape(g):
    np = g["np"]; math = g["math"]; ramp = g["ramp"]; line_z = g["line_z"]
    Q = g["Q"]; J = g["JWu"]
    x, y, z = Q[:, 0], Q[:, 1], Q[:, 2]
    lz = np.array([line_z(v) for v in y])
    D = z - lz
    fy = np.array([ramp(-v, 6.62, 6.8) * (1 - ramp(-v, 7.86, 7.95)) for v in y])
    fx = np.array([1 - ramp(abs(v), 0.9, 1.1) for v in x])
    band = np.nonzero((y > -7.95) & (y < -6.6) & (np.abs(x) < 1.1) & (np.abs(D) < 0.3) & (fy * fx > 0))[0]
    N = _crease_normals(g, Q)
    P = Q[band, :2]; Nb = N[band]
    rad = P - np.array([0.0, -7.0]); rad /= np.maximum(np.linalg.norm(rad, axis=1, keepdims=True), 1e-9)
    nh = Nb[:, :2]
    wall = (np.abs(Nb[:, 2]) < 0.8) & ((nh * rad).sum(1) > 0.3)
    # smoothed horizontal outward direction of the lip surface
    diff = P[:, None, :] - P[None, wall, :]
    w = np.exp(-(diff ** 2).sum(-1) / 0.12 ** 2) * np.exp(-((D[band][:, None] - D[band][None, wall]) / 0.15) ** 2)
    o = w @ nh[wall] + 1e-6 * rad
    o /= np.maximum(np.linalg.norm(o, axis=1, keepdims=True), 1e-9)
    # depth behind the outer surface of the same lip (keeps teeth / tongue / sheet interior still)
    up = J[band] < 0.5
    depth = np.zeros(len(band))
    near = np.abs(D[band]) < 0.2
    for k in range(len(band)):
        same = near & (up == up[k])
        rel = P[same] - P[k]
        a = rel @ o[k]
        perp = np.abs(rel @ np.array([-o[k][1], o[k][0]]))
        a = a[perp < 0.06]
        depth[k] = max(0.0, a.max()) if len(a) else 0.0
    outer = np.exp(-(np.maximum(depth - CR_PLATEAU, 0) / 0.06) ** 2)
    Db = D[band]; ad = np.abs(Db)
    facing = 1 - ramp_np(np, o[:, 1], -0.1, 0.25)     # lip surfaces face sideways / forward, never back
    wgt = fy[band] * fx[band] * outer * facing
    s = np.where(up, 1.0, -1.0)
    G = np.where(up, CR_G_UP, CR_G_LO); B = np.where(up, CR_B_UP, CR_B_LO)
    # only surface on the lip's own side of the seam (upper above, lower below) takes the rim
    own = (s * Db) > -0.004
    cut = np.exp(-(Db / CR_CORNER) ** 2)
    rim = np.exp(-((ad - CR_RIM) / CR_RIM_W) ** 2) * (1 - cut) * own
    dh = (-G * cut + B * rim) * wgt
    Q[band, 0] += dh * o[:, 0]
    Q[band, 1] += dh * o[:, 1]
    # draw the first wall row toward the seam so the crease faces are narrow and steep
    t = s * Db
    pullz = np.where((t > 0.03) & (t < 0.2) & own,
                     CR_PULL * (t - 0.03) * (1 - ramp_np(np, t, 0.1, 0.2)), 0.0) * wgt
    Q[band, 2] -= s * pullz
    g["_CR_DBG"] = (band, depth, o)


def ramp_np(np, v, a, b):
    t = np.clip((v - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


HOOKS["line"].append(_crease_line)
