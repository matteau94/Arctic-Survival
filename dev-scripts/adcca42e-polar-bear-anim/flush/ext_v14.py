# Flush lips: the upper lip no longer juts out over the lower one.
#
# The muzzle outline around the lips is described as a "stadium": half an ellipse at the front
# (centre y=-7.3, half-width 0.40, reach 0.56) and straight sides behind y=-7.3.  Every vertex
# gets a station s along that outline (0 = midline front, 90 = y -7.3, then +1 per 0.01 cm back)
# and an outward horizontal normal n.  Cross-sections perpendicular to the outline are cut
# through the current mesh at stations every 5 deg / 0.05 cm; in each one the outermost
# upper-lip surface near the lip line and the outermost lower-lip surface just below it are
# measured.  Their difference is the overhang G(s) (before: ~0.22 cm at the front, 0.14 at
# y -7.58, 0.08 at y -7.3, ~0.03 from y -7.1 back).
# Fix: the upper lip's lower rim is drawn in along -n by LF_UP*G and the lower lip (with the
# chin below it) is brought out along +n by the rest, so both surfaces meet flush.  The move
# fades up over the upper lip (nose pad untouched), down over the chin, and inward with depth,
# so the mouth interior moves with its own lip.  The top of the lower lip, which sits tucked
# up behind the upper-lip rim, moves with the upper lip so the two never pass through each
# other.  Horizontal moves only: line_z and the painted lip band stay valid.
LF_C, LF_A, LF_B = -7.3, 0.40, 0.56
LF_UP = 0.45          # share of the overhang removed by pulling the upper lip in
LF_MARGIN = 0.03      # lower lip ends this far behind the upper rim (flush, never in front)
LF_WALL = 0.03        # where the upper rim is bevelled in, the lower lip follows the wall above, minus this
LF_SMOOTH = 4
LF_FAIR = 8           # Taubin iterations over the moved lower lip
LF_PASSES = 3         # measure -> move, repeated (the smoothing leaves part of the gap each pass)
LF_TUCK = (-0.045, 0.0)   # (unused when LF_USE_TUCK is False)
LF_USE_TUCK = False
LF_NOTCH = 0.0        # lower-lip edge right at the seam is held this far behind the upper rim (V crease)
LF_CHIN = -0.55       # push fades out down the chin by this dz
LF_LIFT = 0.5         # front: upper-lip hem hanging below the lip line is raised by this fraction
LF_RAISE_BAND = (-0.22, 0.03)   # dz range of the lower lip that is remapped upward
LF_RAISE_P = 0.45     # remap exponent (<1 raises the top rows most)


def _lf_stadium(np, x, y):
    ax = np.abs(x); sx = np.where(x < 0, -1.0, 1.0)
    fr = y < LF_C
    u = ax / LF_A; v = -(y - LF_C) / LF_B
    phi = np.arctan2(u, np.where(fr, v, 0.0))
    rho = np.hypot(u, np.where(fr, v, 0.0))
    gx = ax / LF_A ** 2; gy = (y - LF_C) / LF_B ** 2
    gn = np.maximum(np.hypot(gx, np.where(fr, gy, 0.0)), 1e-9)
    s = np.where(fr, np.degrees(phi), 90.0 + (y - LF_C) * 100.0)
    d = np.where(fr, (rho - 1) * np.maximum(rho, 1e-9) / gn, ax - LF_A)
    nx = np.where(fr, np.sin(phi) / LF_A, 1.0)
    ny = np.where(fr, -np.cos(phi) / LF_B, 0.0)
    nn = np.hypot(nx, ny)
    return s, d, sx * nx / nn, ny / nn


def _lf_station(math, s):
    if s <= 90:
        f = math.radians(s)
        p = (LF_A * math.sin(f), LF_C - LF_B * math.cos(f))
        n = (math.sin(f) / LF_A, -math.cos(f) / LF_B)
        k = math.hypot(*n); n = (n[0] / k, n[1] / k)
    else:
        p = (LF_A, LF_C + (s - 90) / 100.0); n = (1.0, 0.0)
    return p, n


