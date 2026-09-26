"""Arctic fox animation toolkit (run inside Blender via exec).

Coordinate frame = armature space: fox faces -Y (forward), +X is the fox's LEFT, +Z up, metres.
Ground is z=0. Rest paw 'ball' (the joint behind the toes) sits at z~0.02.

Usage in a clip script:
    exec(open(FOXLIB).read())
    def pose(t, f):            # t in [0,1] over the clip, f = frame number
        return {...}           # any subset of the keys below; missing keys = rest pose
    bake("ArcticFox_Pounce", frames=45, fn=pose, loop=False)
    sheet(["ArcticFox_Pounce"], view="side", count=10)   # contact sheet PNG to check your work

Pose keys (angles in RADIANS unless noted):
  hips_off   (x,y,z)  translation of the pelvis joint from rest (moves the whole body; feet stay where you put them)
  hips       (pitch, roll, yaw)  world rotation of pelvis. pitch>0 = rear end UP / nose down; roll>0 = top leans to fox's LEFT; yaw>0 = turns fox to its RIGHT? (rotation about +Z: +X side moves toward +Y/back)
  chest      (pitch, roll, yaw)  world rotation of ribcage (spine is blended between hips and chest)
  flex       scalar; >0 arches (rounds) the back, <0 hollows it
  neck       (pitch1, pitch2) world pitch deltas of the two neck bones; >0 = neck down/forward
  neck_yaw   rad, turns neck
  head       (pitch, yaw, roll) WORLD head rotation delta (head is gaze-stabilised: body motion does not rotate it). pitch>0 = nose down
  ears       (left, right) >0 = laid back
  tail       list of 6 downward slopes in DEGREES, base->tip (rest ~ [56,47,29,13,3,-6]; 0 = horizontal, negative = rising)
  tail_sway  list of 6 yaw values (rad) per segment, or a single float applied with growing amplitude to the tip
  feet       {'LF':(x,y,z), ...} armature-space target of each paw ball. Legs: LF RF LH RH. Missing = rest position.
  pastern    {'LF':deg, ...} angle of front metacarpus / hind metatarsus from vertical, + = paw ahead of wrist/hock.
             rest: front ~34, hind ~39. Folded paw in swing ~ -60..-90. Lying flat front paws ~ 80-90.
  toe        {'LF':deg} extra toe curl added to the rest toe direction (+ = toes point more forward/up)
  scap       {'L':rad,'R':rad} shoulder-blade swing; <0 swings the shoulder joint forward
  knee_pole  {'LH':(x,y,z)} optional pole direction for the 2-bone IK (default hind (0,-1,0) knee forward, front (0,1,0) elbow back)

Legs are solved with 2-bone IK (thigh/shin or upperarm/forearm) to reach the wrist/hock computed from the ball
position and pastern angle; unreachable targets are clamped (report shows max reach ratio; >1.0 = paw falls short).
"""
import bpy, math, os
from mathutils import Vector, Quaternion, Matrix

