"""Add the survivor's non-locomotion clips to 'HumanRig' (human_rig.py): Human_Gather, Human_Attack,
Human_Throw, Human_WarmHands, Human_Hurt and Human_Death.

    blender -b Human_Rigged.blend --python human_anim_locomotion.py --python human_anim_extra.py --python human_export.py
    blender -b Human_Stub.blend --python human_anim_extra.py -- --test-save <path.blend> [--only Human_Throw,...]

Only these six actions are created / replaced (fake user, frame range set, custom props); every other
action is kept. Nothing is saved or exported here - human_export.py does that as the last step.
--test-save writes a copy of the result to <path> for testing only; --only builds a subset.

Conventions as in orca_anim_extra.py / penguin_anim.py: 60 fps, quaternion bones, a key on EVERY frame
on EVERY bone (rotation; location on root, pelvis and whatever Human_Idle keys), linear interpolation,
rest data read from the rig at runtime, rotations given about armature-space axes (dq() helper).

Clips                        frames   notes
  Human_Gather     one shot   210 (3.50 s) step back into a kneel, reach, grab snow, look at it, stand
  Human_Attack     one shot    78 (1.30 s) one-handed overhead chop with the tool at prop.R
  Human_Throw      one shot   114 (1.90 s) overhand spear throw from prop.R, stride, release, follow-through
  Human_WarmHands  loop       240 (4.00 s) rub gloves in front of the face, blow into them, shiver
  Human_Hurt       one shot    48 (0.80 s) flinch from a hit on the front / left, recover
  Human_Death      one shot   156 (2.60 s) knees buckle, topple forward-left, settle on the ground (no return)
One-shots (except Death) start and end on the Human_Idle frame-0 pose (read from the action at runtime;
if the locomotion script has not made it, a neutral stand built here is used instead). Exception, by
design: in Attack the right fingers hold the tool grip on every frame, in Throw they hold the spear
from frame 0 until the release and then relax back to the idle hand. Gameplay events are stored as
custom properties on the action (seconds): event_grab, event_hit, event_release, event_impact.

How the poses are built
  every frame is the Idle frame-0 pose plus channels (numpy arrays over the clip):
    root / pelvis    armature-space offsets + rotations of the pelvis about its head (weight transfer)
    trunk            lean / side / twist spread over spine_01..03 (25 / 35 / 40 %), neck, head
    arms             analytic two-bone IK: wrist target + elbow pole in armature space or in the chest
                     frame (then the target rides on the torso), hand orientation from (fingers, palm)
                     or (tool shaft, palm) vectors; 50 % of the wrist twist goes into the forearm
                     (pronation happens in the forearm, not in the wrist); the clavicle shrugs and
                     protracts automatically when the hand goes above / in front of the shoulder
    legs             analytic two-bone IK baked to FK, per frame, no constraints left: a foot track
                     gives the ball position, the foot pitch about the ball (heel up) or about the heel
                     (toes up), yaw and lift; a planted ball / heel is EXACTLY fixed, the toe stays flat
                     on the ground while the heel is up, knees point along a pole that turns with the hips
    face             jaw (hard stop + rebound), blinks, squint, brows, eyes aimed at the look target
                     (upper lids follow the eye pitch)
    fingers          curl / spread per finger through springs with different rates (index leads, pinky
                     trails) -> the hand closes and opens as a cascade, not as one block
  secondary motion (damped springs): the head is driven by the chest and lags / overshoots it, the
  hood lying down the back is thrown off the back by the chest's acceleration and by gravity when the
  torso leans (hard stop on the back, rebounds), the fingers follow through fast arm moves, the jaw
  bounces on its stop. Loops simulate 5 cycles and keep the settled last one, so they close exactly.
  One-shots are blended onto the exact Idle frame-0 bone pose over the first 0.10 s / last 0.25 s
  (the IK already reproduces it; the blend only removes sub-degree IK / twist differences).
Ground contact
  the kneeling knee (Gather, Death), the fingertips touching the snow (Gather) and the lying body
  (Death) are calibrated against the REAL deformed mesh at runtime (vertices grouped by their dominant
  bone), so there is no ground penetration whatever mesh the rig drives. Death additionally lifts the
  pelvis on any frame where some vertex would go below z = 0.

Biomechanics (timings at 60 fps)
  Gather   the rear knee needs the front foot ~0.7 m ahead of the rear ball (thigh ~vertical, rear
           shin ~horizontal, front shin <= 35 deg forward - boots limit dorsiflexion), so: weight to
           the left, the right foot steps back 0.42 m onto its ball (heel stays up), the left foot
           slides 0.24 m forward, the pelvis sinks ~0.45 m while the right heel rises over the ball
           (toes tucked, toe bone flat) and the knee lands softly (spring, calibrated to touch z=0);
           the torso folds ~55 deg, the left hand props on the left knee, the right arm reaches, the
           fingers spread, touch the snow, close in a cascade (grab), the hand comes up in front of
           the face, palm up, turns the find over while head and eyes track it, brows lift; standing:
           push through the front leg (forward lean first), the rear foot steps back in, then the
           front foot, settle.
  Attack   0.00-0.40 anticipation: weight back onto the right leg, hips and chest wind right, the
           back arches, the tool is cocked behind the head (elbow high), the left arm reaches forward
           as a guide; 0.40-0.54 strike: hips fire first, then chest, shoulder, elbow, wrist (proximal
           to distal whip); pelvis drops 7 cm and drives onto the left leg, the right heel peels off
           the ground; 0.54 impact: the tool stops dead (recoil spring), jaw clenched -> grunt;
           0.54-0.78 follow-through / settle, left arm pulled back to the hip; 0.78-1.30 recovery.
  Throw    lift the spear to the shoulder, draw back (arm extended behind, spear along the arm,
           chest wound 50 deg right, weight back), the left foot strides 0.40 m; hips open before the
           chest (hip-shoulder separation), elbow leads the hand, the fingers open at the release
           (0.97 s) and the spear leaves along its shaft; the arm follows through across the body to
           the left hip, the right heel lifts, the weight moves back, the left foot steps back in.
  WarmHands  (loop) shoulders hunched and protracted, head down, knees soft; the gloves are rubbed
           together (hands slide in anti-phase, 2.5 Hz), then cupped in front of the mouth: inhale
           (chest rises), blow (jaw open, head dips into the hands, chest sinks), rub again; the
           weight rocks between the feet and the unloaded heel lifts; a 7-12 Hz shiver on the trunk,
           shoulders and arms, teeth chatter on the jaw, squinting eyes.
  Hurt     hit on the front-left: the chest is pushed back and turned left (the left shoulder goes
           back), the body bends away to the right, the pelvis gives 4 cm, knees buckle; the head
           lags then whips; the left arm comes up to guard, the right arm flares for balance, fingers
           splay; wince: eyes squeezed shut, brows down, jaw clenched then a short grunt; springy
           recovery with a small overshoot.
  Death    shock (head up, brows up, jaw drops), the knees buckle (pelvis falls 0.5 m, heels rise over
           the balls, toes tucked), the knees hit the snow at 0.50 s with a small rebound; the upper
           body topples forward about the knees under gravity (theta'' = g/L sin theta) and rolls a
           little onto the left side; limp arms trail, the chest lands at ~1.1 s, the head (turned to
           the left) and arms flop and bounce twice, the hood slaps down, a last breath out, still.

STATUS / TODO (checkpoint)
  done   all 6 clips build and bake (Gather 210, Attack 78, Throw 114, WarmHands 240 loop, Hurt 48,
         Death 156 frames); the chain runs on the stub with Human_Idle from human_anim_locomotion.py;
         QA passes for these clips: one-shots start/end on Idle frame 0, no foot slip over 1.5 mm/frame,
         death settles with torso / arms / feet / head each calibrated onto z = 0. 2-3 strip critique
         passes per clip (Gather reach, Death lying pose, Attack / Throw tool orientation).
  left   - verify the latest Throw right-foot yaw (5 deg) keeps the toe tip under 1.5 mm/frame
         - 3rd critique pass on Hurt / WarmHands / Attack timing with the tool visible
         - re-run everything on Human_Rigged.blend once it exists (calibrations adapt to the mesh)
         - remove the debug 'lie calib' print in death()
  note   Human_Stub.blend has broken weights (capsule islands split across bones); dev used a
         scratch copy with each island reassigned to its nearest bone.
"""
import bpy, math, sys
import numpy as np
from mathutils import Vector as V, Quaternion as Q, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None
FPS = 60
DT = 1.0 / FPS
TAU = 2 * math.pi
G = 9.81

scene = bpy.context.scene
scene.render.fps = FPS
arm = bpy.data.objects["HumanRig"]
mesh = bpy.data.objects.get("Human")
pb = arm.pose.bones
if arm.animation_data is None:
    arm.animation_data_create()
for a in bpy.data.actions:
    if a.name.startswith("Human_"):
        a.use_fake_user = True
for p_ in pb:
    p_.rotation_mode = 'QUATERNION'
if arm.matrix_world != Matrix():
    print("[human extra] WARNING: HumanRig object transform is not identity - ground contact assumes it is")
SIDES = (("L", 1), ("R", -1))
X, Y, Z = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))
FING = ("index", "middle", "ring", "pinky")
DIGITS = FING + ("thumb",)
CURL_W = {"index": (1.0, 1.1, 0.75), "middle": (1.0, 1.1, 0.75), "ring": (1.0, 1.1, 0.75),
          "pinky": (1.0, 1.1, 0.75), "thumb": (0.35, 0.8, 0.7)}
SPREAD_W = {"index": 1.0, "middle": 0.0, "ring": -0.7, "pinky": -1.3, "thumb": 0.8}


# ======================================================================= math helpers
def rad(d):
    return math.radians(d)


def clamp(x, a, b):
    return max(a, min(b, x))


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def minjerk(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * t * (10 - 15 * t + 6 * t * t)


def bump(e0, e1, x, p=1.0):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return np.sin(math.pi * t) ** p


def pchip(kv, t, periodic=False):
    """Monotone cubic (Fritsch-Carlson) through (time, value) keys: smooth velocity through the
    keys, no overshoot, zero slope at the ends (or periodic slopes for loops)."""
    kt = np.array([k[0] for k in kv], float)
    kv_ = np.array([k[1] for k in kv], float)
    t = np.asarray(t, float)
    if len(kt) == 1:
        return np.full(t.shape, kv_[0])
    h = np.diff(kt)
    d = np.diff(kv_) / h
    m = np.zeros(len(kt))

    def harm(d0, d1, h0, h1):
        if d0 * d1 <= 0:
            return 0.0
        w1, w2 = 2 * h1 + h0, h1 + 2 * h0
        return (w1 + w2) / (w1 / d0 + w2 / d1)

    for k in range(1, len(kt) - 1):
        m[k] = harm(d[k - 1], d[k], h[k - 1], h[k])
    if periodic:
        m[0] = m[-1] = harm(d[-1], d[0], h[-1], h[0])
    idx = np.clip(np.searchsorted(kt, t, side='right') - 1, 0, len(kt) - 2)
    hh = h[idx]
    s = np.clip((t - kt[idx]) / hh, 0.0, 1.0)
    s2, s3 = s * s, s * s * s
    out = ((2 * s3 - 3 * s2 + 1) * kv_[idx] + (s3 - 2 * s2 + s) * hh * m[idx]
           + (-2 * s3 + 3 * s2) * kv_[idx + 1] + (s3 - s2) * hh * m[idx + 1])
    out = np.where(t <= kt[0], kv_[0], out)
    return np.where(t >= kt[-1], kv_[-1], out)


def dkeys(kv, t, periodic=False):
    """pchip through keys given in degrees -> radians."""
    return np.radians(pchip(kv, t, periodic))


def vkeys(kv, t, periodic=False):
    """pchip through 3-vector keys -> (n, 3) array."""
    return np.stack([pchip([(k[0], k[1][c]) for k in kv], t, periodic) for c in range(3)], axis=1)


def qkeys(kv, t, periodic=False):
    """Orientation keys (time, Quaternion) -> list of Quaternions: rotation vectors relative to the
    first key, interpolated with pchip (smooth angular velocity through the keys)."""
    q0 = kv[0][1].normalized()
    rv = []
    prev = None
    for tk, q in kv:
        d = q0.inverted() @ q.normalized()
        if d.w < 0:
            d.negate()
        ax, an = d.to_axis_angle()
        r = np.array(ax) * an
        rv.append(r)
        prev = r
    arr = np.stack([pchip([(k[0], r[c]) for k, r in zip(kv, rv)], t, periodic) for c in range(3)], axis=1)
    out = []
    for r in arr:
        an = float(np.linalg.norm(r))
        out.append(q0 @ (Q(V(r / an), an) if an > 1e-9 else Q()))
    return out


def spring(u, hz, zeta, loop=False, lo=None, hi=None, bounce=0.35, cycles=5, sub=4, x0=None):
    """Damped spring x'' = w^2 (u - x) - 2 zeta w x' following the input array u (orca_anim_extra.py).
    loop: u is periodic (u[0] == u[-1]): simulate several cycles, keep the settled last one and remove
    the residual so out[0] == out[-1]. lo / hi: hard stops the spring rebounds from."""
    u = np.asarray(u, float)
    w = TAU * hz
    h = DT / sub
    x, v = float(u[0] if x0 is None else x0), 0.0
    seq = np.concatenate([np.tile(u[:-1], cycles), u[:1]]) if loop else u
    out = np.empty(len(seq))
    prev = seq[0]
    for i, target in enumerate(seq):
        for k in range(sub):
            tg = prev + (target - prev) * (k + 1) / sub
            a = w * w * (tg - x) - 2 * zeta * w * v
            v += a * h
            x += v * h
            if lo is not None and x < lo:
                x, v = lo, -v * bounce
            if hi is not None and x > hi:
                x, v = hi, -v * bounce
        prev = target
        out[i] = x
    if loop:
        n = len(u) - 1
        out = out[-(n + 1):].copy()
        out -= (out[-1] - out[0]) * np.linspace(0, 1, n + 1)
    return out


def vspring(u, hz, zeta, loop=False):
    return np.stack([spring(u[:, c], hz, zeta, loop) for c in range(u.shape[1])], axis=1)


def ddt(a, loop=False):
    a = np.asarray(a, float)
    if loop:
        b = a[:-1]
        d = (np.roll(b, -1, axis=0) - np.roll(b, 1, axis=0)) / (2 * DT)
        return np.concatenate([d, d[:1]], axis=0)
    return np.gradient(a, DT, axis=0)


def armq(*rots):
    """Compose armature-space rotations given as (axis, angle), applied right to left."""
    q = Q()
    for axis, ang in rots:
        if ang:
            q = q @ Q(V(axis).normalized(), float(ang))
    return q


def frame_q(x, y):
    """Orthonormal frame with Y along y and X as close as possible to x -> quaternion."""
    y = y.normalized()
    x = (x - x.dot(y) * y).normalized()
    z = x.cross(y)
    return Matrix((x, y, z)).transposed().to_quaternion()


def basis2(a, b):
    a = a.normalized()
    b = (b - b.dot(a) * a).normalized()
    return Matrix((a, b, a.cross(b))).transposed()


def blinks(T, times, close=0.055, hold=0.03, open_=0.11):
    """0..1 lid closure: fast close, short hold, slower open."""
    out = np.zeros_like(T)
    for t0 in times:
        up = smoothstep(t0, t0 + close, T)
        dn = 1 - smoothstep(t0 + close + hold, t0 + close + hold + open_, T)
        out = np.maximum(out, np.minimum(up, dn))
    return out


# ======================================================================= rig tables (read at runtime)
BONES = arm.data.bones
NAMES = [b.name for b in BONES]
HAS = set(NAMES)
PARENT = {b.name: (b.parent.name if b.parent else None) for b in BONES}
ORDER = []


def _visit(b):
    ORDER.append(b.name)
    for c in b.children:
        _visit(c)


for b in BONES:
    if b.parent is None:
        _visit(b)
RESTM = {n: BONES[n].matrix_local.copy() for n in ORDER}
RESTQ = {n: RESTM[n].to_quaternion() for n in ORDER}
REL = {n: (RESTM[PARENT[n]].inverted() @ RESTM[n]) if PARENT[n] else RESTM[n].copy() for n in ORDER}
LEN = {n: BONES[n].length for n in ORDER}
CHILDREN = {n: [] for n in ORDER}
for n in ORDER:
    if PARENT[n]:
        CHILDREN[PARENT[n]].append(n)


def subtree(n):
    out = [n]
    for c in CHILDREN[n]:
        out += subtree(c)
    return out


def dq(n, *rots):
    """Local rotation equal to armature-space rotations measured in the bone's rest frame."""
    r = RESTQ[n]
    return r.inverted() @ armq(*rots) @ r


def _fcurves(act):
    if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])):
        return act.fcurves
    out = []
    for layer in getattr(act, "layers", []):
        for strip in layer.strips:
            for bag in strip.channelbags:
                out.extend(bag.fcurves)
    return out