def _lf_faces(g):
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
    return g["_CR_FACES"]


def lf_overhang(g, Q, verbose=False, want_u=False):
    """overhang G at each station, from cross-sections of the mesh Q"""
    np = g["np"]; math = g["math"]; line_z = g["line_z"]; J = g["JWu"]
    F = _lf_faces(g)
    cen = Q[F].mean(1)
    F = F[(cen[:, 0] > -0.05) & (cen[:, 1] < -6.5) & (cen[:, 1] > -8.3) & (np.abs(cen[:, 2] - 6.85) < 0.7)]
    ST = list(range(0, 91, 5)) + list(range(95, 136, 5))
    G = []; UU = []
    for s in ST:
        (px, py), (nx, ny) = _lf_station(math, s)
        tx, ty = -ny, nx
        sd = (Q[:, 0] - px) * tx + (Q[:, 1] - py) * ty
        pts = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ia, ib = F[:, a], F[:, b]
            m = (sd[ia] > 0) != (sd[ib] > 0)
            ia, ib = ia[m], ib[m]
            t = (sd[ia] / (sd[ia] - sd[ib]))[:, None]
            P = Q[ia] + (Q[ib] - Q[ia]) * t
            w = J[ia] + (J[ib] - J[ia]) * t[:, 0]
            pts.append(np.column_stack([P, w]))
        P = np.concatenate(pts)
        dd = (P[:, 0] - px) * nx + (P[:, 1] - py) * ny
        al = np.abs((P[:, 0] - px) * tx + (P[:, 1] - py) * ty)
        dz = P[:, 2] - np.array([line_z(v) for v in P[:, 1]])
        ok = dd > -0.5
        up = ok & (P[:, 3] < 0.5) & (dz > -0.10) & (dz < 0.10)
        up2 = ok & (P[:, 3] < 0.5) & (dz > -0.10) & (dz < 0.20)   # rim bevelled in: use the wall above
        lo = ok & (P[:, 3] >= 0.5) & (dz > -0.25) & (dz < -0.02)
        u = dd[up].max() if up.any() else np.nan
        if up2.any() and s >= 45:                               # (front: the wall slopes out to the nose)
            u = np.nanmax([u, dd[up2].max() - LF_WALL])
        l = dd[lo].max() if lo.any() else np.nan
        G.append(u - l); UU.append(u)
        if verbose:
            print("[mouth] lipflush s=%3d  upper %.3f lower %.3f  overhang %.3f" % (s, u, l, u - l))
    G = np.nan_to_num(np.array(G), nan=0.0)
    if want_u:
        return np.array(ST, dtype=float), G, np.array(UU)
    return np.array(ST, dtype=float), G


