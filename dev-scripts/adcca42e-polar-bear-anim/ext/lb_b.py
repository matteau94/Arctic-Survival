# Crisp black lip edge along both lips (polar bears have black lip skin).
#
# The lip line is a vertex colour, i.e. linearly interpolated across each triangle, and the
# vertex rows beside the seam are 0.05-0.25 cm apart and uneven. A falloff function of the
# distance to the seam therefore renders as a smudge whose width follows the mesh rows
# (zig-zag). Instead every vertex near the seam gets the value that puts the interpolated
# 50% black->white edge at a fixed distance W from the seam along the edge to its neighbour.
# Result: one black band of constant width that follows the real seam (line_z) on both lips.
W_UP = 0.12        # half-width of the black band on the upper lip, cm
W_LO = 0.085        # ... on the lower lip
BLACK = 0.03       # lip skin colour multiplier
Y_CORNER = -6.70   # the band tapers to a point just past here (mouth corner)

def lipband_color(g):
    np = g["np"]; Q = g["Q"]; nbr = g["nbr"]; ramp = g["ramp"]; line_z = g["line_z"]
    JW = g["JWu"]; U = g["U"]
    x, y, z = Q[:, 0], Q[:, 1], Q[:, 2]
    d = z - np.array([line_z(v) for v in y])
    region = (y > -7.95) & (y < -6.5) & (np.abs(x) < 1.0) & (np.abs(d) < 0.45)
    shade = g["shade"]
    shade[region] = 1.0                       # replace the default soft line in the region
    # seam: vertices snapped onto the lip line, plus the upper/lower-lip boundary vertices
    seam = region & (np.abs(d) < 0.035)
    for i in np.nonzero(region & (np.abs(d) < 0.12))[0]:
        n = nbr[i]
        if len(n) and (JW[i] < 0.5) != (JW[n] < 0.5).all():
            seam[i] = True
    seam &= (y < Y_CORNER + 0.04)
    si = np.nonzero(seam)[0]
    reg = np.nonzero(region)[0]
    # 3D distance to the seam
    r = np.full(U, 9.0)
    for k in range(0, len(reg), 512):
        idx = reg[k:k + 512]
        r[idx] = np.sqrt(((Q[idx, None, :] - Q[None, si, :]) ** 2).sum(-1)).min(1)
    r[si] = 0.0
    w = np.where(JW > 0.5, W_LO, W_UP)
    new = np.ones(U)
    for i in reg:
        wi = w[i]
        n = [j for j in nbr[i] if region[j]]
        if r[i] < wi:
            s = 0.0
        else:
            # brightest value that keeps the edge from the inner (black) neighbour at wi
            inner = [j for j in n if r[j] < wi]
            if not inner:
                continue
            rj = min(r[j] for j in inner)
            s = min(1.0, 0.5 * (r[i] - rj) / max(wi - rj, 1e-6))
        new[i] = BLACK + (1 - BLACK) * s
    # taper to a point at the mouth corner
    t = 1 - np.array([ramp(v, Y_CORNER - 0.05, Y_CORNER + 0.05) for v in y])
    new = 1 - (1 - new) * t
    shade[region] = np.minimum(shade[region], new[region])
    g["shade"] = shade
    print("[mouth] lipband: seam %d, dark verts %d" % (seam.sum(), (new < 0.5).sum()))
HOOKS["color"].append(lipband_color)
