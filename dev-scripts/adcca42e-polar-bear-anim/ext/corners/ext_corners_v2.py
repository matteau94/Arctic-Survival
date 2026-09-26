# Mouth-corner extension: straighten the lip line so it no longer reads as a smile.
# 1) line hook: target lip line droops a little more toward the corner (side view: runs back
#    level-to-slightly-down).
# 2) shape hook: the roar sculpt leaves the upper-lip corner fold rising up and back behind the
#    mouth corner (|x| 0.6-0.8), which reads as an upturned smile from the front. Bend that fold
#    down with a smooth displacement field that is zero on the snapped seam, so the lips stay
#    closed and the painted lip line still sits on line_z.
CORNER_DROP = 0.17

def _corners_line(g):
    def line_z(y):
        u = min(1.15, max(0.0, y + 7.8))
        return 6.95 - 0.23 * u + 0.04 * u * u
    g["line_z"] = line_z

def _corners_shape(g):
    Q = g["Q"]; ramp = g["ramp"]; m = g["math"]
    for i in range(len(Q)):
        x, y, z = Q[i]
        ax = abs(x)
        if ax < 0.55 or ax > 1.3 or not (-6.9 < y < -6.1) or not (6.3 < z < 7.4):
            continue
        w = ramp(ax, 0.55, 0.8) * (1 - ramp(ax, 0.95, 1.25))
        w *= m.exp(-((z - 6.85) / 0.3) ** 2)
        w *= 1 - ramp(y, -6.45, -6.15)
        Q[i][2] = z - CORNER_DROP * w

HOOKS["line"].append(_corners_line)
HOOKS["shape"].append(_corners_shape)