# ======================================================================= pose + FK
class Pose:
    def __init__(self, src=None):
        if src is None:
            self.q = {n: Q() for n in ORDER}
            self.l = {n: V() for n in ORDER}
        else:
            self.q = {n: q.copy() for n, q in src.q.items()}
            self.l = {n: l.copy() for n, l in src.l.items()}

    def copy(self):
        return Pose(self)


def bmat(P, n):
    return Matrix.Translation(P.l[n]) @ P.q[n].to_matrix().to_4x4()


def fk(P, names=None, M=None):
    """Armature-space matrices; names must be in parent-first order (any subset whose parents are in M)."""
    M = {} if M is None else M
    for n in (names or ORDER):
        p = PARENT[n]
        M[n] = ((M[p] @ REL[n]) if p else REL[n]) @ bmat(P, n)
    return M


def parent_frame(M, n):
    p = PARENT[n]
    return (M[p] @ REL[n]) if p else REL[n]


def set_rot(P, M, n, qw):
    """Give bone n the armature-space orientation qw (keeps its location)."""
    P.q[n] = parent_frame(M, n).to_quaternion().inverted() @ qw
    fk(P, subtree(n), M)


# ======================================================================= IK
IK_CLAMPED = {}


def two_bone(P, M, up, lo, target, pole, tag=""):
    """Analytic two-bone IK baked to FK: 'lo' ends on target (clamped to reach), the joint bends
    toward 'pole' (armature-space direction), the hinge axis becomes both bones' local X, which is
    the rig's hinge axis for knees / elbows."""
    F0 = parent_frame(M, up)
    H = F0.translation
    l1, l2 = LEN[up], LEN[lo]
    d = target - H
    dist = d.length
    lim = (l1 + l2) * 0.99995
    if dist > lim:
        IK_CLAMPED[tag] = max(IK_CLAMPED.get(tag, 0.0), dist - lim)
    dist = clamp(dist, abs(l1 - l2) + 1e-4, lim)
    dn = d.normalized()
    ca = clamp((l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist), -1.0, 1.0)
    a = math.acos(ca)
    pp = pole - pole.dot(dn) * dn
    if pp.length < 1e-6:
        pp = dn.orthogonal()
    pp.normalize()
    u1 = math.cos(a) * dn + math.sin(a) * pp
    K = H + l1 * u1
    E = H + dn * dist
    u2 = (E - K).normalized()
    h = dn.cross(pp).normalized()
    r0 = F0.to_3x3()
    xr = r0.col[1].rotation_difference(u1) @ r0.col[0]
    if h.dot(xr) < 0:
        h = -h
    P.q[up] = F0.to_quaternion().inverted() @ frame_q(h, u1)
    fk(P, [up], M)
    F1 = parent_frame(M, lo)
    P.q[lo] = F1.to_quaternion().inverted() @ frame_q(h, u2)
    fk(P, subtree(up), M)
    return K


def twist_about_y(q):
    """Angle of the twist component of local rotation q about its local Y axis."""
    return 2.0 * math.atan2(q.y, q.w)


def solve_arm(P, M, sd, wrist, pole, handq, twist_share=0.5):
    up, lo, hand = f"upper_arm.{sd}", f"forearm.{sd}", f"hand.{sd}"
    two_bone(P, M, up, lo, wrist, pole, "arm." + sd)
    set_rot(P, M, hand, handq)
    tw = twist_about_y(P.q[hand])
    if abs(tw) > 1e-4 and twist_share:
        u2 = M[lo].to_3x3().col[1].normalized()
        set_rot(P, M, lo, Q(u2, twist_share * tw) @ M[lo].to_quaternion())
        set_rot(P, M, hand, handq)


def solve_leg(P, M, sd, ankle, pole, footq, toeq):
    two_bone(P, M, f"thigh.{sd}", f"shin.{sd}", ankle, pole, "leg." + sd)
    set_rot(P, M, f"foot.{sd}", footq)
    set_rot(P, M, f"toe.{sd}", toeq)


# ======================================================================= hands
HAND_SHAFT = {}      # prop socket Y (tool shaft) in the hand's local frame
for sd, s in SIDES:
    hm = RESTM[f"hand.{sd}"].to_3x3()
    HAND_SHAFT[sd] = (hm.inverted() @ RESTM[f"prop.{sd}"].to_3x3().col[1]).normalized()


def hand_q(sd, fingers=None, palm=None, shaft=None):
    """Armature-space hand orientation from (fingers direction, palm normal) or (tool shaft, palm)."""
    if shaft is not None:
        w = basis2(V(shaft), V(palm))
        l = basis2(HAND_SHAFT[sd], V((0, 0, 1)))
        return (w @ l.transposed()).to_quaternion()
    return frame_q(V(fingers).cross(V(palm)), V(fingers))


def q_arr(qs):
    return np.array([[q.w, q.x, q.y, q.z] for q in qs])


def arr_q(a):
    return Q((float(a[0]), float(a[1]), float(a[2]), float(a[3])))


# ======================================================================= Idle frame 0
def read_idle0():
    act = bpy.data.actions.get("Human_Idle")
    if act is None:
        return None, set()
    P = Pose()
    locs = set()
    f0 = act.frame_range[0]
    for fc in _fcurves(act):
        path = fc.data_path
        if not path.startswith('pose.bones["'):
            continue
        n = path.split('"')[1]
        if n not in P.q:
            continue
        v = fc.evaluate(f0)
        if path.endswith("rotation_quaternion"):
            P.q[n][fc.array_index] = v
        elif path.endswith("location"):
            P.l[n][fc.array_index] = v
            locs.add(n)
    for n in ORDER:
        P.q[n].normalize()
    return P, locs


def neutral_stand():
    """Fallback idle: natural relaxed stand - soft knees (pelvis 1.2 cm down), arms hanging at the
    sides slightly away from the bulky parka, palms toward the thighs, fingers relaxed."""
    P = Pose()
    P.l["pelvis"] = RESTQ["pelvis"].inverted() @ V((0, 0.004, -0.012))
    for n, k in (("spine_01", -1.0), ("spine_02", 0.5), ("spine_03", 1.5), ("neck", 3.0), ("head", -3.5)):
        P.q[n] = dq(n, (X, rad(k)))
    M = fk(P)
    for sd, s in SIDES:
        a0 = RESTM[f"shin.{sd}"].to_translation() + (RESTM[f"shin.{sd}"].to_3x3().col[1] * LEN[f"shin.{sd}"])
        solve_leg(P, M, sd, a0, V((0.08 * s, -1, 0)), RESTQ[f"foot.{sd}"], RESTQ[f"toe.{sd}"])
        sh = M[f"upper_arm.{sd}"].translation
        wrist = sh + V((0.085 * s, -0.045, -0.515))
        hq = hand_q(sd, fingers=V((0.12 * s, -0.10, -1)), palm=V((-s, 0.25, 0.0)))
        solve_arm(P, M, sd, wrist, V((0.35 * s, 1.0, 0.0)), hq)
        for f in DIGITS:
            for k in range(3):
                n = f"{f}_0{k + 1}.{sd}"
                P.q[n] = Q(V((1, 0, 0)), rad(9) * CURL_W[f][k] * (0.6 if f == "thumb" else 1.0))
    return P


IDLE0, IDLE_LOCS = read_idle0()
IDLE_SRC = "Human_Idle frame 0"
if IDLE0 is None:
    IDLE0 = neutral_stand()
    IDLE_SRC = "fallback neutral stand (no Human_Idle action yet)"
KEY_LOC = {"root", "pelvis"} | IDLE_LOCS
M0 = fk(IDLE0)

# measurements of the idle pose (armature space)
EYE_MID0 = (M0["eye.L"].translation + M0["eye.R"].translation) / 2
EYE_IN_HEAD = M0["head"].inverted() @ EYE_MID0
PELV_HEAD0 = M0["pelvis"].translation.copy()
CHEST0 = M0["spine_03"].copy()
CHEST0_INV = CHEST0.inverted()
WRIST0, HANDQ0, EPOLE0, SHOULDER0 = {}, {}, {}, {}
ANKLE0, FOOTQ0, TOEQ0, BALL0, HEEL0, KPOLE0, TIP0 = {}, {}, {}, {}, {}, {}, {}
for sd, s in SIDES:
    sh = M0[f"upper_arm.{sd}"].translation
    el = M0[f"forearm.{sd}"].translation
    wr = M0[f"hand.{sd}"].translation
    SHOULDER0[sd] = sh.copy()
    WRIST0[sd] = wr.copy()
    HANDQ0[sd] = M0[f"hand.{sd}"].to_quaternion()
    dn = (wr - sh).normalized()
    e = el - sh
    EPOLE0[sd] = (e - e.dot(dn) * dn).normalized()
    hp = M0[f"thigh.{sd}"].translation
    kn = M0[f"shin.{sd}"].translation
    an = M0[f"foot.{sd}"].translation
    ANKLE0[sd] = an.copy()
    FOOTQ0[sd] = M0[f"foot.{sd}"].to_quaternion()
    TOEQ0[sd] = M0[f"toe.{sd}"].to_quaternion()
    BALL0[sd] = M0[f"toe.{sd}"].translation.copy()
    TIP0[sd] = M0[f"toe.{sd}"] @ V((0, LEN[f"toe.{sd}"], 0))
    fwd = BALL0[sd] - an
    fwd.z = 0
    fwd.normalize()
    HEEL0[sd] = V((an.x, an.y, BALL0[sd].z)) - fwd * 0.055
    dn = (an - hp).normalized()
    e = kn - hp
    KPOLE0[sd] = (e - e.dot(dn) * dn).normalized() if (e - e.dot(dn) * dn).length > 1e-4 else V((0, -1, 0))
LOOK0 = EYE_MID0 + V((0, -4.0, -0.25))
FOOT_FWD = {sd: (BALL0[sd] - HEEL0[sd]).normalized() for sd, _ in SIDES}


