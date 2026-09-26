exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/foxlib.py").read())
N = 120
TAU = 2 * math.pi
def cdist(a, b):
    d = abs(a - b) % 1.0; return min(d, 1 - d)
BURSTS = [(0.03, 0.055), (0.335, 0.05), (0.72, 0.06)]   # centre, half-width
def burst(t):
    env = 0.0
    for c, w in BURSTS:
        d = cdist(t, c)
        if d < w: env = max(env, math.cos(d / w * math.pi / 2) ** 2)
    return env
# lift/listen phase (loop-safe: 0 at ends)
def lift(t): return keys([(0, 0), (0.40, 0), (0.46, 1), (0.56, 1), (0.63, 0), (1, 0)], t)
def yawk(t): return keys([(0, 0.36), (0.08, 0.36), (0.28, -0.40), (0.38, -0.40), (0.46, -0.08), (0.56, -0.02),
                          (0.64, -0.05), (0.78, -0.05), (0.96, 0.36), (1, 0.36)], t)
def pose(t, f):
    L = lift(t); b = burst(t)
    tw = math.sin(TAU * 30 * t)            # 7.5 Hz sniff twitch
    sn = b * (0.5 + 0.5 * tw)              # 0..1 nose dip pulse
    y = yawk(t)
    slow = math.sin(TAU * t)
    fwd = 1 - 0.55 * L
    p = {}
    p['hips_off'] = (0, -0.022 * fwd, -0.018 * fwd - 0.002 * sn)
    p['hips'] = (0.05 * fwd, 0.0, 0.03 * y)
    p['chest'] = (0.12 * fwd, -0.04 * y, 0.12 * y)
    p['neck'] = (lerp(1.30, 0.55, L) + 0.03 * sn, lerp(1.45, 0.70, L) + 0.04 * sn)
    p['neck_yaw'] = y * 0.9
    p['head'] = (lerp(1.00, 0.35, L) + 0.07 * sn, y * 0.55, -0.25 * y)
    lt = keys([(0, 0), (0.44, 0), (0.48, 1), (0.52, -1), (0.56, 0.6), (0.62, 0), (1, 0)], t)
    p['ears'] = (-0.08 + 0.35 * max(0, lt) + 0.04 * sn, -0.08 + 0.35 * max(0, -lt) + 0.04 * sn)
    p['tail'] = [62, 55, 40, 25, 12, 8]
    p['tail_sway'] = 0.14 * math.sin(TAU * t + 0.8)
    # RF small step during the listening pause
    s = keys([(0, 0), (0.47, 0), (0.52, 1), (0.57, 0), (1, 0)], t)
    rf = REST_FEET['RF']
    p['feet'] = {'RF': (rf.x, rf.y, rf.z + 0.035 * s)}
    p['pastern'] = {'LF': 40 * fwd + 32 * (1 - fwd), 'RF': lerp(40 * fwd + 37 * (1 - fwd), -5, s)}
    p['toe'] = {'RF': 8 * s}
    p['scap'] = {'L': -0.05 * fwd, 'R': -0.05 * fwd - 0.1 * s}
    return p
# nose measure
HB = BL['head']; NOSE_L = HB.matrix_local.inverted() @ Vector((0, -0.45, 0.37))
def nose(t):
    M = solve(pose(t, 0), {}); return M['head'] @ NOSE_L
