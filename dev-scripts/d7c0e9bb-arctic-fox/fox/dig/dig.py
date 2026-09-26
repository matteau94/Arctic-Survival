exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/foxlib.py").read())
TAU = 2 * math.pi
N = 24
D = r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/dig/"
VIEWS = globals().get("VIEWS", ["side", "front", "q34"])
FR = globals().get("FR", [0, 3, 6, 9, 12, 15, 18, 21])

PATH = [  # (u, (y, z, pastern))  reach fwd -> strike -> rake back -> flick up -> return
    (0.00, (-0.320, 0.065, 45)),
    (0.14, (-0.305, 0.022, 30)),
    (0.50, (-0.140, 0.026, -30)),
    (0.66, (-0.150, 0.080, -50)),
    (0.86, (-0.265, 0.095, 5)),
    (1.00, (-0.320, 0.065, 45)),
]

def front(u, side):
    y, z, pa = keys(PATH, u % 1.0)
    sg = 1 if side == 'L' else -1
    x = sg * (0.050 + 0.008 * math.sin(TAU * u))
    return (x, y, z), pa

def pose(t, f):
    uL = (2 * t) % 1.0
    uR = (2 * t + 0.5) % 1.0
    pL, aL = front(uL, 'L'); pR, aR = front(uR, 'R')
    s4 = math.sin(TAU * 4 * t); c4 = math.cos(TAU * 4 * t)
    side = math.sin(TAU * 2 * t)
    return {
        'hips_off': (0, 0.012 + 0.006 * s4, -0.003 + 0.003 * c4),
        'hips': (R(6), R(1.5) * side, R(1.5) * side),
        'chest': (R(9) + R(1.5) * s4, R(4) * side, R(-4) * side),
        'flex': -0.05,
        'neck': (R(18), R(12) + R(3) * math.sin(TAU * 4 * t + 0.8)),
        'neck_yaw': R(3) * side,
        'head': (R(38) + R(4) * math.sin(TAU * 4 * t + 1.2), R(2) * side, R(-3) * side),
        'ears': (R(-8) + R(6) * max(0, math.sin(TAU * 3 * t)) ** 4,
                 R(-8) + R(6) * max(0, math.sin(TAU * 3 * t + 2.0)) ** 4),
        'tail': [30 - 4 * s4, 15, 0, -10, -12, -8],
        'tail_sway': R(14) * math.sin(TAU * 2 * t),
        'feet': {'LF': pL, 'RF': pR,
                 'LH': (0.075, 0.165, 0.02), 'RH': (-0.075, 0.140, 0.02)},
        'pastern': {'LF': aL, 'RF': aR, 'LH': 42, 'RH': 42},
        'toe': {'LF': 15 * math.sin(TAU * uL), 'RF': 15 * math.sin(TAU * uR)},
        'scap': {'L': R(-10) * math.cos(TAU * uL), 'R': R(-10) * math.cos(TAU * uR)},
    }

rep = bake("ArcticFox_Dig", N, pose, loop=True)
# per-leg reach report
per = {}
for f in range(N + 1):
    for leg in ['LF', 'RF', 'LH', 'RH']:
        pass
for f in range(N + 1):
    p = pose(f / N, f); r = {}
    M = solve(p, r)
    for s in 'LR':
        for fr, bn, hn in (('F', 'upperarm.', 'hand.'), ('H', 'thigh.', 'hock.')):
            A = M[bn + s].translation; W = M[hn + s].translation
            ratio = (W - A).length / (LEN[bn + s] + LEN[('forearm.' if fr == 'F' else 'shin.') + s])
            per.setdefault(s + fr, []).append(round(ratio, 2))
for k, v in per.items(): print(k, "min", min(v), "max", max(v))
for v in VIEWS:
    sheet(["ArcticFox_Dig"], view=v, frames=FR, path=D + "s_%s.png" % v)