# ======================================================================= mesh contact (runtime calibration)
DOM = None
BONE_INDEX = {n: i for i, n in enumerate(ORDER)}


def _dominant():
    """Dominant deform bone per vertex of the skinned mesh (index into ORDER, -1 = none)."""
    global DOM
    if DOM is not None or mesh is None:
        return DOM
    gi = {g.index: BONE_INDEX.get(g.name, -1) for g in mesh.vertex_groups}
    nv = len(mesh.data.vertices)
    DOM = np.full(nv, -1, np.int32)
    best = np.zeros(nv)
    for v in mesh.data.vertices:
        for g in v.groups:
            if g.weight > best[v.index] and gi.get(g.group, -1) >= 0:
                best[v.index] = g.weight
                DOM[v.index] = gi[g.group]
    return DOM


def push(P):
    for n in ORDER:
        pb[n].matrix_basis = bmat(P, n)
    bpy.context.view_layer.update()


def mesh_z(P, bones=None):
    """Lowest world z of the deformed mesh (optionally only vertices whose dominant bone is in 'bones')."""
    if mesh is None:
        return 0.0
    push(P)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    ev.to_mesh_clear()
    co = co.reshape(-1, 3)
    mw = np.array(mesh.matrix_world, np.float64)
    z = co @ mw[2, :3] + mw[2, 3]
    if bones:
        dom = _dominant()
        ids = [BONE_INDEX[b] for b in bones if b in BONE_INDEX]
        if dom is not None and len(dom) == len(z):
            m = np.isin(dom, ids)
            if m.any():
                z = z[m]
    return float(z.min())


REST_MINZ = None


# ======================================================================= channels -> pose
def clip_time(n):
    return np.arange(n + 1) * DT


def base_channels(n):
    """Every channel at its idle value: scalars 0 (offsets), vectors / orientations at the idle pose."""
    C = {"n": n}
    for sd, s in SIDES:
        C[f"{sd}_wrist"] = np.tile(np.array(WRIST0[sd]), (n + 1, 1))
        C[f"{sd}_wsp"] = np.ones(n + 1)                     # 1: target rides on the chest, 0: world
        C[f"{sd}_epole"] = np.tile(np.array(EPOLE0[sd]), (n + 1, 1))
        C[f"{sd}_handq"] = np.tile(np.array(HANDQ0[sd]), (n + 1, 1))
        C[f"{sd}_ball"] = np.tile(np.array(BALL0[sd]), (n + 1, 1))
        for k in ("phi", "psi", "air", "toe_flex", "kpole_x"):
            C[f"{sd}_{k}"] = np.zeros(n + 1)
    C["look"] = np.tile(np.array(LOOK0), (n + 1, 1))
    return C


def g(C, k, i, d=0.0):
    a = C.get(k)
    return d if a is None else float(a[i])


def gv(C, k, i):
    return V(C[k][i].tolist())


def foot_pose(C, i, sd):
    """Foot track -> (ankle target, foot orientation, toe orientation) in armature space."""
    ball = gv(C, f"{sd}_ball", i)
    phi, psi = g(C, f"{sd}_phi", i), g(C, f"{sd}_psi", i)
    air = g(C, f"{sd}_air", i)
    lat = Z.cross(FOOT_FWD[sd]).normalized()
    Ry = Q(Z, psi)
    R = Ry @ Q(lat, phi)
    b0 = BALL0[sd]
    if phi >= 0:
        piv0, piv = b0, ball
    else:
        piv0 = HEEL0[sd]
        piv = ball + Ry @ (HEEL0[sd] - b0)
    ankle = piv + R @ (ANKLE0[sd] - piv0)
    footq = R @ FOOTQ0[sd]
    toe_on_foot = R @ TOEQ0[sd]
    toe_flat = Ry @ TOEQ0[sd]
    if phi >= 0:
        toeq = toe_flat.slerp(toe_on_foot, clamp(air, 0.0, 1.0))
    else:
        toeq = toe_on_foot
    tf = g(C, f"{sd}_toe_flex", i)
    if tf:
        toeq = Q(R @ lat, -tf) @ toeq
    return ankle, footq, toeq


TRUNK_W = (("spine_01", 0.25), ("spine_02", 0.35), ("spine_03", 0.40))


def build(C, i, hood=(0.0, 0.0, 0.0)):
    """Pose of frame i from the channel arrays C."""
    P = IDLE0.copy()
    gg = lambda k, d=0.0: g(C, k, i, d)
    # ---- root (only Death moves it) + pelvis about its head (weight transfer)
    P.l["root"] = IDLE0.l["root"] + V((gg("rx"), gg("ry"), gg("rz")))
    M = fk(P, ["root"])
    Rp = armq((Z, gg("p_yaw")), (Y, gg("p_roll")), (X, gg("p_pitch")))
    d = V((gg("px"), gg("py"), gg("pz")))
    Wp = Matrix.Translation(PELV_HEAD0 + d) @ Rp.to_matrix().to_4x4() @ Matrix.Translation(-PELV_HEAD0) @ M0["pelvis"]
    Wp = M["root"] @ M0["root"].inverted() @ Wp
    loc, rq, _ = (parent_frame(M, "pelvis").inverted() @ Wp).decompose()
    P.q["pelvis"], P.l["pelvis"] = rq, loc
    # ---- trunk, neck, head, face bones, clavicles, hood
    lean, side, twist = gg("lean"), gg("side"), gg("twist")
    shv = gg("shiver")
    for n, k in TRUNK_W:
        P.q[n] = IDLE0.q[n] @ dq(n, (Z, twist * k + gg(f"{n}_yaw")), (Y, side * k + gg(f"{n}_roll")),
                                 (X, lean * k + gg(f"{n}_pitch")))
    P.q["neck"] = IDLE0.q["neck"] @ dq("neck", (Z, gg("n_yaw")), (Y, gg("n_roll")), (X, gg("n_pitch")))
    P.q["head"] = IDLE0.q["head"] @ dq("head", (Z, gg("h_yaw")), (Y, gg("h_roll")), (X, gg("h_pitch")))
    P.q["jaw"] = IDLE0.q["jaw"] @ dq("jaw", (X, gg("jaw")), (Z, gg("jaw_side")))
    hp, hr, hp2 = hood
    if "hood_01" in HAS:
        P.q["hood_01"] = IDLE0.q["hood_01"] @ dq("hood_01", (Y, hr), (X, hp))
        P.q["hood_02"] = IDLE0.q["hood_02"] @ dq("hood_02", (Y, 0.6 * hr), (X, hp2))
    for sd, s in SIDES:
        P.q[f"clavicle.{sd}"] = IDLE0.q[f"clavicle.{sd}"] @ dq(
            f"clavicle.{sd}", (Z, -s * gg(f"{sd}_cfwd")), (Y, -s * gg(f"{sd}_cup")))
    M = fk(P)
    # ---- legs (IK on the foot track; the knee pole turns with the hips)
    Rpel = M["pelvis"].to_quaternion() @ M0["pelvis"].to_quaternion().inverted()
    for sd, s in SIDES:
        ankle, footq, toeq = foot_pose(C, i, sd)
        pole = Rpel @ (KPOLE0[sd] + V((s * gg(f"{sd}_kpole_x"), 0, 0)))
        solve_leg(P, M, sd, ankle, pole, footq, toeq)
    # ---- arms (IK; targets in the chest frame or in armature space)
    Cs = M["spine_03"] @ CHEST0_INV
    Csq = Cs.to_quaternion()
    for sd, s in SIDES:
        w = gg(f"{sd}_wsp", 1.0)
        tw = gv(C, f"{sd}_wrist", i)
        tgt = (Cs @ tw) * w + tw * (1 - w)
        hq = arr_q(C[f"{sd}_handq"][i]).normalized()
        wq = gg(f"{sd}_qsp", w) if f"{sd}_qsp" in C else w     # orientation space (default = target's)
        hq = Q().slerp(Csq, wq) @ hq
        # hand on the knee (Gather): follow the thigh just above the knee
        kw = gg(f"{sd}_onknee")
        if kw > 0:
            kn = M[f"shin.{sd}"].translation
            th = M[f"thigh.{sd}"].to_3x3()
            on = kn - th.col[1] * 0.06 + th.col[2] * 0.075 + V((0.015 * s, 0, 0))
            tgt = tgt.lerp(on, kw)
        # clavicle follows the hand: shrug when above the shoulder, protract when reaching forward
        sh = M[f"upper_arm.{sd}"].translation
        dv = (tgt - sh)
        dv_c = Csq.inverted() @ dv
        el = math.degrees(math.atan2(dv_c.z, math.hypot(dv_c.x, dv_c.y)))
        up = rad(0.30 * clamp(el + 25.0, 0.0, 115.0)) + gg(f"{sd}_cup")
        fw = rad(0.22 * clamp(math.degrees(math.atan2(-dv_c.y, abs(dv_c.x) + 1e-6)), -10, 70)) + gg(f"{sd}_cfwd")
        P.q[f"clavicle.{sd}"] = IDLE0.q[f"clavicle.{sd}"] @ dq(f"clavicle.{sd}", (Z, -s * fw), (Y, -s * up))
        fk(P, subtree(f"clavicle.{sd}"), M)
        pole = Csq @ gv(C, f"{sd}_epole", i)
        solve_arm(P, M, sd, tgt, pole, hq)
        # fingers: curl (radians per segment, cascade handled in the channels) + spread
        for f in DIGITS:
            c = gg(f"{sd}_curl_{f}")
            sp = gg(f"{sd}_spread") * SPREAD_W[f] * s
            for k in range(3):
                nm = f"{f}_0{k + 1}.{sd}"
                if nm in HAS:
                    P.q[nm] = IDLE0.q[nm] @ Q(V((1, 0, 0)), c * CURL_W[f][k]) @ (
                        Q(V((0, 0, 1)), sp) if k == 0 else Q())
        fk(P, subtree(f"hand.{sd}"), M)
    # ---- head aim at the look target (neck takes 35 %), eyes finish the job
    lw = gg("look_w")
    tgt = gv(C, "look", i)
    lh = gg("look_hand")
    if lh > 0:
        tgt = tgt.lerp(M["hand.R"] @ V((0, 0.07, 0.03)), lh)
    if lw > 0:
        for n, share in (("neck", 0.35), ("head", 1.0)):
            eye = M["head"] @ EYE_IN_HEAD
            fwd = M["head"].to_3x3().col[2].normalized()
            want = (tgt - eye).normalized()
            rd = fwd.rotation_difference(want)
            ang = rd.angle
            lim = rad(75)
            if ang > lim:
                rd = Q().slerp(rd, lim / ang)
            rd = Q().slerp(rd, lw * (share if n == "neck" else 1.0))
            set_rot(P, M, n, rd @ M[n].to_quaternion())
        # re-apply the head offsets on top of the aim (secondary lag, nods)
    ew = gg("eye_w")
    e_pitch_total = gg("e_pitch")
    for sd, s in SIDES:
        n = f"eye.{sd}"
        if n not in HAS:
            continue
        q = IDLE0.q[n] @ dq(n, (Z, gg("e_yaw")), (X, gg("e_pitch")))
        P.q[n] = q
        fk(P, [n], M)
        if ew > 0:
            e = M[n].translation
            fwd = M[n].to_3x3().col[1].normalized()
            want = (tgt - e).normalized()
            rd = fwd.rotation_difference(want)
            if rd.angle > rad(30):
                rd = Q().slerp(rd, rad(30) / rd.angle)
            rd = Q().slerp(rd, ew)
            set_rot(P, M, n, rd @ M[n].to_quaternion())
    # eye pitch relative to the head (for the lids to follow)
    ep = 0.0                                  # + = eyes look down (head frame: Y up, Z forward)
    if "eye.L" in HAS:
        e_loc = M["head"].to_3x3().inverted() @ M["eye.L"].to_3x3().col[1].normalized()
        e_rest = M0["head"].to_3x3().inverted() @ M0["eye.L"].to_3x3().col[1].normalized()
        ep = math.asin(clamp(e_rest.y, -1, 1)) - math.asin(clamp(e_loc.y, -1, 1))
    blink = clamp(gg("blink"), 0.0, 1.0)
    squint = gg("squint")
    for sd, s in SIDES:
        up_close = rad(30) * blink + rad(9) * squint + 0.55 * max(-rad(25), min(rad(25), ep))
        lo_close = rad(8) * blink + rad(7) * squint
        for n, ang in ((f"lid_upper.{sd}", up_close), (f"lid_lower.{sd}", -lo_close)):
            if n in HAS:
                P.q[n] = IDLE0.q[n] @ dq(n, (X, ang))
        n = f"brow.{sd}"
        if n in HAS:
            P.q[n] = IDLE0.q[n] @ dq(n, (X, -gg("brow") + rad(3) * squint), (Z, s * gg("brow_in")))
    return P


