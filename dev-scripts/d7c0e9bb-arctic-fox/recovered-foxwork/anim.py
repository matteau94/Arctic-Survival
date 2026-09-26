import bpy, math
from mathutils import Vector, Quaternion, Matrix
rig = bpy.data.objects["FoxRig"]; arm = rig.data
R = math.radians
X = Vector((1, 0, 0)); Y = Vector((0, 1, 0)); Z = Vector((0, 0, 1))
def qx(a): return Quaternion(X, a)
def qy(a): return Quaternion(Y, a)
def qz(a): return Quaternion(Z, a)
def mj(w): return w * w * w * (10 - 15 * w + 6 * w * w)
def sst(e0, e1, x):
    t = min(1, max(0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)

def periodic_curve(pts):
    """Periodic Catmull-Rom through (u, value_deg) points, u in [0,1)."""
    pts = sorted(pts); n = len(pts)
    U = [p[0] for p in pts]; V = [p[1] for p in pts]
    def get(i):
        k, m = divmod(i, n); return U[m] + k, V[m]
    def f(u):
        u %= 1.0
        i = max(j for j in range(-1, n) if get(j)[0] <= u)
        u0, v0 = get(i); u1, v1 = get(i + 1); um, vm = get(i - 1); u2, v2 = get(i + 2)
        t = (u - u0) / (u1 - u0)
        m0 = (v1 - vm) / (u1 - um) * (u1 - u0); m1 = (v2 - v0) / (u2 - u0) * (u1 - u0)
        return (2*t**3 - 3*t*t + 1) * v0 + (t**3 - 2*t*t + t) * m0 + (-2*t**3 + 3*t*t) * v1 + (t**3 - t*t) * m1
    return f

def vdir(a):  # unit vector joint->distal; a>0 = distal end ahead (toward -Y)
    return Vector((0, -math.sin(a), -math.cos(a)))
def ang_of(v): return math.atan2(-v.y, -v.z)

def ik2(A, T, a, b, pole):
    d = T - A; L = d.length; ratio = L / (a + b)
    L = min(max(L, abs(a - b) + 1e-4), a + b - 1e-4); u = d.normalized()
    ca = (a*a + L*L - b*b) / (2*a*L); sa = math.sqrt(max(0, 1 - ca*ca))
    n = pole - u * pole.dot(u); n.normalize()
    return A + u*a*ca + n*a*sa, A + u*L, ratio

bones = list(arm.bones)
order = []; seen = set()
def visit(b):
    if b.name in seen: return
    if b.parent: visit(b.parent)
    seen.add(b.name); order.append(b)
for b in bones: visit(b)
BL = {b.name: b for b in bones}
LEN = {b.name: b.length for b in bones}
def rest_dir(n): b = BL[n]; return (b.tail_local - b.head_local).normalized()
ball0 = {s: BL[f'hock.{s}'].tail_local.copy() for s in 'LR'}
fball0 = {s: BL[f'hand.{s}'].tail_local.copy() for s in 'LR'}
PSI_REST = sum(ang_of(rest_dir(f'hand.{s}')) for s in 'LR') / 2
PHI_REST = sum(ang_of(rest_dir(f'hock.{s}')) for s in 'LR') / 2
TOE_F = sum(ang_of(rest_dir(f'toes_front.{s}')) for s in 'LR') / 2
TOE_H = sum(ang_of(rest_dir(f'toes_hind.{s}')) for s in 'LR') / 2
def slope(k):
    v = BL[f'tail{k}'].tail_local - BL[f'tail{k}'].head_local
    return math.atan2(-v.z, v.y)            # downward slope of the tail segment
TAIL_REST = [slope(k) for k in range(1, 7)]

def leg_state(u, d, S, y0, h, x, zr):
    u %= 1.0
    if u < d:
        s = u / d
        return Vector((x, y0 - S/2 + S*s, zr)), math.sin(math.pi*s), None
    w = (u - d) / (1 - d)
    y = y0 + S/2 - S*mj(w) - S*0.05*math.sin(math.pi*sst(0.55, 1.0, w))
    z = zr + h * math.sin(math.pi * (w ** 0.85)) ** 1.3
    return Vector((x, y, z)), 0.0, w

def run(G):
    N = G['frames']; name = G['name']
    act = bpy.data.actions.get(name)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    rig.animation_data_create(); rig.animation_data.action = act
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'; pb.matrix_basis = Matrix()
    psi = periodic_curve(G['psi']); phi = periodic_curve(G['phi'])
    legs = G['legs']; d = G['duty']; S = G['S']
    def loads_at(t):
        return {leg: leg_state(t + legs[leg], d, S, 0, 0, 0, 0)[1] for leg in legs}
    smp = [loads_at(i / 240) for i in range(240)]
    mean_tot = sum(sum(s.values()) for s in smp) / 240
    mean_fh = sum(s['LF'] + s['RF'] - s['LH'] - s['RH'] for s in smp) / 240
    extra_fn = G.get('extra', lambda t: {})
    prevq = {}; worst = 0.0
    for f in range(N + 1):
        t = f / N; T2 = 2 * math.pi * t; ld = loads_at(t); ex = extra_fn(t)
        tot = sum(ld.values()) - mean_tot
        fh = ld['LF'] + ld['RF'] - ld['LH'] - ld['RH'] - mean_fh
        lr_h = ld['LH'] - ld['RH']; lr_f = ld['LF'] - ld['RF']
        zoff = G['crouch'] - G['bob'] * tot + ex.get('z', 0)
        xoff = G.get('sway', 0) * (lr_h + lr_f) * 0.5
        yoff = ex.get('y', 0)
        pitch = G['pitch'] * fh + ex.get('pitch', 0)
        F = ex.get('flex', 0)
        feet = {}; sw = {}
        for leg in legs:
            s = leg[0]; front = leg[1] == 'F'
            base = (fball0 if front else ball0)[s]
            x = math.copysign(G['xf' if front else 'xh'], base.x)
            p, _, w = leg_state(t + legs[leg], d, S, G['y0f' if front else 'y0h'],
                                G['hf' if front else 'hh'], x, base.z)
            feet[leg] = p; sw[leg] = w
        yaw_h = -G['yaw'] * (feet['RH'].y - feet['LH'].y) / S
        yaw_c = -G['yaw'] * (feet['RF'].y - feet['LF'].y) / S
        roll_h = -G['roll'] * lr_h; roll_c = -G['roll'] * lr_f
        Q = {'root': Quaternion()}
        Q['hips'] = qz(yaw_h) @ qy(roll_h) @ qx(pitch - 0.6 * F)
        Qc = qz(yaw_c * 0.6) @ qy(roll_c) @ qx(pitch + 0.7 * F)
        Q['spine1'] = Q['hips'].slerp(Qc, 0.33) @ qx(-0.25 * F)
        Q['spine2'] = Q['hips'].slerp(Qc, 0.66) @ qx(0.2 * F)
        Q['chest'] = Qc
        nk = G['neck']
        nod = G.get('nod', 0) * (ld['LF'] + ld['RF'] - 0.5 * (ld['LH'] + ld['RH'])) + ex.get('nod', 0)
        Q['neck1'] = qz(yaw_c * 0.3) @ qx(R(nk[0]) + nod * 0.5 + 0.4 * F)
        Q['neck2'] = qz(yaw_c * 0.1) @ qx(R(nk[1]) + nod + 0.2 * F)
        Q['head'] = qz(ex.get('look', 0)) @ qx(R(G['head']) + nod * 0.3 + ex.get('head', 0))   # gaze held steady in the world
        for s in 'LR':
            ea = R(G['ears']) + ex.get('ear' + s, 0)
            Q[f'ear.{s}'] = Q['head'] @ qx(-ea)
        for k in range(6):
            kk = k / 5
            lift = TAIL_REST[k] - R(G['tail'][k])
            bounce = G['tbounce'] * (0.35 + kk) * math.sin(G.get('tvf', 2) * T2 - G['tlag'] * (k + 1) + G.get('tph', 0))
            swy = G['tsway'] * (0.25 + kk) * math.sin(T2 - G['tlag'] * (k + 1) * 0.7) + ex.get('tswish', 0) * (0.2 + kk)
            Q[f'tail{k+1}'] = Q['hips'] @ qz(swy) @ qx(lift + bounce)
        for s in 'LR':
            fy = feet[s + 'F'].y - G['y0f']
            Q[f'scapula.{s}'] = Quaternion(Qc @ X, G['scap'] * fy / (S / 2)) @ Qc
        M = {}
        for b in order:
            n = b.name
            if b.parent:
                p = b.parent; head = (M[p.name] @ p.matrix_local.inverted() @ b.matrix_local).translation
            else:
                head = b.matrix_local.translation.copy()
            if n == 'hips': head = head + Vector((xoff, yoff, zoff))
            if n.startswith('thigh.') or n.startswith('upperarm.'):
                s = n[-1]; front = n.startswith('upper')
                leg = s + ('F' if front else 'H'); u = (t + legs[leg]) % 1
                a3 = R((psi if front else phi)(u))
                c2 = ('forearm.' if front else 'shin.') + s
                c3 = ('hand.' if front else 'hock.') + s
                c4 = ('toes_front.' if front else 'toes_hind.') + s
                Tgt = feet[leg] - vdir(a3) * LEN[c3]
                pole = Vector((0, 1, 0)) if front else Vector((0, -1, 0))
                J, Tn, ratio = ik2(head, Tgt, LEN[n], LEN[c2], pole); worst = max(worst, ratio)
                w = sw[leg]; toe_rest = TOE_F if front else TOE_H
                if w is None: ta = toe_rest
                else:
                    e = math.sin(math.pi * w)
                    ta = toe_rest + (a3 - (PSI_REST if front else PHI_REST)) * 0.85 * e ** 0.6 + R(-20) * e
                dirs = {n: J - head, c2: Tn - J, c3: vdir(a3), c4: vdir(ta)}
                pq = Q[b.parent.name]
                for c in (n, c2, c3, c4):
                    base = pq @ rest_dir(c)
                    Q[c] = base.rotation_difference(dirs[c].normalized()) @ pq; pq = Q[c]
            if n not in Q: Q[n] = Q[b.parent.name] if b.parent else Quaternion()
            M[n] = Matrix.Translation(head) @ (Q[n].to_matrix() @ b.matrix_local.to_3x3()).to_4x4()
        for b in order:
            pb = rig.pose.bones[b.name]
            if b.parent:
                p = b.parent
                basis = (p.matrix_local.inverted() @ b.matrix_local).inverted() @ (M[p.name].inverted() @ M[b.name])
            else:
                basis = b.matrix_local.inverted() @ M[b.name]
            loc, rot, _ = basis.decompose()
            if b.name in prevq and rot.dot(prevq[b.name]) < 0: rot.negate()
            prevq[b.name] = rot
            pb.rotation_quaternion = rot; pb.keyframe_insert("rotation_quaternion", frame=f, group=b.name)
            if b.name == 'hips':
                pb.location = loc; pb.keyframe_insert("location", frame=f, group=b.name)
    fps = 30.0
    act["speed_m_per_s"] = round(S / d * fps / N if d > 0 else 0.0, 3)
    act["loop_frames"] = N
    act.use_frame_range = True; act.frame_start = 0; act.frame_end = N; act.use_cyclic = True
    return worst