def _lf_pass(g, verbose):
    np = g["np"]; ramp = g["ramp"]; line_z = g["line_z"]
    Q = g["Q"]; J = g["JWu"]; nbr = g["nbr"]; U = g["U"]
    ST, G, UU = lf_overhang(g, Q, verbose=verbose, want_u=True)
    G = np.maximum(G - LF_MARGIN, 0.0)
    Gc = G.copy()                                        # fill single-station dips (section noise)
    for k in range(1, len(G) - 1):
        Gc[k] = max(G[k], min(G[max(0, k - 2):k].max(), G[k + 1:k + 3].max()))
    G = Gc
    for _ in range(2):                                   # smooth along the outline
        G = np.concatenate([[G[0]], 0.25 * G[:-2] + 0.5 * G[1:-1] + 0.25 * G[2:], [G[-1]]])
    G *= 1 - np.array([ramp(v, 110, 125) for v in ST])   # leave the mouth corner alone
    x, y, z = Q[:, 0], Q[:, 1], Q[:, 2]
    s, d, nx, ny = _lf_stadium(np, x, y)
    dz = z - np.array([line_z(v) for v in y])
    reg = (y < -6.5) & (y > -8.3) & (np.abs(x) < 1.0) & (dz < 0.4) & (dz > -0.9) & (d > -0.8)
    Gi = np.interp(s, ST, G)
    rp = lambda v, a, b: np.clip((v - a) / (b - a), 0, 1) ** 2 * (3 - 2 * np.clip((v - a) / (b - a), 0, 1))
    wd = rp(d, -0.75, -0.4)
    pull = -LF_UP * Gi * (1 - rp(dz, 0.06, 0.3))
    c = rp(dz, LF_TUCK[0], LF_TUCK[1]) * LF_USE_TUCK                   # lower-lip top tucked behind the rim
    push = (1 - LF_UP) * Gi * rp(dz, LF_CHIN, -0.08)
    amt = np.where(J < 0.5, pull, (1 - c) * push + c * pull) * wd * reg
    D = np.zeros((U, 3))
    D[:, 0] = amt * nx; D[:, 1] = amt * ny
    act = np.nonzero(np.abs(amt) > 0)[0]
    region = set(act.tolist())
    for i in act:
        region.update(nbr[i].tolist())
    region = np.array(sorted(region))
    up = J < 0.5
    for _ in range(LF_SMOOTH):
        N = D.copy()
        for i in region:
            nb = [j for j in nbr[i] if up[j] == up[i]]
            if nb:
                N[i] = 0.5 * D[i] + 0.5 * D[nb].mean(0)
        D = N
    Q += D
    UU = np.nan_to_num(UU, nan=9.0); Uc = UU.copy()          # same dip filling for the rim
    for k in range(1, len(UU) - 1):
        Uc[k] = max(UU[k], min(UU[max(0, k - 2):k].max(), UU[k + 1:k + 3].max()))
    _lf_clamp(g, ST, Uc - LF_UP * G, D)
    print("[mouth] lipflush: %d vertices moved, max %.3f cm" % ((np.abs(D).sum(1) > 1e-5).sum(),
                                                            np.linalg.norm(D, axis=1).max()))


def _lf_clamp(g, ST, UR, D):
    """The lower lip never ends up in front of the upper rim: lower-lip skin near the seam is
    held at (upper rim - margin), and right at the seam a little further back (lower half of
    the V crease)."""
    np = g["np"]; line_z = g["line_z"]; Q = g["Q"]; J = g["JWu"]
    x, y, z = Q[:, 0], Q[:, 1], Q[:, 2]
    s, d, nx, ny = _lf_stadium(np, x, y)
    dz = z - np.array([line_z(v) for v in y])
    lim = np.interp(s, ST, UR) - LF_MARGIN - LF_NOTCH * np.exp(-(dz / 0.03) ** 2)
    rp = lambda v, a, b: np.clip((v - a) / (b - a), 0, 1) ** 2 * (3 - 2 * np.clip((v - a) / (b - a), 0, 1))
    w = rp(dz, -0.22, -0.1) * (J >= 0.5) * (y < -6.5) * (s < 125) * (dz < 0.1) * (d > -0.45)
    pushed = np.maximum(D[:, 0] * nx + D[:, 1] * ny, 0)       # only undo this pass's push
    over = np.minimum(np.maximum(d - lim, 0), pushed) * w
    Q[:, 0] -= over * nx
    Q[:, 1] -= over * ny