# ======================================================================= secondary: hood
def hood_channels(C, n, loop):
    """Pass 1: the chest's motion without the hood -> the hood's swing off the back (+) through
    springs with a hard stop on the back. Driven by the acceleration of the hood root in the chest
    frame (inertia: the chest accelerates forward -> the hood lags back / off the back) and by
    gravity once the torso leans forward (the hood hangs toward vertical)."""
    if "hood_01" not in HAS:
        return np.zeros((n + 1, 3))
    pos, fwd_acc, lat_acc, tilt, rot = [], [], [], [], []
    for i in range(n + 1):
        P = build(C, i)
        M = fk(P)
        m = M["spine_03"]
        pos.append(np.array(M["hood_01"].translation))
        rot.append(m.to_3x3())
        y = m.to_3x3().col[1]                  # chest "up" axis
        tilt.append(math.atan2(-y.y, y.z))     # + = leaning forward (toward -Y)
    pos = np.array(pos)
    acc = ddt(ddt(pos, loop), loop)
    for i in range(n + 1):
        a = rot[i].inverted() @ V(acc[i].tolist())
        fwd_acc.append(-a.z)                   # chest local Z = forward -> accel along the facing
        lat_acc.append(a.x)
    fwd_acc, lat_acc, tilt = np.array(fwd_acc), np.array(lat_acc), np.array(tilt)
    t0 = tilt[0] if not loop else float(np.mean(tilt))
    grav = np.clip(0.75 * (tilt - t0), 0.0, rad(70)) * (tilt < rad(80))
    u = grav + np.clip(0.030 * fwd_acc, -rad(8), rad(35))
    hp = spring(u, 2.2, 0.28, loop, lo=-rad(2), bounce=0.35)
    hp2 = spring(0.55 * hp + 0.25 * (hp - spring(hp, 3.0, 0.3, loop)), 3.2, 0.3, loop, lo=-rad(3), bounce=0.3)
    hr = spring(np.clip(-0.025 * lat_acc, -rad(20), rad(20)), 1.9, 0.25, loop)
    return np.stack([hp, hr, hp2], axis=1)


# ======================================================================= bake
def begin(name):
    old = bpy.data.actions.get(name)
    if old:
        bpy.data.actions.remove(old)
    arm.animation_data.action = None


def key_pose(P, f):
    for n in ORDER:
        p_ = pb[n]
        p_.rotation_quaternion = P.q[n]
        p_.keyframe_insert("rotation_quaternion", frame=f)
        if n in KEY_LOC:
            p_.location = P.l[n]
            p_.keyframe_insert("location", frame=f)


def finish(name, n, cyclic, props=None):
    act = arm.animation_data.action
    act.name = name
    act.use_fake_user = True
    act.use_frame_range = True
    act.frame_start, act.frame_end = 0, n
    act.use_cyclic = cyclic
    for k, v in (props or {}).items():
        act[k] = v
    for fc in _fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    arm.animation_data.action = None
    for p_ in pb:
        p_.matrix_basis = Matrix()
    print(f"[human extra] {name}: {n} frames ({n / FPS:.2f} s){' loop' if cyclic else ''}")
    return act


def bake(name, C, cyclic=False, blend_in=0.10, blend_out=0.25, hold=(), hold_end=(), props=None,
         lift=None, end_blend=True):
    """Build every frame from the channels (2 passes: hood secondary motion), blend one-shots onto the
    exact idle bone pose at the ends, key every bone on every frame."""
    n = C["n"]
    T = clip_time(n)
    hood = hood_channels(C, n, cyclic)
    if cyclic:
        w = np.ones(n + 1)
    else:
        w = smoothstep(0, blend_in, T)
        if end_blend:
            w = np.minimum(w, 1 - smoothstep(n * DT - blend_out, n * DT, T))
    hold, hold_end = set(hold), set(hold_end)
    begin(name)
    poses = []
    for i in range(n + 1):
        P = build(C, i, tuple(hood[i]))
        if lift is not None and lift[i]:
            P.l["root"] = P.l["root"] + V((0, 0, float(lift[i])))
        wi = float(w[i])
        if wi < 1.0:
            for b in ORDER:
                wb = wi
                if b in hold and (T[i] < n * DT / 2 or b in hold_end):
                    wb = 1.0
                P.q[b] = IDLE0.q[b].slerp(P.q[b], wb) if IDLE0.q[b].dot(P.q[b]) >= 0 else \
                    (-IDLE0.q[b]).slerp(P.q[b], wb)
                P.l[b] = IDLE0.l[b].lerp(P.l[b], wb)
        key_pose(P, i)
        poses.append(P)
    act = finish(name, n, cyclic, props)
    return act, poses


# ======================================================================= shared clip helpers
def step_track(C, sd, T, steps, phi_keys=None, psi_keys=None, toe_keys=None):
    """Foot track: steps = [(t0, t1, (dx, dy), lift)] moves of the ball (min-jerk, lift arc);
    phi_keys (deg, + heel up about the ball, - toes up about the heel); air = off the ground."""
    ball = np.tile(np.array(BALL0[sd]), (len(T), 1))
    off = np.zeros((len(T), 3))
    acc = np.zeros(3)
    air = np.zeros(len(T))
    for t0, t1, (dx, dy), lift in steps:
        u = minjerk(t0, t1, T)[:, None]
        off = off + u * np.array([dx, dy, 0.0])
        ar = bump(t0, t1, T, 0.8)
        # lift: quick off the ground, a little lower before landing (toe clearance, then reach)
        off[:, 2] += lift * ar * (1 + 0.25 * np.sin(math.pi * np.clip((T - t0) / (t1 - t0), 0, 1)) * 0)
        L_ = t1 - t0          # toes follow the foot only well clear of the snow (flat at toe-off / landing)
        air = np.maximum(air, smoothstep(t0 + 0.2 * L_, t0 + 0.45 * L_, T) * (1 - smoothstep(t1 - 0.45 * L_, t1 - 0.2 * L_, T)))
    C[f"{sd}_ball"] = ball + off
    C[f"{sd}_air"] = air
    if phi_keys:
        C[f"{sd}_phi"] = dkeys(phi_keys, T)
    if psi_keys:
        C[f"{sd}_psi"] = dkeys(psi_keys, T)
    if toe_keys:
        C[f"{sd}_toe_flex"] = dkeys(toe_keys, T)


def finger_channels(C, sd, T, curl_keys, spread_keys=None, thumb_keys=None, rates=None, loop=False,
                    zeta=0.55):
    """Finger curl (deg per segment) through springs with different rates: index leads, pinky
    trails -> cascades; thumb separately."""
    base = dkeys(curl_keys, T, loop)
    rates = rates or {"index": 9.0, "middle": 8.0, "ring": 7.0, "pinky": 6.0, "thumb": 8.5}
    for f in FING:
        C[f"{sd}_curl_{f}"] = spring(base, rates[f], zeta, loop)
    th = dkeys(thumb_keys, T, loop) if thumb_keys else base * 0.8
    C[f"{sd}_curl_thumb"] = spring(th, rates["thumb"], zeta, loop)
    if spread_keys:
        C[f"{sd}_spread"] = spring(dkeys(spread_keys, T, loop), 7.0, 0.6, loop)


def head_spring(C, loop=False, hz=3.2, zeta=0.45, gain=0.55):
    """Secondary: the head lags the chest's pitch / yaw / roll and overshoots it (chest channels)."""
    for hc, cc in (("h_pitch", "lean"), ("h_yaw", "twist"), ("h_roll", "side")):
        src = C.get(cc)
        if src is None:
            continue
        lag = gain * (spring(src, hz, zeta, loop) - src)
        C[hc] = C.get(hc, np.zeros_like(src)) + lag


def cons(C, key, T, v):
    C[key] = np.tile(np.array(v, float), (len(T), 1)) if np.ndim(v) else np.full(len(T), float(v))


def world_from_chest0(p):
    return p


# ======================================================================= GATHER
GATHER_N = 210


def gather_channels(drop=0.455, touch_z=0.17):
    n = GATHER_N
    T = clip_time(n)
    C = base_channels(n)
    BACK, FWD = 0.42, 0.24
    # ---- feet: right steps back onto its ball, left slides forward; reverse to stand up
    step_track(C, "R", T, [(0.12, 0.47, (0.0, BACK), 0.055), (2.42, 2.80, (0.0, -BACK), 0.05)],
               phi_keys=[(0, 0), (0.10, 0), (0.20, 16), (0.33, 18), (0.47, 30), (0.62, 34), (1.10, 58),
                         (1.30, 57), (2.25, 57), (2.40, 40), (2.48, 22), (2.62, 12), (2.74, -4),
                         (2.82, 0), (3.5, 0)],
               toe_keys=[(0, 0), (0.15, 0), (0.28, 15), (0.44, 0), (2.44, 0), (2.56, 12), (2.74, 0), (3.5, 0)])
    step_track(C, "L", T, [(0.50, 0.80, (0.0, -FWD), 0.035), (2.88, 3.22, (0.0, FWD), 0.035)],
               phi_keys=[(0, 0), (0.46, 0), (0.54, 10), (0.66, 4), (0.76, -8), (0.84, 0), (2.84, 0),
                         (2.92, 12), (3.06, 5), (3.18, -5), (3.26, 0), (3.5, 0)])
    # ---- pelvis: weight left, back over the stepping foot, sink into the kneel, push up, return
    C["px"] = pchip([(0, 0), (0.14, 0.035), (0.42, 0.02), (0.55, -0.02), (0.80, -0.005), (1.15, 0.0),
                     (2.3, 0.0), (2.42, 0.03), (2.78, 0.035), (2.95, -0.03), (3.22, -0.01), (3.5, 0)], T)
    C["py"] = pchip([(0, 0), (0.12, 0.0), (0.47, 0.14), (0.80, 0.09), (1.12, 0.06), (1.40, 0.02),
                     (2.2, 0.06), (2.42, 0.02), (2.62, -0.06), (2.85, -0.10), (3.22, -0.01), (3.5, 0)], T)
    C["pz"] = pchip([(0, 0), (0.14, -0.012), (0.47, -0.07), (0.70, -0.20), (1.08, -drop - 0.012),
                     (1.18, -drop + 0.004), (1.26, -drop), (1.40, -drop - 0.005), (2.25, -drop), (2.40, -drop + 0.02),
                     (2.64, -0.16), (2.85, -0.035), (3.10, -0.02), (3.5, 0)], T)
    C["p_pitch"] = dkeys([(0, 0), (0.45, 4), (1.10, 16), (1.45, 22), (2.05, 8), (2.35, 10), (2.55, 22),
                          (2.80, 6), (3.2, 1), (3.5, 0)], T)
    C["p_yaw"] = dkeys([(0, 0), (0.45, -8), (1.10, -10), (1.45, -12), (2.1, -6), (2.6, -4), (3.0, 2), (3.5, 0)], T)
    C["p_roll"] = dkeys([(0, 0), (0.14, 3), (0.45, -2), (0.8, 1), (1.2, 2), (2.4, 2), (2.85, -3), (3.2, 1), (3.5, 0)], T)
    # ---- trunk: fold to reach, rise to look, lean forward to push up, upright
    C["lean"] = dkeys([(0, 0), (0.45, 4), (0.95, 22), (1.25, 38), (1.45, 44), (1.62, 40), (2.00, 6),
                       (2.30, 4), (2.55, 28), (2.85, 8), (3.2, -1), (3.5, 0)], T)
    C["twist"] = dkeys([(0, 0), (0.5, -4), (1.30, -14), (1.55, -12), (2.05, 4), (2.3, 6), (2.7, 0), (3.5, 0)], T)
    C["side"] = dkeys([(0, 0), (0.14, -2), (0.5, 1), (1.35, -6), (1.6, -5), (2.05, 1), (2.6, 0), (3.5, 0)], T)
    head_spring(C, hz=2.6, gain=0.5)
    # ---- right arm: follows the torso, reaches the snow (world), grabs, brings the find to the face
    gp = V((-0.21, BALL0["L"].y - FWD + 0.03, 0.0))       # grab point on the snow
    wrist_touch = gp + V((0.0, 0.07, touch_z))
    C["R_wrist"] = vkeys([(0, WRIST0["R"]), (0.55, WRIST0["R"] + V((-0.02, -0.04, 0.02))),
                          (0.95, gp + V((-0.03, 0.12, 0.42))), (1.22, gp + V((-0.01, 0.08, 0.12 + touch_z))),
                          (1.40, wrist_touch), (1.50, wrist_touch + V((0, 0.01, -0.012))),
                          (1.62, wrist_touch + V((0, 0.02, 0.01))), (1.75, gp + V((0.0, 0.10, 0.30))),
                          (3.5, gp)], T)
    # chest-space part of the path (inspect in front of the face, then back to the side)
    insp = SHOULDER0["R"] + V((0.16, -0.33, 0.02))
    chest_path = vkeys([(0, WRIST0["R"]), (0.55, WRIST0["R"] + V((-0.02, -0.06, 0.03))),
                        (1.70, SHOULDER0["R"] + V((0.02, -0.38, -0.25))), (2.05, insp),
                        (2.30, insp + V((0.01, 0.02, 0.01))), (2.55, SHOULDER0["R"] + V((0.03, -0.18, -0.36))),
                        (2.95, WRIST0["R"] + V((0.0, -0.05, 0.03))), (3.5, WRIST0["R"])], T)
    wsp = pchip([(0, 1), (0.62, 1), (0.98, 0), (1.66, 0), (1.95, 1), (3.5, 1)], T)
    C["R_wrist"] = chest_path * wsp[:, None] + C["R_wrist"] * (1 - wsp[:, None])
    C["R_wsp"] = wsp
    q_touch = hand_q("R", fingers=V((0.1, -0.55, -0.83)), palm=V((0.25, 0.83, -0.5)))
    q_lift = hand_q("R", fingers=V((0.2, -0.5, -0.84)), palm=V((0.5, 0.5, -0.6)))
    q_insp = hand_q("R", fingers=V((0.55, -0.80, 0.25)), palm=V((0.2, 0.28, 0.94)))
    q_turn = hand_q("R", fingers=V((0.60, -0.78, 0.10)), palm=V((0.62, 0.42, 0.66)))
    q_carry = hand_q("R", fingers=V((0.15, -0.35, -0.92)), palm=V((0.95, 0.1, 0.1)))
    # orientation keys: the world-space part is converted to chest space by the bake (slerp by wsp),
    # so key them as they should look at each time
    C["R_handq"] = q_arr(qkeys([(0, HANDQ0["R"]), (0.55, HANDQ0["R"]), (1.05, q_touch), (1.45, q_touch),
                                (1.62, q_lift), (2.05, q_insp), (2.22, q_turn), (2.38, q_insp),
                                (2.62, q_carry), (3.05, HANDQ0["R"]), (3.5, HANDQ0["R"])], T))
    C["R_epole"] = vkeys([(0, EPOLE0["R"]), (0.9, V((-0.6, 0.6, 0.3))), (1.5, V((-0.7, 0.55, 0.3))),
                          (2.05, V((-0.35, 0.2, -0.9))), (2.4, V((-0.35, 0.2, -0.9))), (2.9, EPOLE0["R"]),
                          (3.5, EPOLE0["R"])], T)
    finger_channels(C, "R", T, [(0, 0), (0.9, -6), (1.30, -14), (1.42, -12), (1.52, 55), (1.62, 62),
                                (1.90, 58), (2.05, 26), (2.35, 30), (2.55, 50), (3.0, 20), (3.5, 0)],
                    spread_keys=[(0, 0), (1.0, 10), (1.4, 12), (1.52, 0), (2.05, 4), (2.4, 4), (2.6, 0), (3.5, 0)],
                    thumb_keys=[(0, 0), (1.3, -10), (1.46, -8), (1.58, 38), (1.9, 36), (2.05, 18), (2.4, 20),
                                (2.6, 34), (3.0, 12), (3.5, 0)])
    # ---- left arm: hand props on the left knee while kneeling, pushes off it to stand
    C["L_onknee"] = pchip([(0, 0), (0.75, 0), (1.12, 1), (2.60, 1), (2.95, 0), (3.5, 0)], T)
    q_knee = hand_q("L", fingers=V((-0.1, -0.85, -0.5)), palm=V((-0.05, 0.5, -0.86)))
    C["L_handq"] = q_arr(qkeys([(0, HANDQ0["L"]), (0.75, HANDQ0["L"]), (1.12, q_knee), (2.60, q_knee),
                                (2.95, HANDQ0["L"]), (3.5, HANDQ0["L"])], T))
    C["L_wsp"] = pchip([(0, 1), (0.8, 1), (1.1, 0), (2.6, 0), (2.95, 1), (3.5, 1)], T)
    C["L_epole"] = vkeys([(0, EPOLE0["L"]), (1.1, V((0.9, 0.3, 0.1))), (2.6, V((0.9, 0.3, 0.1))),
                          (2.95, EPOLE0["L"]), (3.5, EPOLE0["L"])], T)
    finger_channels(C, "L", T, [(0, 0), (0.9, 0), (1.12, 18), (2.6, 18), (2.9, 4), (3.5, 0)])
    # ---- clavicles
    C["R_cfwd"] = dkeys([(0, 0), (1.0, 8), (1.45, 14), (1.8, 4), (2.3, 2), (3.5, 0)], T)
    C["R_cup"] = dkeys([(0, 0), (1.3, -6), (1.6, -4), (2.0, 2), (3.5, 0)], T)
    C["L_cup"] = dkeys([(0, 0), (1.2, 6), (2.5, 6), (2.7, 10), (3.0, 0), (3.5, 0)], T)
    # ---- look: the spot on the snow, then the find in the hand, then ahead
    C["look"] = vkeys([(0, LOOK0), (0.35, LOOK0), (0.70, gp + V((0, 0, 0.02))), (1.6, gp + V((0, 0, 0.02))),
                       (3.5, gp)], T)
    C["look_w"] = pchip([(0, 0), (0.35, 0), (0.75, 0.9), (2.42, 0.9), (2.9, 0.0), (3.5, 0)], T)
    C["look_hand"] = pchip([(0, 0), (1.55, 0), (1.85, 1), (2.42, 1), (2.6, 0), (3.5, 0)], T)
    C["eye_w"] = pchip([(0, 0), (0.30, 0), (0.55, 1), (2.5, 1), (2.9, 0), (3.5, 0)], T)
    C["n_pitch"] = dkeys([(0, 0), (1.3, 6), (2.0, 0), (2.5, -4), (3.0, 0), (3.5, 0)], T)
    C["h_roll"] = C["h_roll"] + dkeys([(0, 0), (1.9, 0), (2.1, 8), (2.35, 5), (2.5, 0), (3.5, 0)], T)
    # ---- face: blinks at the saccades, curious brows, effort breath on the push-up
    C["blink"] = blinks(T, [0.40, 1.66, 2.62, 3.30])
    C["brow"] = dkeys([(0, 0), (1.3, -2), (1.95, 0), (2.10, 7), (2.40, 6), (2.6, 0), (3.5, 0)], T)
    C["squint"] = pchip([(0, 0), (1.1, 0.25), (1.6, 0.3), (1.9, 0), (2.45, 0.35), (2.8, 0), (3.5, 0)], T)
    C["jaw"] = spring(dkeys([(0, 0), (2.42, 0), (2.52, 7), (2.75, 4), (2.9, 0), (3.5, 0)], T), 6.0, 0.5,
                      lo=-rad(0.5), bounce=0.3)
    C["gp"] = gp
    return C