rig = bpy.data.objects["FoxRig"]; arm = rig.data
R = math.radians
X = Vector((1, 0, 0)); Y = Vector((0, 1, 0)); Z = Vector((0, 0, 1))
def qx(a): return Quaternion(X, a)
def qy(a): return Quaternion(Y, a)
def qz(a): return Quaternion(Z, a)
def mj(w): w = min(1, max(0, w)); return w * w * w * (10 - 15 * w + 6 * w * w)          # min-jerk ease 0..1
def sst(e0, e1, x):
    t = min(1, max(0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t
def keys(pts, t):
    """Smooth interpolation through [(t, value), ...] (values may be numbers or tuples). Eases in/out at each key."""
    pts = sorted(pts, key=lambda p: p[0])
    if t <= pts[0][0]: return pts[0][1]
    if t >= pts[-1][0]: return pts[-1][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t0 <= t <= t1:
            s = mj((t - t0) / (t1 - t0))
            if isinstance(v0, (tuple, list)): return tuple(lerp(a, b, s) for a, b in zip(v0, v1))
            return lerp(v0, v1, s)

def vdir(a): return Vector((0, -math.sin(a), -math.cos(a)))
def ang_of(v): return math.atan2(-v.y, -v.z)
def ik2(A, T, a, b, pole):
    d = T - A; L = d.length; ratio = L / (a + b)
    L = min(max(L, abs(a - b) + 1e-4), a + b - 1e-4); u = d.normalized()
    ca = (a*a + L*L - b*b) / (2*a*L); sa = math.sqrt(max(0, 1 - ca*ca))
    n = pole - u * pole.dot(u)
    if n.length < 1e-6: n = Vector((0, 0, 1)) - u * u.z
    n.normalize()
    return A + u*a*ca + n*a*sa, A + u*L, ratio

bones = list(arm.bones); order = []; _seen = set()
def _visit(b):
    if b.name in _seen: return
    if b.parent: _visit(b.parent)
    _seen.add(b.name); order.append(b)
for _b in bones: _visit(_b)
BL = {b.name: b for b in bones}; LEN = {b.name: b.length for b in bones}
def rest_dir(n): b = BL[n]; return (b.tail_local - b.head_local).normalized()
REST_FEET = {s + 'F': BL[f'hand.{s}'].tail_local.copy() for s in 'LR'}
REST_FEET.update({s + 'H': BL[f'hock.{s}'].tail_local.copy() for s in 'LR'})
REST_PAST = {s + 'F': math.degrees(ang_of(rest_dir(f'hand.{s}'))) for s in 'LR'}
REST_PAST.update({s + 'H': math.degrees(ang_of(rest_dir(f'hock.{s}'))) for s in 'LR'})
TOE_REST = {s + 'F': ang_of(rest_dir(f'toes_front.{s}')) for s in 'LR'}
TOE_REST.update({s + 'H': ang_of(rest_dir(f'toes_hind.{s}')) for s in 'LR'})
def _slope(k):
    v = BL[f'tail{k}'].tail_local - BL[f'tail{k}'].head_local
    return math.atan2(-v.z, v.y)
TAIL_REST = [_slope(k) for k in range(1, 7)]
TAIL_REST_DEG = [round(math.degrees(a), 1) for a in TAIL_REST]
HIP_Y = {s: BL[f'thigh.{s}'].head_local.y for s in 'LR'}
SHOULDER_Y = {s: BL[f'upperarm.{s}'].head_local.y for s in 'LR'}

def _fcurves(act):
    if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])): return list(act.fcurves)
    out = []
    for layer in getattr(act, "layers", []):
        for strip in layer.strips:
            for cb in strip.channelbags: out += list(cb.fcurves)
    return out