def _lf_lift(g):
    """At the front the upper-lip hem hangs up to ~0.08 cm below the lip line, in front of the
    lower lip's rim. Raise it back up to the line (smoothly) so the lower lip can come forward
    underneath it instead of through it."""
    np = g["np"]; line_z = g["line_z"]; Q = g["Q"]; J = g["JWu"]; nbr = g["nbr"]; ramp = g["ramp"]
    x, y, z = Q[:, 0], Q[:, 1], Q[:, 2]
    s, d, _, _ = _lf_stadium(np, x, y)
    dz = z - np.array([line_z(v) for v in y])
    sel = (J < 0.5) & (dz < 0) & (dz > -0.14) & (d > -0.45) & (y < -6.9) & (np.abs(x) < 0.8)
    dzl = np.zeros(g["U"])
    for i in np.nonzero(sel)[0]:
        w = LF_LIFT * (1 - ramp(s[i], 55, 85)) * ramp(d[i], -0.45, -0.25)
        dzl[i] = -dz[i] * w
    # a little of the lift carries into the upper-lip skin just above, so nothing folds
    for i in np.nonzero(dzl)[0]:
        for j in nbr[i]:
            if J[j] < 0.5 and dzl[j] == 0 and dz[j] >= 0:
                dzl[j] = max(dzl[j], 0.3 * dzl[i])
    Q[:, 2] += dzl
    print("[mouth] lipflush: hem lifted, %d vertices, max %.3f cm" % ((dzl > 0).sum(), dzl.max()))


def _lf_raise(g):
    """The lower lip's outer top edge sits up to ~0.07 cm below the lip line (it used to hide
    under the overhang). Once it is brought forward its flat top would show as a ledge, so the
    top of the lower lip is stretched up (monotone remap of dz, top rows moved most) until its
    outer edge meets the upper lip at the line."""
    np = g["np"]; line_z = g["line_z"]; Q = g["Q"]; J = g["JWu"]; ramp = g["ramp"]
    x, y, z = Q[:, 0], Q[:, 1], Q[:, 2]
    s, d, _, _ = _lf_stadium(np, x, y)
    dz = z - np.array([line_z(v) for v in y])
    lo, hi = LF_RAISE_BAND
    sel = (J >= 0.5) & (dz > lo) & (dz < hi) & (d > -0.5) & (y < -6.6) & (np.abs(x) < 0.9)
    n = 0
    for i in np.nonzero(sel)[0]:
        w = (1 - ramp(s[i], 95, 120)) * ramp(d[i], -0.5, -0.3)
        t = (dz[i] - lo) / (hi - lo)
        Q[i, 2] += w * ((lo + (hi - lo) * t ** LF_RAISE_P) - dz[i])
        n += w > 0
    print("[mouth] lipflush: lower-lip top raised, %d vertices" % n)


def _lf_fair(g):
    """Taubin-relax (no shrinkage) the outer skin of the moved lower lip so the coarse facets
    left by the move don't catch the light as dark notches. The seam rows stay put."""
    np = g["np"]; line_z = g["line_z"]; Q = g["Q"]; J = g["JWu"]; nbr = g["nbr"]; ramp = g["ramp"]
    x, y, z = Q[:, 0], Q[:, 1], Q[:, 2]
    s, d, _, _ = _lf_stadium(np, x, y)
    dz = z - np.array([line_z(v) for v in y])
    m = np.zeros(g["U"])
    sel = np.nonzero((J >= 0.5) & (dz < -0.02) & (dz > -0.5) & (d > -0.35) & (y < -6.8))[0]
    for i in sel:
        m[i] = ramp(-dz[i], 0.02, 0.07) * (1 - ramp(-dz[i], 0.35, 0.5)) * (1 - ramp(s[i], 90, 110)) \
            * ramp(d[i], -0.35, -0.25)
    act = np.nonzero(m > 0.01)[0]
    for _ in range(LF_FAIR):
        for f in (0.5, -0.53):
            new = Q[act].copy()
            for k, i in enumerate(act):
                nb = nbr[i]
                if len(nb):
                    new[k] = Q[i] + f * m[i] * (Q[nb].mean(0) - Q[i])
            Q[act] = new
    print("[mouth] lipflush: lower lip faired, %d vertices" % len(act))


def lipflush_shape(g):
    _lf_lift(g)
    _lf_raise(g)
    for k in range(LF_PASSES):
        _lf_pass(g, k == 0)
        if k == 0:
            _lf_fair(g)
    lf_overhang(g, g["Q"], verbose=True)


HOOKS["shape"].append(lipflush_shape)