def gather():
    """Calibrate the kneel depth (knee mesh touches z = 0) and the reach (fingertips touch the snow)
    against the real deformed mesh, then bake."""
    drop, touch = 0.455, 0.17
    k_frame = int(1.30 * FPS)
    t_frame = int(1.50 * FPS)
    kb = ["shin.R", "thigh.R"]
    fb = ["hand.R"] + [f"{f}_0{k}.R" for f in DIGITS for k in (1, 2, 3)]
    for it in range(7):
        C = gather_channels(drop, touch)
        zk = mesh_z(build(C, k_frame), kb)
        zf = mesh_z(build(C, t_frame), fb)
        ek, ef = zk - 0.004, zf - 0.006
        if abs(ek) < 0.002 and abs(ef) < 0.002:
            break
        drop += ek
        touch = clamp(touch - ef, 0.08, 0.30)
    print(f"[human extra] gather: kneel drop {drop:.3f} m (knee z {zk * 1000:+.1f} mm), "
          f"wrist height at touch {touch:.3f} m (fingertips z {zf * 1000:+.1f} mm)")
    C = gather_channels(drop, touch)
    act, poses = bake("Human_Gather", C, props={"event_grab": 1.52})
    return act


# ======================================================================= ATTACK
ATTACK_N = 78


def attack_channels():
    n = ATTACK_N
    T = clip_time(n)
    C = base_channels(n)
    TI = 0.54                                   # impact
    # ---- legs: weight back onto the right, drive onto the left; right heel peels on the strike
    step_track(C, "R", T, [], phi_keys=[(0, 0), (0.42, 0), (0.52, 12), (0.64, 18), (0.85, 6), (1.0, 0), (1.3, 0)])
    step_track(C, "L", T, [], phi_keys=[(0, 0), (0.12, 0), (0.28, 6), (0.40, 3), (0.47, 0), (1.3, 0)])
    C["px"] = pchip([(0, 0), (0.30, -0.035), (0.40, -0.03), (0.54, 0.03), (0.72, 0.035), (1.0, 0.01), (1.3, 0)], T)
    C["py"] = pchip([(0, 0), (0.32, 0.06), (0.40, 0.055), (0.54, -0.07), (0.70, -0.08), (1.0, -0.02), (1.3, 0)], T)
    C["pz"] = spring(pchip([(0, 0), (0.15, -0.015), (0.36, -0.005), (0.42, 0.0), (0.54, -0.075), (0.66, -0.08),
                            (0.95, -0.02), (1.3, 0)], T), 5.0, 0.7)
    # ---- rotations: hips fire before the chest (proximal -> distal)
    C["p_yaw"] = dkeys([(0, 0), (0.36, -16), (0.40, -15), (0.50, 12), (0.60, 16), (0.9, 5), (1.3, 0)], T)
    C["p_pitch"] = dkeys([(0, 0), (0.36, -5), (0.42, -4), (0.54, 12), (0.68, 14), (1.0, 3), (1.3, 0)], T)
    C["p_roll"] = dkeys([(0, 0), (0.34, -4), (0.54, 4), (0.8, 2), (1.3, 0)], T)
    C["twist"] = spring(dkeys([(0, 0), (0.38, -32), (0.42, -31), (0.53, 16), (0.62, 20), (0.95, 4), (1.3, 0)], T), 6.0, 0.6)
    C["lean"] = spring(dkeys([(0, 0), (0.38, -14), (0.43, -13), (0.54, 24), (0.66, 30), (0.95, 8), (1.3, 0)], T), 6.0, 0.6)
    C["side"] = dkeys([(0, 0), (0.38, 9), (0.54, -6), (0.8, -3), (1.3, 0)], T)
    head_spring(C, hz=3.0, gain=0.6)
    # ---- right arm: cock behind the head, whip through, stop dead at impact (recoil), recover
    Rs = SHOULDER0["R"]
    C["R_wrist"] = vkeys([(0, WRIST0["R"]), (0.16, Rs + V((-0.06, -0.10, -0.20))), (0.30, Rs + V((0.00, 0.02, 0.26))),
                          (0.40, Rs + V((0.03, 0.10, 0.30))), (0.46, Rs + V((0.00, -0.08, 0.34))),
                          (0.50, Rs + V((0.02, -0.36, 0.18))), (TI, Rs + V((0.05, -0.50, -0.02))),
                          (0.58, Rs + V((0.05, -0.49, -0.05))), (0.72, Rs + V((0.06, -0.44, -0.20))),
                          (0.95, Rs + V((0.00, -0.18, -0.42))), (1.3, WRIST0["R"])], T)
    sh0 = HANDQ0["R"] @ HAND_SHAFT["R"]
    q_cock = hand_q("R", shaft=V((0, 0.62, 0.78)), palm=V((1, 0, 0.1)))
    q_top = hand_q("R", shaft=V((0, -0.2, 0.98)), palm=V((1, 0.1, 0)))
    q_whip = hand_q("R", shaft=V((0, -0.95, 0.30)), palm=V((1, 0, 0)))
    q_imp = hand_q("R", shaft=V((0.05, -0.80, -0.60)), palm=V((1, 0, 0.05)))
    q_ft = hand_q("R", shaft=V((0.1, -0.55, -0.83)), palm=V((1, 0.0, 0.1)))
    q_lift = hand_q("R", shaft=V((0.0, -0.95, 0.30)), palm=V((1, 0.0, -0.2)))
    C["R_handq"] = q_arr(qkeys([(0, HANDQ0["R"]), (0.16, q_lift), (0.30, q_cock), (0.40, q_cock), (0.46, q_top),
                                (0.50, q_whip), (TI, q_imp), (0.60, q_imp), (0.74, q_ft), (1.0, q_lift),
                                (1.3, HANDQ0["R"])], T))
    C["R_epole"] = vkeys([(0, EPOLE0["R"]), (0.30, V((-0.4, -0.3, 0.87))), (0.42, V((-0.3, -0.5, 0.8))),
                          (TI, V((-0.3, 0.6, 0.2))), (0.8, V((-0.5, 0.8, 0.0))), (1.3, EPOLE0["R"])], T)
    # impact recoil: the hand stops dead and bounces back a little (spring on a short impulse)
    rec = spring(np.where((T > TI) & (T < TI + 0.03), 1.0, 0.0), 9.0, 0.35)
    C["R_wrist"] = C["R_wrist"] + np.outer(rec, [0, 0.035, 0.04])
    # right fingers: tool grip for the whole clip, squeeze at impact
    grip = pchip([(0, 62), (0.45, 64), (TI - 0.02, 72), (TI + 0.1, 70), (1.3, 62)], T)
    for f in FING:
        C[f"R_curl_{f}"] = np.radians(grip + {"index": -3, "middle": 0, "ring": 2, "pinky": 4}[f])
    C["R_curl_thumb"] = np.radians(pchip([(0, 42), (TI, 48), (1.3, 42)], T))
    # ---- left arm: forward guide in the wind-up, yanked back to the hip on the strike (counter-rotation)
    Ls = SHOULDER0["L"]
    C["L_wrist"] = vkeys([(0, WRIST0["L"]), (0.36, Ls + V((0.02, -0.40, -0.10))), (0.44, Ls + V((0.02, -0.40, -0.12))),
                          (0.58, Ls + V((0.12, 0.10, -0.42))), (0.8, Ls + V((0.10, 0.06, -0.45))), (1.3, WRIST0["L"])], T)
    q_guide = hand_q("L", fingers=V((-0.15, -0.95, 0.1)), palm=V((-0.35, 0, -0.93)))
    C["L_handq"] = q_arr(qkeys([(0, HANDQ0["L"]), (0.36, q_guide), (0.46, q_guide), (0.64, HANDQ0["L"]),
                                (1.3, HANDQ0["L"])], T))
    C["L_epole"] = vkeys([(0, EPOLE0["L"]), (0.36, V((0.8, 0.2, -0.5))), (0.6, V((0.5, 0.8, 0.1))), (1.3, EPOLE0["L"])], T)
    finger_channels(C, "L", T, [(0, 0), (0.30, -6), (0.44, -4), (0.56, 40), (0.85, 30), (1.3, 0)],
                    spread_keys=[(0, 0), (0.3, 10), (0.46, 8), (0.56, 0), (1.3, 0)])
    C["R_cup"] = dkeys([(0, 0), (0.35, 6), (0.5, 2), (1.3, 0)], T)
    C["R_cfwd"] = dkeys([(0, 0), (0.35, -8), (0.54, 12), (0.8, 6), (1.3, 0)], T)
    # ---- look at the target (in front, low), face: effort
    tgt = V((-0.12, -0.95, 0.45))
    C["look"] = vkeys([(0, LOOK0), (0.25, tgt), (1.3, tgt)], T)
    C["look_w"] = pchip([(0, 0), (0.25, 0.75), (0.95, 0.75), (1.3, 0)], T)
    C["eye_w"] = pchip([(0, 0), (0.2, 1), (1.0, 1), (1.3, 0)], T)
    C["brow"] = dkeys([(0, 0), (0.30, -5), (TI, -9), (0.9, -3), (1.3, 0)], T)
    C["brow_in"] = dkeys([(0, 0), (0.3, 4), (TI, 7), (1.0, 2), (1.3, 0)], T)
    C["squint"] = pchip([(0, 0), (0.35, 0.4), (TI, 0.85), (0.8, 0.4), (1.3, 0)], T)
    C["blink"] = blinks(T, [TI - 0.02, 1.05])
    C["jaw"] = spring(dkeys([(0, 0), (0.30, 3), (0.46, -0.5), (TI, -0.5), (0.58, 11), (0.72, 6), (0.9, 1), (1.3, 0)], T),
                      7.0, 0.5, lo=-rad(0.5), bounce=0.35)
    C["TI"] = TI
    return C