def solve(p, rep):
    """Return {bone: armature-space matrix} for pose dict p."""
    g = lambda k, d: p.get(k, d)
    hp, hr, hy = g('hips', (0, 0, 0)); cp, cr, cy = g('chest', (0, 0, 0)); F = g('flex', 0.0)
    Q = {'root': Quaternion()}
    Q['hips'] = qz(hy) @ qy(hr) @ qx(hp - 0.6 * F)
    Qc = qz(cy) @ qy(cr) @ qx(cp + 0.7 * F)
    Q['spine1'] = Q['hips'].slerp(Qc, 0.33) @ qx(-0.25 * F)
    Q['spine2'] = Q['hips'].slerp(Qc, 0.66) @ qx(0.2 * F)
    Q['chest'] = Qc
    n1, n2 = g('neck', (0, 0)); ny = g('neck_yaw', 0.0)
    Q['neck1'] = qz(ny * 0.5 + cy * 0.5) @ qx(n1 + 0.4 * F)
    Q['neck2'] = qz(ny) @ qx(n2 + 0.2 * F)
    h = g('head', (0, 0, 0)); h = tuple(h) + (0,) * (3 - len(h))
    Q['head'] = qz(h[1]) @ qy(h[2]) @ qx(h[0])
    eL, eR = g('ears', (0, 0))
    Q['ear.L'] = Q['head'] @ qx(-eL); Q['ear.R'] = Q['head'] @ qx(-eR)
    tail = g('tail', TAIL_REST_DEG); sw = g('tail_sway', 0.0)
    if not isinstance(sw, (list, tuple)): sw = [sw * (0.25 + k / 5) / 1.25 for k in range(6)]
    for k in range(6):
        Q[f'tail{k+1}'] = Q['hips'] @ qz(sw[k]) @ qx(TAIL_REST[k] - R(tail[k]))
    scap = g('scap', {})
    for s in 'LR': Q[f'scapula.{s}'] = Quaternion(Qc @ X, scap.get(s, 0.0)) @ Qc
    feet = g('feet', {}); past = g('pastern', {}); toe = g('toe', {}); poles = g('knee_pole', {})
    off = Vector(g('hips_off', (0, 0, 0)))
    M = {}
    for b in order:
        n = b.name
        if b.parent:
            pb = b.parent; head = (M[pb.name] @ pb.matrix_local.inverted() @ b.matrix_local).translation
        else: head = b.matrix_local.translation.copy()
        if n == 'hips': head = head + off
        if n.startswith('thigh.') or n.startswith('upperarm.'):
            s = n[-1]; front = n.startswith('upper'); leg = s + ('F' if front else 'H')
            ball = Vector(feet.get(leg, REST_FEET[leg]))
            a3 = R(past.get(leg, REST_PAST[leg]))
            c2 = ('forearm.' if front else 'shin.') + s; c3 = ('hand.' if front else 'hock.') + s
            c4 = ('toes_front.' if front else 'toes_hind.') + s
            Tgt = ball - vdir(a3) * LEN[c3]
            pole = Vector(poles.get(leg, (0, 1, 0) if front else (0, -1, 0)))
            J, Tn, ratio = ik2(head, Tgt, LEN[n], LEN[c2], pole)
            rep['reach'] = max(rep.get('reach', 0), ratio)
            if ratio > 1.0: rep.setdefault('short', set()).add(leg)
            paw = Tn + vdir(a3) * LEN[c3]
            rep['minz'] = min(rep.get('minz', 9), paw.z)
            ta = TOE_REST[leg] + R(toe.get(leg, 0.0))
            dirs = {n: J - head, c2: Tn - J, c3: vdir(a3), c4: vdir(ta)}
            pq = Q[b.parent.name]
            for c in (n, c2, c3, c4):
                base = pq @ rest_dir(c)
                Q[c] = base.rotation_difference(dirs[c].normalized()) @ pq; pq = Q[c]
        if n not in Q: Q[n] = Q[b.parent.name] if b.parent else Quaternion()
        M[n] = Matrix.Translation(head) @ (Q[n].to_matrix() @ b.matrix_local.to_3x3()).to_4x4()
    return M

def bake(name, frames, fn, loop=False, fps=30, speed=0.0):
    """Bake fn(t, f) for f = 0..frames into action `name` (replaces an existing one). Returns a report dict."""
    act = bpy.data.actions.get(name)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    rig.animation_data_create(); ad = rig.animation_data; ad.action = act
    for pb in rig.pose.bones: pb.rotation_mode = 'QUATERNION'; pb.matrix_basis = Matrix()
    prevq = {}; rep = {}
    for f in range(frames + 1):
        t = f / frames
        M = solve(fn(t, f), rep)
        for b in order:
            pb = rig.pose.bones[b.name]
            if b.parent:
                p = b.parent
                basis = (p.matrix_local.inverted() @ b.matrix_local).inverted() @ (M[p.name].inverted() @ M[b.name])
            else: basis = b.matrix_local.inverted() @ M[b.name]
            loc, rot, _ = basis.decompose()
            if b.name in prevq and rot.dot(prevq[b.name]) < 0: rot.negate()
            prevq[b.name] = rot
            pb.rotation_quaternion = rot; pb.keyframe_insert("rotation_quaternion", frame=f, group=b.name)
            if b.name == 'hips':
                pb.location = loc; pb.keyframe_insert("location", frame=f, group=b.name)
    for fc in _fcurves(act):
        for k in fc.keyframe_points: k.interpolation = 'LINEAR'
        if loop and not any(m.type == 'CYCLES' for m in fc.modifiers): fc.modifiers.new('CYCLES')
    act["loop_frames"] = frames; act["speed_m_per_s"] = speed; act["looping"] = bool(loop)
    act.use_frame_range = True; act.frame_start = 0; act.frame_end = frames; act.use_cyclic = bool(loop)
    # keep every clip on its own muted NLA track so it exports with the others
    for tr in list(ad.nla_tracks):
        if tr.name == name: ad.nla_tracks.remove(tr)
    tr = ad.nla_tracks.new(); tr.name = name; tr.strips.new(name, 0, act); tr.mute = True
    rep['short'] = sorted(rep.get('short', []))
    rep = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in rep.items()}
    print("baked", name, frames + 1, "frames; reach(max, >1 = paw short):", rep.get('reach'),
          "short legs:", rep['short'], "lowest paw z (rest 0.02, <0.015 = in ground):", rep.get('minz'))
    return rep

