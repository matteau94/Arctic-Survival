# Philtrum: a short, shallow vertical groove at x=0 from the bottom of the black nose pad
# down to the upper lip, with dark (black-skinned) lip skin in and around it.
# Measured on the baked mesh: the pad's black texture ends at z~7.21 (y~-7.99); the bare
# upper-lip strip below it runs z 7.17 -> 6.95 (y -7.97 -> -7.88) and meets the lip line
# at z~6.90-6.95. Only ~2 vertex rows span it, so the groove is shaped per vertex with a
# narrow Gaussian in x and then its offset is smoothed over the neighbours.
PH_TOP = 7.24         # groove fades out just inside the bottom edge of the nose pad
PH_DEPTH = 0.065      # how far the groove floor is pushed back (+y), cm
PH_SIG = 0.045        # half-width of the groove (Gaussian sigma in x), cm


def _ph_weight(g, x, y, z, sig):
    ramp = g["ramp"]
    if y > -7.7 or abs(x) > 0.35:
        return 0.0
    zl = g["line_z"](y)
    fz = ramp(z, zl - 0.03, zl + 0.045) * (1 - ramp(z, PH_TOP - 0.12, PH_TOP))
    return fz * math.exp(-(x / sig) ** 2)


def ph_shape(g):
    Q, JWu, nbr = g["Q"], g["JWu"], g["nbr"]
    U = g["U"]
    off = np.zeros(U)
    for i in range(U):
        if JWu[i] > 0.5:
            continue
        x, y, z = Q[i]
        off[i] = PH_DEPTH * _ph_weight(g, x, y, z, PH_SIG)
    act = np.nonzero(off)[0]
    # one gentle smoothing pass of the offset field so the groove edges blend in
    region = set(act.tolist())
    for i in act:
        region.update(nbr[i].tolist())
    region = [i for i in region if JWu[i] <= 0.5]
    sm = off.copy()
    for i in region:
        nb = [j for j in nbr[i] if JWu[j] <= 0.5]
        if nb:
            sm[i] = 0.6 * off[i] + 0.4 * off[nb].mean()
    for i in region:
        if sm[i] > 1e-5:
            Q[i][1] += sm[i]
            Q[i][2] += 0.15 * sm[i]      # push roughly along the inward surface normal
    print("[mouth] philtrum groove: %d vertices moved, max %.3f cm" % ((sm > 1e-5).sum(), sm.max()))


def ph_color(g):
    Q, shade, JWu = g["Q"], g["shade"], g["JWu"]
    for i in range(g["U"]):
        if JWu[i] > 0.5:
            continue
        x, y, z = Q[i]
        groove = _ph_weight(g, x, y, z, 0.06)             # black groove skin
        patch = _ph_weight(g, x, y, z, 0.16)              # small dark stretch of upper lip
        s = 1 - max(0.95 * groove, 0.55 * patch)
        if s < shade[i]:
            shade[i] = s


HOOKS["shape"].append(ph_shape)
HOOKS["color"].append(ph_color)