def attack():
    C = attack_channels()
    grip = [f"{f}_0{k}.R" for f in DIGITS for k in (1, 2, 3)]
    act, _ = bake("Human_Attack", C, hold=grip, hold_end=grip, props={"event_hit": C["TI"]})
    return act


# ======================================================================= THROW
THROW_N = 114


def throw_channels():
    n = THROW_N
    T = clip_time(n)
    C = base_channels(n)
    TR = 0.97                                   # release
    STRIDE = 0.40
    # ---- legs: stride with the left, pivot the right on its ball, step back in
    step_track(C, "L", T, [(0.46, 0.82, (0.035, -STRIDE), 0.06), (1.42, 1.72, (-0.035, STRIDE), 0.045)],
               phi_keys=[(0, 0), (0.30, 0), (0.44, 8), (0.60, 6), (0.78, -12), (0.86, 0), (1.38, 0),
                         (1.46, 10), (1.60, 5), (1.68, -6), (1.76, 0), (1.9, 0)],
               psi_keys=[(0, 0), (0.46, 0), (0.82, 8), (1.42, 8), (1.72, 0), (1.9, 0)])
    step_track(C, "R", T, [], phi_keys=[(0, 0), (0.86, 0), (0.95, 14), (1.10, 32), (1.28, 30), (1.40, 8),
                                       (1.50, 0), (1.9, 0)],
               psi_keys=[(0, 0), (0.93, 0), (1.14, 5), (1.28, 5), (1.40, 0), (1.9, 0)])
    C["R_kpole_x"] = dkeys([(0, 0), (0.9, 0), (1.1, -10), (1.4, 0), (1.9, 0)], T)
    C["px"] = pchip([(0, 0), (0.30, -0.03), (0.60, -0.045), (0.82, -0.01), (1.00, 0.02), (1.25, 0.03),
                     (1.42, -0.02), (1.70, -0.005), (1.9, 0)], T)
    C["py"] = pchip([(0, 0), (0.30, 0.03), (0.62, 0.08), (0.82, 0.0), (1.00, -0.17), (1.22, -0.23),
                     (1.40, -0.18), (1.56, -0.10), (1.75, -0.01), (1.9, 0)], T)
    C["pz"] = spring(pchip([(0, 0), (0.30, -0.01), (0.62, -0.035), (0.78, -0.02), (0.88, -0.06), (1.05, -0.07),
                            (1.25, -0.08), (1.45, -0.03), (1.62, -0.03), (1.9, 0)], T), 5.0, 0.8)
    # hips open first (0.80-0.92), the chest follows (0.84-0.98): hip-shoulder separation
    C["p_yaw"] = dkeys([(0, 0), (0.30, -8), (0.70, -30), (0.80, -28), (0.92, 14), (1.05, 22), (1.35, 16),
                        (1.7, 2), (1.9, 0)], T)
    C["p_pitch"] = dkeys([(0, 0), (0.62, -6), (0.82, -3), (1.00, 12), (1.25, 18), (1.5, 6), (1.9, 0)], T)
    C["p_roll"] = dkeys([(0, 0), (0.62, -6), (0.90, 0), (1.1, 6), (1.5, 2), (1.9, 0)], T)
    C["twist"] = spring(dkeys([(0, 0), (0.30, -8), (0.72, -40), (0.84, -40), (0.98, 26), (1.12, 32), (1.40, 18),
                               (1.75, 2), (1.9, 0)], T), 5.5, 0.65)
    C["lean"] = spring(dkeys([(0, 0), (0.30, -2), (0.72, -14), (0.86, -12), (1.00, 20), (1.20, 36), (1.45, 16),
                              (1.75, 2), (1.9, 0)], T), 5.5, 0.65)
    C["side"] = spring(dkeys([(0, 0), (0.72, 14), (0.88, 12), (1.02, -10), (1.3, -6), (1.9, 0)], T), 5.0, 0.7)
    head_spring(C, hz=3.0, gain=0.55)
    # ---- right arm: spear up to the shoulder, draw back, elbow leads, release, across the body
    Rs = SHOULDER0["R"]
    carry = Rs + V((-0.05, 0.02, 0.18))
    draw = Rs + V((-0.14, 0.44, 0.10))
    C["R_wrist"] = vkeys([(0, WRIST0["R"]), (0.14, Rs + V((-0.02, -0.10, -0.25))), (0.32, carry),
                          (0.72, draw), (0.84, draw + V((0.01, -0.03, 0.02))), (0.90, Rs + V((-0.08, 0.20, 0.24))),
                          (0.94, Rs + V((-0.03, -0.06, 0.26))), (TR, Rs + V((0.01, -0.30, 0.18))),
                          (1.06, Rs + V((0.10, -0.46, -0.10))), (1.22, Rs + V((0.30, -0.36, -0.46))),
                          (1.42, Rs + V((0.25, -0.22, -0.52))), (1.9, WRIST0["R"])], T)
    fwd = V((0.0, -1.0, 0.16)).normalized()
    q_carry = hand_q("R", shaft=V((0.05, -1, 0.12)), palm=V((0.35, 0, 0.94)))
    q_draw = hand_q("R", shaft=V((0.05, -1, 0.22)), palm=V((0.15, 0.0, 0.99)))
    q_pass = hand_q("R", shaft=fwd, palm=V((0.3, 0.3, 0.9)))
    q_rel = hand_q("R", shaft=fwd, palm=V((0.3, -0.6, 0.75)))
    q_ft = hand_q("R", fingers=V((0.30, -0.45, -0.84)), palm=V((0.85, 0.35, 0.1)))
    q_lift = hand_q("R", shaft=V((0.0, -0.98, 0.2)), palm=V((0.95, 0.0, 0.3)))
    C["R_handq"] = q_arr(qkeys([(0, HANDQ0["R"]), (0.14, q_lift), (0.32, q_carry), (0.72, q_draw), (0.86, q_draw),
                                (0.94, q_pass), (TR, q_rel), (1.08, q_ft), (1.45, q_ft), (1.9, HANDQ0["R"])], T))
    # the spear is AIMED: its orientation is world-referenced from the carry to the release
    C["R_qsp"] = pchip([(0, 1), (0.22, 1), (0.40, 0), (1.02, 0), (1.25, 1), (1.9, 1)], T)
    C["R_epole"] = vkeys([(0, EPOLE0["R"]), (0.32, V((-0.7, 0.1, -0.7))), (0.72, V((-0.5, 0.0, -0.87))),
                          (0.90, V((-0.6, -0.3, -0.2))), (TR, V((-0.4, 0.2, -0.8))), (1.2, V((-0.6, 0.6, 0.0))),
                          (1.9, EPOLE0["R"])], T)
    # grip until the release, fingers fly open (overshoot), then relax to the idle hand
    gr = pchip([(0, 62), (0.9, 64), (TR - 0.02, 62), (TR + 0.04, -18), (1.12, -8), (1.35, 6), (1.9, 0)], T)
    for f, lagf in (("index", 0.0), ("middle", 0.006), ("ring", 0.012), ("pinky", 0.018)):
        g_ = np.interp(T - lagf, T, gr)
        C[f"R_curl_{f}"] = spring(np.radians(g_ + {"index": -3, "middle": 0, "ring": 2, "pinky": 4}[f] *
                                             (T < TR)), 11.0, 0.45)
    C["R_curl_thumb"] = spring(np.radians(pchip([(0, 42), (TR - 0.02, 42), (TR + 0.05, -14), (1.3, 2), (1.9, 0)], T)),
                               11.0, 0.45)
    C["R_spread"] = spring(dkeys([(0, 0), (TR - 0.01, 0), (TR + 0.06, 12), (1.3, 3), (1.9, 0)], T), 8.0, 0.5)
    # ---- left arm: points at the target in the draw, pulled down to the hip on the throw
    Ls = SHOULDER0["L"]
    C["L_wrist"] = vkeys([(0, WRIST0["L"]), (0.35, Ls + V((-0.02, -0.34, -0.20))), (0.72, Ls + V((-0.12, -0.50, 0.02))),
                          (0.88, Ls + V((-0.10, -0.50, 0.00))), (1.02, Ls + V((0.10, 0.02, -0.40))),
                          (1.3, Ls + V((0.12, 0.12, -0.45))), (1.9, WRIST0["L"])], T)
    q_aim = hand_q("L", fingers=V((-0.1, -0.98, 0.1)), palm=V((-0.5, 0, -0.86)))
    C["L_handq"] = q_arr(qkeys([(0, HANDQ0["L"]), (0.35, q_aim), (0.88, q_aim), (1.1, HANDQ0["L"]), (1.9, HANDQ0["L"])], T))
    C["L_epole"] = vkeys([(0, EPOLE0["L"]), (0.6, V((0.9, 0.2, -0.4))), (1.0, V((0.4, 0.9, 0))), (1.9, EPOLE0["L"])], T)
    finger_channels(C, "L", T, [(0, 0), (0.35, -8), (0.88, -8), (1.00, 45), (1.4, 32), (1.9, 0)],
                    spread_keys=[(0, 0), (0.35, 12), (0.88, 10), (1.0, 0), (1.9, 0)])
    C["R_cfwd"] = dkeys([(0, 0), (0.72, -12), (0.86, -10), (TR, 10), (1.2, 16), (1.5, 4), (1.9, 0)], T)
    C["R_cup"] = dkeys([(0, 0), (0.72, 4), (TR, 6), (1.2, -4), (1.9, 0)], T)
    # ---- look at the target far ahead (slightly up), effort face
    tgt = V((0.0, -9.0, 1.9))
    C["look"] = vkeys([(0, LOOK0), (0.3, tgt), (1.9, tgt)], T)
    C["look_w"] = pchip([(0, 0), (0.3, 0.85), (1.35, 0.85), (1.75, 0), (1.9, 0)], T)
    C["eye_w"] = pchip([(0, 0), (0.25, 1), (1.5, 1), (1.8, 0), (1.9, 0)], T)
    C["brow"] = dkeys([(0, 0), (0.6, -4), (TR, -8), (1.3, 2), (1.9, 0)], T)
    C["brow_in"] = dkeys([(0, 0), (0.6, 4), (TR, 7), (1.3, 1), (1.9, 0)], T)
    C["squint"] = pchip([(0, 0), (0.6, 0.45), (TR, 0.8), (1.3, 0.2), (1.9, 0)], T)
    C["blink"] = blinks(T, [0.20, 1.45])
    C["jaw"] = spring(dkeys([(0, 0), (0.7, 2), (0.9, -0.5), (TR, 0), (1.02, 12), (1.2, 6), (1.5, 1), (1.9, 0)], T),
                      7.0, 0.5, lo=-rad(0.5), bounce=0.3)
    C["TR"] = TR
    return C


def throw():
    C = throw_channels()
    grip = [f"{f}_0{k}.R" for f in DIGITS for k in (1, 2, 3)]
    act, _ = bake("Human_Throw", C, hold=grip, props={"event_release": C["TR"]})
    return act


# ======================================================================= WARM HANDS (loop)
WARM_N = 240