def sheet(actions, view="side", count=8, path=None, frames=None):
    """Render a quick workbench contact sheet (one row per action) and save it as PNG. Returns the path.
    view: side | front | q34 | top | back.  frames: explicit frame list (overrides count)."""
    import numpy as np
    sc = bpy.context.scene; ad = rig.animation_data; keep = ad.action
    old = (sc.render.engine, sc.render.resolution_x, sc.render.resolution_y, sc.camera)
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'TEXTURE'; sh.show_backface_culling = True
    cam = bpy.data.objects.get("FoxSheetCam")
    if not cam:
        cam = bpy.data.objects.new("FoxSheetCam", bpy.data.cameras.new("FoxSheetCam")); sc.collection.objects.link(cam)
    sc.camera = cam; cam.data.type = 'ORTHO'; cam.data.ortho_scale = 1.3
    W, H = 400, 300; sc.render.resolution_x = W; sc.render.resolution_y = H; sc.render.resolution_percentage = 100
    P = {'side': ((2.0, 0.0, 0.3), (0, 0.0, 0.3)), 'front': ((0, -2.0, 0.3), (0, 0, 0.3)),
         'back': ((0, 2.0, 0.3), (0, 0, 0.3)), 'q34': ((1.4, -1.3, 0.6), (0, 0, 0.25)),
         'top': ((0, 0.0, 2.0), (0, 0, 0))}[view]
    cam.location = P[0]; cam.rotation_euler = (Vector(P[1]) - Vector(P[0])).to_track_quat('-Z', 'Y').to_euler()
    if view == 'top': cam.rotation_euler = (0, 0, 0)
    tmp = os.path.join(os.environ.get("TEMP", "C:/Temp"), "_foxsheet_%s.png" % os.getpid())
    rows = []
    for an in actions:
        a = bpy.data.actions[an]; ad.action = a; N = int(a.frame_end)
        fl = frames or [round(i * N / max(1, count - 1)) for i in range(count)]
        row = []
        for fr in fl:
            sc.frame_set(fr); sc.render.filepath = tmp; bpy.ops.render.render(write_still=True)
            img = bpy.data.images.load(tmp, check_existing=False)
            px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4); bpy.data.images.remove(img)
            px[:2, :, :3] = 0.1; px[:, :2, :3] = 0.1; row.append(px)
        rows.append(np.concatenate(row, 1))
    wmax = max(r.shape[1] for r in rows)
    rows = [np.pad(r, ((0, 0), (0, wmax - r.shape[1]), (0, 0))) for r in rows]
    s = np.concatenate(rows[::-1], 0)
    path = path or os.path.join(os.environ.get("TEMP", "C:/Temp"), "foxsheet_%s_%s.png" % ("_".join(actions), view))
    out = bpy.data.images.new("_sheet", s.shape[1], s.shape[0], alpha=True); out.pixels.foreach_set(s.ravel())
    out.filepath_raw = path; out.file_format = 'PNG'; out.save(); bpy.data.images.remove(out)
    cam.data.type = 'PERSP'; ad.action = keep
    sc.render.engine, sc.render.resolution_x, sc.render.resolution_y, sc.camera = old
    print("sheet", path, "frames", fl)
    return path
