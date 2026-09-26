exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/foxlib.py").read())
OUT = r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/liedown/"
NAME = "ArcticFox_LieDown"
N = 72
P = globals().get('P', {})
def pp(k, d): return P.get(k, d)

TR = TAIL_REST_DEG
def step(t, t0, t1, a, b, lift=0.03):
    s = mj((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
    s = min(1, max(0, s)) if t0 <= t <= t1 else (0.0 if t < t0 else 1.0)
    u = min(1, max(0, (t - t0) / (t1 - t0)))
    v = tuple(lerp(x, y, s) for x, y in zip(a, b))
    return (v[0], v[1], v[2] + lift * math.sin(math.pi * u))

def pose(t, f):
    # --- key times
    T_SIT0, T_SIT1 = 0.06, 0.38
    T_LOW0, T_LOW1 = 0.42, 0.78
    br = 0.0
    if t > 0.80:
        w = sst(0.80, 0.88, t)
        br = w * math.sin(2 * math.pi * (t - 0.80) / 0.20)
    # exhale: a small extra sink right after landing
    exh = keys([(0, 0), (0.74, 0), (0.82, 1), (0.92, 0.6), (1, 0.6)], t)
    hz = keys([(0, 0), (T_SIT0, 0), (T_SIT1, pp('sit_z', -0.125)), (T_LOW0, pp('sit_z', -0.125)), (T_LOW1, pp('lie_z', -0.148))], t)
    hy = keys([(0, 0), (T_SIT0, 0), (T_SIT1, pp('sit_y', 0.06)), (T_LOW0, pp('sit_y', 0.06)), (T_LOW1, pp('lie_y', 0.04))], t)
    hz += -0.004 * exh + 0.0025 * br
    hp = keys([(0, 0), (T_SIT0, 0), (T_SIT1, pp('sit_hp', -0.42)), (T_LOW0, pp('sit_hp', -0.42)), (T_LOW1, pp('lie_hp', 0.0))], t)
    cp = keys([(0, 0), (T_SIT0, 0), (T_SIT1, pp('sit_cp', -0.36)), (T_LOW0, pp('sit_cp', -0.36)), (T_LOW1, pp('lie_cp', -0.06))], t)
    cp += 0.02 * exh - 0.012 * br
    flex = keys([(0, 0), (T_SIT1, 0.08), (T_LOW0, 0.08), (T_LOW1, 0.0)], t) + 0.03 * br
    # --- hind legs: hocks down, metatarsus flat
    hx = pp('hx', 0.075)
    LH0 = tuple(REST_FEET['LH']); RH0 = tuple(REST_FEET['RH'])
    LH1 = (hx, pp('lh_y', 0.15), 0.02); RH1 = (-hx, pp('rh_y', 0.12), 0.02)
    s_h = mj((t - T_SIT0) / (T_SIT1 - T_SIT0 - 0.04)) if t > T_SIT0 else 0
    s_h = min(1, s_h)
    lh = tuple(lerp(a, b, s_h) for a, b in zip(LH0, LH1))
    rh = tuple(lerp(a, b, s_h) for a, b in zip(RH0, RH1))
    hpast = pp('hpast', 84)
    pLH = keys([(0, REST_PAST['LH']), (T_SIT0, REST_PAST['LH']), (T_SIT1, hpast)], t)
    pRH = keys([(0, REST_PAST['RH']), (T_SIT0 + 0.02, REST_PAST['RH']), (T_SIT1 + 0.02, hpast)], t)
    # --- front legs: two steps forward, then elbows down
    LF0 = tuple(REST_FEET['LF']); RF0 = tuple(REST_FEET['RF'])
    fx = pp('fx', 0.055)
    LFa = (fx, pp('lf_a', -0.22), 0.02); RFa = (-fx, pp('rf_a', -0.25), 0.02)
    LF1 = (fx, pp('lf_y', -0.27), 0.02); RF1 = (-fx, pp('rf_y', -0.28), 0.02)
    lf = LF0 if t < 0.36 else step(t, 0.36, 0.48, LF0, LFa) if t < 0.52 else step(t, 0.58, 0.70, LFa, LF1, 0.02)
    rf = RF0 if t < 0.44 else step(t, 0.44, 0.56, RF0, RFa) if t < 0.62 else step(t, 0.64, 0.76, RFa, RF1, 0.02)
    fpast = pp('fpast', 84)
    pLF = keys([(0, REST_PAST['LF']), (0.36, REST_PAST['LF']), (0.42, -20), (0.48, REST_PAST['LF'] + 5), (0.56, 45), (0.64, 60), (0.78, fpast)], t)
    pRF = keys([(0, REST_PAST['RF']), (0.44, REST_PAST['RF']), (0.50, -20), (0.56, REST_PAST['RF'] + 5), (0.64, 50), (0.70, 65), (0.80, fpast)], t)
    fpole = pp('fpole', (0, 1, -0.6))
    poleF = tuple(lerp(a, b, sst(0.45, 0.75, t)) for a, b in zip((0, 1, 0), fpole))
    hpole = pp('hpole', (0.5, -1, 0.3))
    poleL = tuple(lerp(a, b, sst(0.06, 0.35, t)) for a, b in zip((0, -1, 0), hpole))
    poleR = (-poleL[0], poleL[1], poleL[2])
    # --- head / neck
    n1 = keys([(0, 0), (T_SIT0, 0), (T_SIT1, -0.28), (0.55, -0.2), (T_LOW1, pp('n1', -0.15)), (0.9, pp('n1', -0.15) + 0.1), (1, pp('n1', -0.15) + 0.1)], t)
    n2 = keys([(0, 0), (T_SIT0, 0), (T_SIT1, -0.18), (0.55, -0.12), (T_LOW1, pp('n2', -0.1)), (0.9, pp('n2', -0.1) + 0.12), (1, pp('n2', -0.1) + 0.12)], t)
    hdp = keys([(0, 0), (0.5, 0.05), (0.62, 0.12), (T_LOW1, 0.0), (0.9, 0.08), (1, 0.08)], t)
    hyaw = keys([(0, 0), (0.25, 0.0), (0.35, 0.12), (0.5, 0.0), (1, 0)], t)
    ears = keys([(0, (0, 0)), (0.2, (0, 0)), (0.3, (0.25, 0.1)), (0.42, (0, 0)), (0.82, (0.2, 0.2)), (0.9, (0.1, 0.12)), (1, (0.1, 0.12))], t)
    # --- tail
    tail_sit = pp('tail_sit', [30, 5, 0, -2, -3, -3])
    tail_lie = pp('tail_lie', [55, 20, 6, 2, 0, 0])
    tail = [keys([(0, TR[k]), (T_SIT0, TR[k]), (T_SIT1, tail_sit[k]), (T_LOW0, tail_sit[k]), (T_LOW1, tail_lie[k])], t) for k in range(6)]
    sway_end = pp('sway', [0.0, 0.25, 0.35, 0.35, 0.3, 0.25])
    ts = keys([(0, 0), (0.55, 0), (0.88, 1)], t)
    sway = [s * ts for s in sway_end]
    return dict(hips_off=(0, hy, hz), hips=(hp, 0, 0), chest=(cp, 0, 0), flex=flex,
                neck=(n1, n2), head=(hdp, hyaw, 0), ears=ears, tail=tail, tail_sway=sway,
                feet={'LF': lf, 'RF': rf, 'LH': lh, 'RH': rh},
                pastern={'LF': pLF, 'RF': pRF, 'LH': pLH, 'RH': pRH},
                knee_pole={'LF': poleF, 'RF': poleF, 'LH': poleL, 'RH': poleR})

def check(frames):
    ob = bpy.data.objects['ArcticFox']; sc = bpy.context.scene; ad = rig.animation_data; keep = ad.action
    ad.action = bpy.data.actions[NAME]
    for fr in frames:
        sc.frame_set(fr); dg = bpy.context.evaluated_depsgraph_get(); e = ob.evaluated_get(dg)
        me = e.to_mesh(); mw = ob.matrix_world; rw = rig.matrix_world.inverted()
        zs = [(rw @ (mw @ v.co)) for v in me.vertices]
        lo = min(zs, key=lambda v: v.z)
        below = sum(1 for v in zs if v.z < -0.003)
        print("frame", fr, "mesh minz %.3f at y %.3f x %.3f, verts below -3mm: %d" % (lo.z, lo.y, lo.x, below))
        e.to_mesh_clear()
    ad.action = keep
    rep = {}; M = solve(pose(1.0, N), rep)
    for n in ['forearm.L', 'hand.L', 'hock.L', 'shin.L', 'upperarm.L', 'thigh.L', 'tail6', 'head']:
        print(n, tuple(round(c, 3) for c in M[n].translation))