def warm_channels():
    n = WARM_N
    T = clip_time(n)
    L = n * DT
    C = base_channels(n)
    per = lambda kv: pchip(kv, T, periodic=True)
    dper = lambda kv: dkeys(kv, T, periodic=True)
    # phases (s): rub 0.0-1.8, cup + inhale 1.8-2.2, blow 2.2-3.05, part / rub 3.05-4.0
    rub = per([(0, 1), (1.75, 1), (1.95, 0), (3.05, 0), (3.30, 1), (4.0, 1)])
    cup = per([(0, 0), (1.75, 0), (2.0, 1), (3.0, 1), (3.25, 0), (4.0, 0)])
    blow = per([(0, 0), (2.12, 0), (2.30, 1), (2.85, 0.8), (3.05, 0), (4.0, 0)])
    inhale = per([(0, 0), (1.80, 0), (2.12, 1), (2.30, 0.4), (2.9, -0.6), (3.2, 0), (4.0, 0)])
    # ---- stance: knees soft, weight rocking between the feet, unloaded heel lifts (keeps warm)
    rock = np.sin(TAU * 2 * T / L)
    C["pz"] = -0.03 + 0.006 * np.cos(TAU * 4 * T / L) - 0.004 * inhale
    C["px"] = 0.022 * rock
    C["py"] = np.full(n + 1, 0.012)
    C["p_roll"] = rad(2.0) * rock
    C["p_pitch"] = np.full(n + 1, rad(4))
    for sd, s in SIDES:
        lift = np.clip(-s * rock, 0, None) ** 1.5
        C[f"{sd}_phi"] = spring(rad(9) * lift, 3.0, 0.6, loop=True)
    # ---- trunk hunched, head down into the collar; breathing
    shiv_w = per([(0, 1), (1.8, 1), (2.1, 0.5), (2.9, 0.4), (3.2, 1), (4.0, 1)])
    sh = lambda f, ph: np.sin(TAU * f * T / L + ph)          # f = cycles per loop (integer -> loops)
    C["lean"] = rad(9) - rad(3) * inhale + rad(5) * blow
    C["side"] = -0.6 * C["p_roll"]
    C["twist"] = rad(1.5) * np.sin(TAU * T / L + 0.4)
    C["spine_03_roll"] = rad(0.8) * shiv_w * (sh(37, 0.3) + 0.6 * sh(45, 1.1))
    C["spine_03_yaw"] = rad(0.6) * shiv_w * (sh(41, 2.0) + 0.5 * sh(29, 0.2))
    C["spine_02_pitch"] = rad(0.6) * shiv_w * sh(33, 0.9)
    C["n_pitch"] = rad(10) + rad(8) * blow - rad(3) * inhale
    C["h_pitch"] = rad(6) + rad(5) * blow - rad(4) * inhale + rad(0.8) * shiv_w * sh(47, 0.5)
    C["h_yaw"] = rad(3) * np.sin(TAU * T / L + 1.2)
    C["h_roll"] = rad(2) * np.sin(TAU * T / L + 2.5)
    head_spring(C, loop=True, hz=2.8, gain=0.5)
    for sd, s in SIDES:
        C[f"{sd}_cup"] = rad(12) + rad(5) * inhale - rad(3) * blow + rad(1.0) * shiv_w * sh(39 + 2 * (s > 0), s)
        C[f"{sd}_cfwd"] = rad(10) + rad(3) * cup
    # ---- hands: palms together in front of the mouth, rubbing in anti-phase; cupped for the blow
    mouth0 = M0["jaw"] @ V((0, LEN["jaw"] * 0.9, 0.0))
    mouth = mouth0 + V((0, -0.14, 0.0))
    ph = TAU * 10 * T / L                                    # 10 rubs per loop = 2.5 Hz
    rubv = rub * np.sin(ph)
    rubv2 = rub * np.sin(2 * ph + 0.6)
    shake = 0.002 * shiv_w * sh(43, 0.7)
    for sd, s in SIDES:
        base_rub = np.array(mouth + V((0.030 * s, -0.02, -0.21)))
        base_cup = np.array(mouth + V((0.040 * s, 0.035, -0.19)))
        w = (1 - cup)[:, None] * base_rub + cup[:, None] * base_cup
        w = w + np.outer(-s * 0.032 * rubv, [0, 0, 1]) + np.outer(0.010 * rubv2, [0, 1, 0])
        w = w + np.outer(shake + 0.01 * blow, [0, -0.3, 1])
        C[f"{sd}_wrist"] = w
        q_rub = hand_q(sd, fingers=V((0.0, -0.22, 1)), palm=V((-s, 0, 0)))
        q_cup = hand_q(sd, fingers=V((-0.20 * s, -0.40, 0.90)), palm=V((-0.70 * s, 0.62, 0.2)))
        qa = q_arr([q_rub] * (n + 1))
        qb = q_arr([q_cup] * (n + 1))
        if qa[0] @ qb[0] < 0:
            qb = -qb
        q = qa * (1 - cup)[:, None] + qb * cup[:, None]
        C[f"{sd}_handq"] = q / np.linalg.norm(q, axis=1)[:, None]
        C[f"{sd}_epole"] = np.tile(np.array(V((0.55 * s, 0.05, -0.83)).normalized()), (n + 1, 1))
        # fingers: straight-ish while rubbing, curled into a cup for the blow
        base = rad(6) + rad(28) * cup + rad(3) * rub * np.sin(ph + 1.0)
        for f, k in (("index", 1.0), ("middle", 1.05), ("ring", 1.1), ("pinky", 1.2)):
            C[f"{sd}_curl_{f}"] = spring(base * k, 7.0, 0.6, loop=True)
        C[f"{sd}_curl_thumb"] = spring(rad(-4) + rad(22) * cup, 7.0, 0.6, loop=True)
        C[f"{sd}_spread"] = rad(-3) * np.ones(n + 1)
    # ---- face: squinting in the cold, teeth chatter while rubbing, blow through pursed lips
    chat = rub * shiv_w * (0.5 + 0.5 * np.sin(TAU * 40 * T / L))
    C["jaw"] = spring(rad(1.4) * chat + rad(9) * blow + rad(3) * np.clip(inhale, 0, None), 9.0, 0.35,
                      loop=True, lo=-rad(0.5), bounce=0.4)
    C["squint"] = 0.45 + 0.2 * blow
    C["brow"] = rad(-3) + rad(3) * inhale
    C["brow_in"] = np.full(n + 1, rad(4))
    C["blink"] = blinks(T, [0.55, 1.95, 3.35])
    C["look"] = np.tile(np.array(mouth + V((0, -0.05, -0.08))), (n + 1, 1))
    C["eye_w"] = 0.6 * (1 - cup) + 0.0 * cup
    return C


# ======================================================================= HURT
HURT_N = 48


def hurt_channels():
    n = HURT_N
    T = clip_time(n)
    C = base_channels(n)
    TH = 0.02
    imp = np.where((T >= TH) & (T < TH + 0.07), 1.0, 0.0)       # the blow (a short push)
    resp = spring(imp, 2.6, 0.48) / 0.6                         # body response (peak ~1 at ~0.17 s)
    fast = spring(imp, 4.5, 0.42) / 0.75                        # lighter segments react faster
    C["lean"] = rad(-22) * resp
    C["twist"] = rad(22) * fast
    C["side"] = rad(-11) * resp
    C["px"] = -0.035 * resp
    C["py"] = 0.07 * resp
    C["pz"] = -0.06 * spring(imp, 2.2, 0.6) / 0.55
    C["p_pitch"] = rad(-6) * resp
    C["p_yaw"] = rad(9) * resp
    # head: inertia keeps it in place (relative flex forward), then whips back past the chest
    C["h_pitch"] = rad(8) * (fast - spring(imp, 2.0, 0.5) / 0.55) - rad(4) * resp
    C["h_yaw"] = rad(-6) * fast
    C["n_pitch"] = rad(-5) * resp
    step_track(C, "L", T, [], phi_keys=[(0, 0), (0.06, 0), (0.16, 7), (0.32, 2), (0.45, 0), (0.8, 0)])
    C["R_kpole_x"] = dkeys([(0, 0), (0.18, 8), (0.5, 0), (0.8, 0)], T)
    # arms: left arm up to guard, right arm flares for balance
    Ls, Rs = SHOULDER0["L"], SHOULDER0["R"]
    guard = spring(pchip([(0, 0), (0.05, 0), (0.14, 1), (0.34, 1), (0.66, 0), (0.8, 0)], T), 5.5, 0.55)
    C["L_wrist"] = np.array(WRIST0["L"]) * (1 - guard)[:, None] + np.outer(guard, Ls + V((-0.14, -0.28, -0.10)))
    q_guard = hand_q("L", fingers=V((-0.5, -0.4, 0.75)), palm=V((-0.2, 0.9, 0.3)))
    C["L_handq"] = q_arr(qkeys([(0, HANDQ0["L"]), (0.06, HANDQ0["L"]), (0.16, q_guard), (0.36, q_guard),
                                (0.7, HANDQ0["L"]), (0.8, HANDQ0["L"])], T))
    C["L_epole"] = vkeys([(0, EPOLE0["L"]), (0.14, V((0.8, 0.0, -0.6))), (0.5, V((0.8, 0.0, -0.6))),
                          (0.8, EPOLE0["L"])], T)
    flare = spring(pchip([(0, 0), (0.04, 0), (0.12, 1), (0.30, 0.6), (0.62, 0), (0.8, 0)], T), 5.0, 0.5)
    C["R_wrist"] = np.array(WRIST0["R"]) * (1 - flare)[:, None] + np.outer(flare, Rs + V((-0.30, -0.02, -0.32)))
    C["R_epole"] = vkeys([(0, EPOLE0["R"]), (0.12, V((-0.5, 0.6, 0.6))), (0.5, V((-0.3, 0.8, 0.2))),
                          (0.8, EPOLE0["R"])], T)
    for sd in ("L", "R"):
        finger_channels(C, sd, T, [(0, 0), (0.04, 0), (0.10, -14), (0.22, 20), (0.45, 28), (0.7, 5), (0.8, 0)],
                        spread_keys=[(0, 0), (0.04, 0), (0.10, 14), (0.25, 4), (0.8, 0)],
                        rates={"index": 12, "middle": 11, "ring": 10, "pinky": 9, "thumb": 11})
    for sd, s in SIDES:
        C[f"{sd}_cup"] = rad(10) * spring(imp, 3.5, 0.5) / 0.7
    # wince
    C["blink"] = pchip([(0, 0), (0.025, 0), (0.06, 1), (0.26, 1), (0.40, 0.2), (0.50, 0), (0.8, 0)], T)
    C["squint"] = pchip([(0, 0), (0.04, 0), (0.08, 1), (0.34, 0.9), (0.55, 0.2), (0.8, 0)], T)
    C["brow"] = dkeys([(0, 0), (0.04, 0), (0.08, -8), (0.34, -7), (0.6, -1), (0.8, 0)], T)
    C["brow_in"] = dkeys([(0, 0), (0.04, 0), (0.08, 9), (0.36, 7), (0.6, 1), (0.8, 0)], T)
    C["jaw"] = spring(dkeys([(0, 0), (0.04, 0), (0.06, -0.5), (0.14, -0.5), (0.18, 13), (0.34, 8), (0.55, 1),
                             (0.8, 0)], T), 8.0, 0.45, lo=-rad(0.5), bounce=0.35)
    C["jaw_side"] = dkeys([(0, 0), (0.14, 0), (0.22, -2), (0.5, 0), (0.8, 0)], T)
    C["eye_w"] = np.zeros(n + 1)
    return C


# ======================================================================= DEATH
DEATH_N = 156


def death_channels(adj=None):
    """adj: calibration offsets (knee_drop, lie_z) found against the real mesh."""
    adj = adj or {}
    n = DEATH_N
    T = clip_time(n)
    C = base_channels(n)
    T_KNEE = 0.50
    # ---- phase 1: knees buckle, heels rise over the balls (toes tucked), knees hit the snow
    kd = adj.get("knee_drop", 0.47)
    fall = minjerk(0.10, T_KNEE, T) ** 1.4                       # accelerating drop
    knock = spring(np.where((T > T_KNEE) & (T < T_KNEE + 0.04), 1.0, 0.0), 6.0, 0.4)
    # ---- phase 2: topple about the knees under gravity
    Lc = 0.62                                                     # knee -> upper-body COM
    th = np.zeros(n + 1)
    om = 0.0
    t_top = 0.56
    th_c = rad(9)
    th_end = adj.get("th_end", rad(84))
    t_land = None
    for i in range(1, n + 1):
        t = T[i]
        if t < t_top:
            th[i] = th_c * smoothstep(0.20, t_top, t)
            continue
        if th[i - 1] >= th_end:
            if t_land is None:
                t_land = t
            th[i] = th_end
            continue
        a = G / Lc * math.sin(th[i - 1])
        om += a * DT
        th[i] = min(th_end, th[i - 1] + om * DT)
    if t_land is None:
        t_land = T[-1]
    land = smoothstep(t_land - 0.02, t_land + 0.02, T)
    hit = spring(np.where((T >= t_land) & (T < t_land + 0.05), 1.0, 0.0), 5.0, 0.35)   # impact bounce
    hit2 = spring(np.where((T >= t_land) & (T < t_land + 0.05), 1.0, 0.0), 3.2, 0.3)
    tp = np.clip((th - th_c) / (th_end - th_c), 0, 1)             # 0 kneeling .. 1 lying
    # knee (pivot) and hip positions: kneel height from the calibrated drop, then the thigh rotates
    # about the knee; the pelvis follows the hip
    C["pz"] = -kd * fall + 0.012 * knock
    # hip path in the sagittal plane (forward = -Y)
    l1 = LEN["thigh.L"]
    hip0 = (M0["thigh.L"].translation + M0["thigh.R"].translation) / 2
    knee_y = BALL0["L"].y - 0.36
    # during the buckle the hips move forward over the knees
    buck_y = (knee_y + 0.03 - hip0.y) * fall
    hip_kneel_z = hip0.z - kd
    top_y = -l1 * np.sin(th) + l1 * math.sin(0)            # displacement of the hip about the knee
    top_z = l1 * np.cos(th) - l1
    lie = adj.get("lie_z", 0.0)
    C["py"] = buck_y + np.where(T >= t_top, top_y, -l1 * np.sin(th))
    C["pz"] = C["pz"] + top_z + lie * tp
    C["px"] = 0.10 * tp
    # pelvis pitches forward with the thigh (+ slump), rolls onto the left side a little
    C["p_pitch"] = th * 1.0 + rad(8) * fall * (1 - tp)
    C["p_roll"] = rad(20) * tp ** 1.5
    C["p_yaw"] = rad(8) * tp
    # ---- trunk: slumps in the buckle, straightens out onto the ground, bounces at the impact
    C["lean"] = rad(14) * fall * (1 - tp) + rad(3) * tp + rad(4) * hit
    C["side"] = rad(10) * tp + rad(-3) * hit2
    C["twist"] = rad(-12) * tp
    C["spine_03_pitch"] = rad(-4) * tp
    # head: jerks up with the shock, lolls in the buckle, turned to the left lying on the cheek
    shock = pchip([(0, 0), (0.04, 0), (0.10, 1), (0.25, 0.6), (0.45, 0), (2.6, 0)], T)
    C["n_pitch"] = rad(-10) * shock + rad(18) * fall * (1 - tp) + rad(6) * tp + rad(8) * hit
    C["h_pitch"] = rad(-8) * shock + rad(12) * fall * (1 - tp) + (rad(4) + adj.get("head_p", 0.0)) * tp + rad(10) * hit2
    C["h_yaw"] = spring(rad(66) * tp ** 2, 2.5, 0.5)
    C["n_yaw"] = rad(18) * tp ** 2
    C["h_roll"] = rad(8) * fall * (1 - tp) + rad(12) * tp
    # ---- legs: balls planted, heels rise (toes tucked), knee pole turns with the hips
    for sd, s in SIDES:
        # as the hips extend the feet are dragged back and roll over onto their tops (laces down)
        phi = rad(58) * smoothstep(0.12, T_KNEE, T) + rad(77) * tp ** 1.5
        C[f"{sd}_ball"] = C[f"{sd}_ball"] + np.outer(adj.get("feet_back", 0.31) * smoothstep(0.25, 1.0, tp),
                                                     [0.03 * s, 1.0, 0.0]) + np.outer(adj.get("feet_z", 0.0) * smoothstep(0.3, 1.0, tp), [0, 0, 1.0])
        C[f"{sd}_air"] = smoothstep(0.2, 0.7, tp)
        C[f"{sd}_phi"] = phi
        C[f"{sd}_kpole_x"] = 1.1 * tp ** 2
    # ---- arms: limp - flinch out at the shock, hang (world down) in the fall, flop on the ground
    for sd, s in SIDES:
        sh = SHOULDER0[sd]
        hang = np.array(WRIST0[sd]) + np.outer(shock, [0.06 * s, -0.08, 0.10])
        C[f"{sd}_wsp"] = np.clip(1 - 1.4 * tp, 0, 1)
        C[f"{sd}_wrist"] = hang
    # lying positions in armature space, computed from the final body placement in death()
    C["t_land"] = t_land
    C["adj"] = adj
    C["tp"] = tp
    C["hit"] = hit
    C["hit2"] = hit2
    # face
    C["brow"] = dkeys([(0, 0), (0.05, 0), (0.10, 9), (0.4, 4), (1.2, 0), (2.6, -1)], T)
    C["jaw"] = spring(dkeys([(0, 0), (0.05, 0), (0.12, 12), (0.4, 7), (1.0, 5), (1.3, 9), (1.6, 6), (2.6, 7)], T),
                      5.0, 0.5, lo=-rad(0.5), bounce=0.3)
    C["blink"] = pchip([(0, 0), (0.08, 0), (0.12, 0.4), (0.3, 0.2), (0.8, 0.4), (t_land, 0.55), (t_land + 0.1, 0.9),
                        (t_land + 0.3, 0.62), (2.6, 0.62)], T)
    C["squint"] = pchip([(0, 0), (0.10, 0.6), (0.5, 0.3), (2.6, 0.1)], T)
    C["spine_02_pitch"] = rad(-2.5) * smoothstep(1.85, 2.25, T) * tp     # last breath out
    return C


def death():
    """Knee drop calibrated so the knees touch; the lying pose is found by letting the body settle
    onto z = 0 (pelvis lift per frame against the real deformed mesh), with the arms laid on the
    ground from the landed pose."""
    adj = {"knee_drop": 0.47, "lie_z": 0.0}
    kb = ["shin.L", "shin.R", "thigh.L", "thigh.R"]
    kneel_f = int(0.53 * FPS)
    for it in range(4):
        C = death_channels(adj)
        dress_death_arms(C)
        zk = mesh_z(build(C, kneel_f), kb)
        if abs(zk - 0.004) < 0.002:
            break
        adj["knee_drop"] += zk - 0.004
    # lying height: the pelvis / chest rest ON the snow in the final pose
    n = C["n"]
    for it in range(5):
        C = death_channels(adj)
        dress_death_arms(C)
        zl = mesh_z(build(C, n), ["pelvis", "spine_01", "spine_02", "spine_03"])
        if abs(zl - 0.003) < 0.0015:
            break
        adj["lie_z"] += 0.003 - zl
        print("  lie calib", it, round(zl, 4), round(adj["lie_z"], 4))
    # every body part rests on the snow on its own: arms, feet (on their tops) and the head (on its
    # cheek) are calibrated separately so no single part props the body up
    parts = {"torso": ["pelvis", "spine_01", "spine_02", "spine_03"], "head": ["head", "neck", "jaw"],
             "armL": ["upper_arm.L", "forearm.L", "hand.L"] + [f"{f}_0{k}.L" for f in DIGITS for k in (1, 2, 3)],
             "armR": ["upper_arm.R", "forearm.R", "hand.R"] + [f"{f}_0{k}.R" for f in DIGITS for k in (1, 2, 3)],
             "legs": ["thigh.L", "thigh.R", "shin.L", "shin.R"], "feet": ["foot.L", "foot.R", "toe.L", "toe.R"]}
    for it in range(5):
        Pn = build(C, n)
        z = {k: mesh_z(Pn, v) for k, v in parts.items()}
        err = max(abs(z["torso"] - 0.003), abs(z["armL"] - 0.004), abs(z["armR"] - 0.004),
                  abs(z["feet"] - 0.004), max(0.0, z["head"] - 0.012), max(0.0, -z["head"]))
        if err < 0.003:
            break
        adj["lie_z"] += 0.003 - z["torso"]
        for sd in ("L", "R"):
            adj["arm_z_" + sd] = adj.get("arm_z_" + sd, 0.05) + 0.004 - z["arm" + sd]
        adj["feet_z"] = adj.get("feet_z", 0.0) + 0.004 - z["feet"]
        if z["head"] > 0.012 or z["head"] < 0:
            adj["head_p"] = adj.get("head_p", 0.0) + (z["head"] - 0.006) / 0.16
        C = death_channels(adj)
        dress_death_arms(C)
    # settle: lift the root where anything is still under the snow (smoothed), then bake
    n = C["n"]
    Pn = build(C, n)
    print("[human extra] death: final contact heights (mm):",
          {k: round(mesh_z(Pn, v) * 1000, 1) for k, v in parts.items()},
          {k: round(v, 3) for k, v in adj.items()})
    lift = np.zeros(n + 1)
    for i in range(n + 1):
        lift[i] = max(0.0, 0.003 - mesh_z(build(C, i)))
    # smooth: a moving max then ease so the correction never pops
    k = 5
    lm = np.array([lift[max(0, i - k):i + k + 1].max() for i in range(n + 1)])
    lm = np.convolve(np.pad(lm, 4, mode="edge"), np.ones(9) / 9, mode="valid")
    lm = np.maximum(lm, lift)
    print(f"[human extra] death: knee drop {adj['knee_drop']:.3f} m, landed at {C['t_land']:.2f} s, "
          f"max settle lift {lm.max() * 1000:.1f} mm, final lift {lm[-1] * 1000:.1f} mm")
    act, poses = bake("Human_Death", C, lift=lm, end_blend=False, props={"event_impact": float(C["t_land"])})
    zmin = min(mesh_z(poses[i]) for i in range(0, n + 1, 3))
    print(f"[human extra] death: lowest vertex over the clip {zmin * 1000:+.1f} mm")
    return act


def dress_death_arms(C):
    """Arm targets for the fall / lying phases, in armature space: the limp arms hang under the
    shoulders while toppling (lagging the torso), then lie on the snow - the left arm along the side,
    palm up, the right arm bent up beside the head."""
    n = C["n"]
    T = clip_time(n)
    tp = C["tp"]
    hit = C["hit"]
    # final placement of shoulders from a probe pose at the last frame
    Pf = build(C, n)
    Mf = fk(Pf)
    tl = C["t_land"]
    for sd, s in SIDES:
        sh_path = []
        for i in range(n + 1):
            if i % 6 == 0 or i == n:
                P = build(C, i)
                M = fk(P)
                sh_path.append((T[i], np.array(M[f"upper_arm.{sd}"].translation)))
        ts = np.array([a for a, _ in sh_path])
        sp = np.array([b for _, b in sh_path])
        shp = np.stack([np.interp(T, ts, sp[:, c]) for c in range(3)], axis=1)
        hang = shp + np.array([0.05 * s, 0.03, -0.50])
        hang = vspring(hang, 2.2, 0.35)                                   # limp: lags and swings
        shf = V(sp[-1].tolist())
        chest_f = Mf["spine_03"].to_3x3()
        across = chest_f.col[0] * s                                      # toward this side
        along = chest_f.col[1]                                           # toward the head
        if sd == "L":
            lie = shf + along * -0.46 + across * 0.12
        else:
            lie = shf + along * 0.22 + across * 0.30
        lie.z = C["adj"].get("arm_z_" + sd, 0.05)
        lw = smoothstep(tl - 0.10, tl + 0.12, T)
        w = hang * (1 - lw)[:, None] + np.array(lie)[None, :] * lw[:, None]
        w[:, 2] = np.maximum(w[:, 2], lie.z) + 0.03 * hit * lw          # bounce on the impact
        base = C[f"{sd}_wrist"]
        pre = np.clip((T - 0.35) / 0.3, 0, 1)[:, None]                   # from the chest-carried hang
        C[f"{sd}_wrist"] = base * (1 - pre) + w * pre
        C[f"{sd}_wsp"] = np.clip(1 - pre[:, 0], 0, 1)
        if sd == "L":
            q_lie = hand_q(sd, fingers=-along, palm=V((0.2 * s, 0, 1)))
            pole = V((0.6 * s, 0.0, 0.8))
        else:
            q_lie = hand_q(sd, fingers=along, palm=V((0, 0, -1)))
            pole = (across * 0.8 - along * 0.3 + V((0, 0, -0.3))).normalized()
        q_hang = hand_q(sd, fingers=V((0.05 * s, 0, -1)), palm=V((-s, 0.2, 0)))
        C[f"{sd}_handq"] = q_arr(qkeys([(0, HANDQ0[sd]), (0.4, HANDQ0[sd]), (0.8, q_hang), (tl, q_hang),
                                        (tl + 0.2, q_lie), (2.6, q_lie)], T))
        C[f"{sd}_epole"] = vkeys([(0, EPOLE0[sd]), (0.5, EPOLE0[sd]), (tl, V((0.3 * s, 0.6, 0.3))),
                                  (tl + 0.2, pole), (2.6, pole)], T)
        finger_channels(C, sd, T, [(0, 0), (0.1, -10), (0.3, 12), (tl, 18), (tl + 0.25, 24), (2.6, 22)],
                        spread_keys=[(0, 0), (0.1, 10), (0.4, 3), (2.6, 2)])


# ======================================================================= WARM + HURT bakers
def warm_hands():
    act, _ = bake("Human_WarmHands", warm_channels(), cyclic=True)
    return act


def hurt():
    act, _ = bake("Human_Hurt", hurt_channels(), blend_in=0.03, props={"event_hit": 0.02})
    return act


# ======================================================================= build
BUILDERS = [("Human_Gather", gather), ("Human_Attack", attack), ("Human_Throw", throw),
            ("Human_WarmHands", warm_hands), ("Human_Hurt", hurt), ("Human_Death", death)]
print(f"[human extra] idle pose: {IDLE_SRC}; keyed locations: {sorted(KEY_LOC)}")
for name, fn in BUILDERS:
    if ONLY and name not in ONLY:
        continue
    fn()
for p_ in pb:
    p_.matrix_basis = Matrix()
if IK_CLAMPED:
    print("[human extra] IK targets out of reach (max overshoot, m):",
          {k: round(v, 4) for k, v in IK_CLAMPED.items()})
if bpy.data.actions.get("Human_Idle"):
    arm.animation_data.action = bpy.data.actions["Human_Idle"]
print("[human extra] actions:", sorted(a.name for a in bpy.data.actions if a.name.startswith("Human_")))

if "--test-save" in argv:
    path = argv[argv.index("--test-save") + 1]
    bpy.ops.wm.save_as_mainfile(filepath=path, copy=True)
    print("[human extra] test copy saved to", path)
